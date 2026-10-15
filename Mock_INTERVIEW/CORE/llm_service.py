import random
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from UTILS.config import (
    FEEDBACK_OPENAI_API_KEY,
    FEEDBACK_OPENAI_BASE_URL,
    FEEDBACK_OPENAI_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    QUESTION_OPENAI_API_KEY,
)

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None


def _demo_completion(prompt: str, model: str = OPENAI_MODEL, max_tokens: int = 500, temperature: float = 0.7) -> str:
    """Return safe demo responses for presentations when the API key is unavailable."""
    lowered = prompt.lower()

    if "question" in lowered and "resume" in lowered:
        question_sets = {
            "hr": [
                "Which experience on your resume best prepared you for this role, and why?",
                "Tell me about a disagreement with a teammate and how you handled it.",
                "What accomplishment are you most proud of, and what was your contribution?",
                "What kind of team environment helps you do your best work?",
                "What are you hoping to learn or achieve in your next role?",
                "Describe a setback at work or school and how you responded.",
                "How do you prioritize when several important tasks are due at once?",
                "What motivates you to stay engaged in challenging work?",
                "How would a teammate describe your communication style?",
                "What strengths from your background would you bring to this team?",
            ],
            "technical": [
                "Choose a project from your resume and explain its architecture and key trade-offs.",
                "Describe a difficult bug you fixed and how you isolated its cause.",
                "How did you test the most important feature in one of your projects?",
                "What would you change if you rebuilt your strongest project today?",
                "How do you decide whether to optimize code for speed or maintainability?",
                "Explain how you would design a reliable API for a growing application.",
                "Tell me about a technology you learned recently and how you applied it.",
                "How do you investigate a performance problem in an application?",
                "Describe a technical decision where you considered multiple approaches.",
                "How would you protect user data in an application you built?",
            ],
            "managerial": [
                "Tell me about a project where you coordinated work across a team.",
                "How do you handle competing priorities for people on your team?",
                "Describe a time you gave difficult feedback and what happened afterward.",
                "How would you support a teammate who was missing agreed expectations?",
                "Tell me about a decision you made with incomplete information.",
                "How do you keep a team aligned when requirements change?",
                "Describe how you resolved conflict between collaborators.",
                "How do you decide what to delegate and what to handle yourself?",
                "What signals tell you a project is at risk, and what do you do next?",
                "How do you recognize and develop strengths in teammates?",
            ],
            "general": [
                "Walk me through the path that led you to your current career goals.",
                "What skill have you improved most recently, and how did you practice it?",
                "Describe a time you had to adapt quickly to an unexpected change.",
                "What type of problem do you most enjoy solving, and why?",
                "Tell me about a goal you set and how you tracked your progress.",
                "What would you like a future teammate to know about working with you?",
                "Describe a lesson you learned from a project that did not go as planned.",
                "How do you make sure you understand a task before starting it?",
                "Which part of your experience would you most like to build on next?",
                "What questions would help you decide whether this role is a good fit?",
            ],
        }
        round_key = next(
            (name for name in question_sets if f"for a '{name}' round" in lowered),
            "general",
        )
        questions = question_sets[round_key]
        previous_match = re.search(
            r"Do not repeat or lightly reword any question in this list:\s*\n(.*?)\nFormat the output",
            prompt,
            re.IGNORECASE | re.DOTALL,
        )
        previous_questions = set()
        if previous_match:
            previous_questions = {
                " ".join(line.lstrip("- ").casefold().split())
                for line in previous_match.group(1).splitlines()
                if line.strip() and line.strip() != "- None"
            }
        available_questions = [
            question
            for question in questions
            if " ".join(question.casefold().split()) not in previous_questions
        ]
        if not available_questions:
            return "[]"

        question_count = min(len(available_questions), max(1, max_tokens // 300 or 1))
        return str(random.sample(available_questions, question_count))

    if "overall feedback" in lowered or "suggestions" in lowered or "total score" in lowered:
        return (
            "Overall Feedback: Your answers are clear and structured, with strong examples from your experience. "
            "You can improve by adding more measurable impact and concise results.\n"
            "Suggestions: Highlight metrics, include the business outcome, and show decision-making in technical trade-offs.\n"
            "Scores per Question:\n"
            "Q1 Score: 8/10\n"
            "Q2 Score: 9/10\n"
            "Q3 Score: 8/10\n"
            "Total Score: 25/30"
        )

    return (
        "Overall Feedback: Demo mode is active because the configured AI provider is unavailable. "
        "The application is still running with sample interview content.\n"
        "Suggestions: Check the API key, endpoint, and configured model to enable live AI responses.\n"
        "Total Score: 0/0"
    )


# Initialize the LLM with LangChain only when configured
llm = None
if OPENAI_API_KEY and ChatOpenAI is not None:
    try:
        llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            temperature=0.7,
            max_tokens=500,
        )
    except Exception:
        llm = None


def _resolve_model_settings(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    use_feedback_key: bool = False,
) -> tuple[str | None, str, str]:
    resolved_api_key = api_key or (FEEDBACK_OPENAI_API_KEY if use_feedback_key else QUESTION_OPENAI_API_KEY) or OPENAI_API_KEY
    resolved_base_url = base_url or (FEEDBACK_OPENAI_BASE_URL if use_feedback_key else OPENAI_BASE_URL)
    resolved_model = model or (FEEDBACK_OPENAI_MODEL if use_feedback_key else OPENAI_MODEL)
    return resolved_api_key, resolved_base_url, resolved_model


def generate_completion(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 500,
    temperature: float = 0.7,
    allow_demo_fallback: bool = True,
    api_key: str | None = None,
    base_url: str | None = None,
    use_feedback_key: bool = False,
) -> str:
    """
    Generates text completion using LangChain and OpenAI.
    Falls back to demo responses when allowed and the AI service is unavailable.
    """
    resolved_api_key, resolved_base_url, resolved_model = _resolve_model_settings(
        api_key=api_key,
        base_url=base_url,
        model=model,
        use_feedback_key=use_feedback_key,
    )

    if not resolved_api_key or ChatOpenAI is None:
        if not allow_demo_fallback:
            if not resolved_api_key:
                raise RuntimeError("An OpenAI API key is required to generate real AI feedback.")
            raise RuntimeError("The AI provider dependency is unavailable; install langchain-openai.")
        print("OpenAI key missing; using demo fallback mode for presentation.")
        return _demo_completion(prompt, resolved_model, max_tokens, temperature)

    try:
        chat_model = ChatOpenAI(
            api_key=resolved_api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        messages = [
            SystemMessage(content="You are a helpful AI assistant."),
            HumanMessage(content=prompt),
        ]

        response = chat_model.invoke(messages)
        if response and getattr(response, "content", None):
            return response.content.strip()
        print("Warning: LLM response content is empty.")
        if not allow_demo_fallback:
            raise RuntimeError("The AI provider returned an empty response; no feedback was generated.")
        return _demo_completion(prompt, resolved_model, max_tokens, temperature)

    except Exception as e:
        print(f"Error during LLM completion: {e}")
        if not allow_demo_fallback:
            raise RuntimeError(
                "AI feedback generation failed. Check the API key, provider URL, model, and network connection."
            ) from e
        return _demo_completion(prompt, resolved_model, max_tokens, temperature)


    

    
    
# def generate_completion(prompt:str, model:str= "gpt-3.5-turbo",max_tokens:int= 500, temperature: float = 0.7) -> str:
#     try:
#         response = openai.chat.completions.create(
#             model=model,
#             messages=[
#                 {"role": "system", "content": "You are a helpful AI assistant."},
#                 {"role": "user", "content": prompt}
#             ],
#             max_tokens= max_tokens,
#             temperature= temperature,
#             n=1,
#             stop=None,
#         )
#         if response.choices and len(response.choices)>0:
#             if response.choices[0].message and response.choices[0].message.content:
#                 return response.choices[0].message.content.strip()
#             else:
#                 print("Warning: LLM response message or content is empty. ")
#                 return " Error: No Content in response. "
#         else:
#             print("Warning: LLM response choices list is empty.")
#             return " Error: No choice in response."
#     except openai.AuthenticationError as e:
#         print(f"OpenAI Authentication Error: {e}")
#         print("Please check your OPENAI_AI_KEY in the. env file.")
#     except openai.RateLimitError as e:
#         print(f"OpenAI Rate Limit Error: {e}")
#         return " Error: OpenAI Rate Limit Exceed."
#     except Exception as e:
#         print(f"Error during OpenAI API call: {e}")
#         return f"Error: Could not generate completion- {e}"