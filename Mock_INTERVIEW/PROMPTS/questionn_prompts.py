def get_question_generation_prompt(
    resume_text: str,
    round_name: str,
    num_questions: int,
    previous_questions: list[str] | None = None,
) -> str:
    """Create a prompt to generate interview questions."""

    round_instructions = {
        "HR": "Focus on behavioral questions, cultural fit, salary expectations(ask indirectly), and general background.",
        "Technical": "Focus on specific technical skills, technologies , and project experiences mentioned in the resume. Ask problem-solving or coding concepts questionn relevant to the skills.",
        "Managerial": "Focus on leadership potential, team collaboration , conflict resolution, project manaagement approaches, and career goals.",
        "General": "Ask a mix of behavioral , situational , and resume- based questions."
    }

    instructions = round_instructions.get(round_name, round_instructions["General"])
    previous_questions_text = "\n".join(
        f"- {question}" for question in (previous_questions or [])
    ) or "- None"

    prompt = f"""
Based on the following resume text, genertate {num_questions} relevant interview questions for a '{round_name}' round. {instructions}
Ensure the questions are open-ended and encourage detailed answers. Do not ask questions that can be answered with a simple 'yes
or 'no'. 
Do not repeat or lightly reword any question in this list:
{previous_questions_text}
Format the output as a Python list of strings, like this:
["Question 1?", "Question 2?", "Question 3?"]

Resume Text:
___
{resume_text}
___

Generate the list of questions now:
"""
    return prompt

