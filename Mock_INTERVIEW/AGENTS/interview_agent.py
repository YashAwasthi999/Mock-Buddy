# purpose = it generates the questions

import ast

from CORE.llm_service import generate_completion
from CORE.audio_io import record_audio, speak_text, transcribe_audio
from CORE.feedback_generator import generate_feedback_and_scores
from PROMPTS.questionn_prompts import get_question_generation_prompt
from UTILS.config import OPENAI_API_KEY, QUESTION_OPENAI_API_KEY


class InterviewAgent:
    def __init__(self, resume_text: str):
        self.resume_text = resume_text
        self.interview_history = []
        self.current_round_info = None
        self.feedback = None
        self.questions = []
        self.asked_questions = []

    def _remember_new_questions(self, questions: list[str]) -> list[str]:
        seen = {" ".join(question.casefold().split()) for question in self.asked_questions}
        new_questions = []

        for question in questions:
            question = question.strip()
            normalized = " ".join(question.casefold().split())
            if normalized and normalized not in seen:
                seen.add(normalized)
                new_questions.append(question)

        self.asked_questions.extend(new_questions)
        return new_questions

    def generate_questions_for_round(self, round_name: str, num_questions: int) -> list[str]:
        """Generates questions for the specified round using the LLM."""
        print(f"\nGenerating {num_questions} questions for the {round_name} round based on your resume...")
        prompt = get_question_generation_prompt(
            self.resume_text,
            round_name,
            num_questions,
            self.asked_questions,
        )
        raw_response = generate_completion(
            prompt,
            max_tokens=300 * num_questions,
            temperature=0.8,
            api_key=QUESTION_OPENAI_API_KEY or OPENAI_API_KEY,
        )

        try:
            cleaned = raw_response.strip().strip("```python").strip("```").strip()
            questions = ast.literal_eval(cleaned)
            if isinstance(questions, list) and all(isinstance(q, str) for q in questions):
                if len(questions) > num_questions:
                    print(f"Warning: LLM generated {len(questions)} questions, expected {num_questions}. Using the first {num_questions}.")
                questions = self._remember_new_questions(questions[:num_questions])
                if len(questions) < num_questions:
                    print(f"Warning: LLM generated only {len(questions)} new questions, expected {num_questions}.")

                print("Questions generated successfully.")
                self.questions = questions
                return questions
            raise ValueError("Parsed result is not a list of strings.")
        except (SyntaxError, ValueError, TypeError) as e:
            print(f"Error parsing questions from LLM response: {e}")
            print(f"Raw Response: {raw_response}")
            lines = [line.strip() for line in raw_response.split("\n") if line.strip()]
            if lines and len(lines) >= max(1, num_questions // 2):
                print("Falling back to line splitting for questions.")
                fallback_questions = self._remember_new_questions(lines[:num_questions])
                self.questions = fallback_questions
                return fallback_questions

            print("Could not generate questions properly; using default questions.")
            default_questions = [
                f"Tell me about your experience relevant to the {round_name} role based on your resume.",
                "What is your biggest strength related to this area?",
                "Can you describe a challenge you faced and how you overcame it?",
                "Where do you see yourself in 5 years?",
                "Do you have any questions for me?",
            ][:num_questions]
            default_questions = self._remember_new_questions(default_questions)
            self.questions = default_questions
            return default_questions

    def _generate_questions(self, round_name: str, num_questions: int) -> list[str]:
        """Backward-compatible wrapper."""
        return self.generate_questions_for_round(round_name, num_questions)

    def conduct_round(self, round_info: dict):
        """Conducts a single round of the interview."""
        self.current_round_info = round_info
        round_name = round_info["name"]
        num_questions = round_info["num_questions"]
        self.interview_history = []

        print(f"\n--- Starting {round_name} Round ---")
        speak_text(f"Welcome to the {round_name} round. I will ask you {num_questions} questions based on your resume. Please answer clearly after I finish speaking.")

        questions = self.generate_questions_for_round(round_name, num_questions)

        for i, question in enumerate(questions):
            print(f"\nQuestion {i + 1}/{len(questions)}: ")
            speak_text(question)

            record_duration = 30
            audio_file = record_audio(duration=record_duration)

            answer = None
            if audio_file:
                answer = transcribe_audio(audio_file)

            if not answer:
                speak_text("I didn't catch that. Let's move to the next question.")
                answer = "[No response recorded]"

            self.interview_history.append({"question": question, "answer": answer})

        print(f"\n--- {round_name} Round Complete ---")
        speak_text("Thank you. That concludes the questions for this round.")
        self.feedback = generate_feedback_and_scores(self.resume_text, round_name, self.interview_history)

    def display_feedback(self):
        """Print the generated feedback and scores."""
        if not self.feedback:
            print("\nNo feedback available.")
            return
        print("\n--- Interview Feedback ---")
        print(f"\nRound: {self.current_round_info['name']}")

        print("\n[Overall Feedback]")
        print(self.feedback.get("overall_feedback", "N/A"))

        print("\n[Suggestions For Improvement]")
        print(self.feedback.get("suggestions", "N/A"))

        print("\n[Scores per Question]")
        scores = self.feedback.get("scores_per_question", [])
        if scores and len(scores) == len(self.interview_history):
            for i, score in enumerate(scores):
                print(f" Q{i + 1}: {score}/10")
        elif scores:
            print(f" (Raw scores: {scores} - mismatch in count, check raw_output)")
        else:
            print(" Scores not available or parsing failed. ")

        print(f"\n[Total Score For Round]")
        print(f" {self.feedback.get('total_score', 'N/A')}/ {len(self.interview_history) * 10 if self.interview_history else 'N/A'}")

    def get_total_score(self) -> int | None:
        """Returns the total score for the last completion."""
        if self.feedback:
            return self.feedback.get("total_score")
        return None
