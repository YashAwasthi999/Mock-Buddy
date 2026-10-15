import json
import re

from CORE.llm_service import generate_completion
from PROMPTS.feedback_prompts import get_feedback_prompt
from UTILS.config import FEEDBACK_OPENAI_API_KEY, FEEDBACK_OPENAI_BASE_URL, FEEDBACK_OPENAI_MODEL, OPENAI_API_KEY


def _parse_json_feedback(raw_feedback: str) -> dict | None:
    response = raw_feedback.strip()
    if response.startswith("```"):
        response = re.sub(r"^```(?:json)?\s*|\s*```$", "", response, flags=re.IGNORECASE).strip()

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _parse_labeled_feedback(raw_feedback: str) -> dict:
    overall_match = re.search(
        r"Overall Feedback:\s*(.*?)(?=\n\s*Suggestions:|\Z)",
        raw_feedback,
        re.IGNORECASE | re.DOTALL,
    )
    suggestions_match = re.search(
        r"Suggestions:\s*(.*?)(?=\n\s*Scores? per Question:|\n\s*Total Score:|\Z)",
        raw_feedback,
        re.IGNORECASE | re.DOTALL,
    )
    scores = [
        int(match.group(1))
        for match in re.finditer(
            r"\bQ\s*\d+\s*(?:Score)?\s*:\s*(\d+)\s*/\s*10\b",
            raw_feedback,
            re.IGNORECASE,
        )
    ]

    return {
        "overall_feedback": overall_match.group(1).strip() if overall_match else "",
        "suggestions": suggestions_match.group(1).strip() if suggestions_match else "",
        "scores_per_question": scores,
    }


def generate_feedback_and_scores(resume_text: str, round_name: str, qa_pairs: list[dict]) -> dict:
    """Generate and validate real AI feedback and scores for an interview round."""
    if not qa_pairs:
        raise ValueError("At least one answered question is required to generate feedback.")

    prompt = get_feedback_prompt(resume_text, round_name, qa_pairs)
    raw_feedback = generate_completion(
        prompt,
        model=FEEDBACK_OPENAI_MODEL,
        max_tokens=1500,
        temperature=0.3,
        allow_demo_fallback=False,
        api_key=FEEDBACK_OPENAI_API_KEY or OPENAI_API_KEY,
        base_url=FEEDBACK_OPENAI_BASE_URL,
        use_feedback_key=True,
    )

    feedback_data = _parse_json_feedback(raw_feedback)
    if feedback_data is None:
        feedback_data = _parse_labeled_feedback(raw_feedback)

    overall_feedback = feedback_data.get("overall_feedback")
    suggestions = feedback_data.get("suggestions")
    scores = feedback_data.get("scores_per_question")

    if not isinstance(overall_feedback, str) or not overall_feedback.strip():
        raise ValueError("The AI response did not include overall feedback.")
    if not isinstance(suggestions, str) or not suggestions.strip():
        raise ValueError("The AI response did not include suggestions for improvement.")
    if (
        not isinstance(scores, list)
        or len(scores) != len(qa_pairs)
        or any(type(score) is not int or not 0 <= score <= 10 for score in scores)
    ):
        raise ValueError(
            f"The AI response must include one score from 0 to 10 for each of "
            f"the {len(qa_pairs)} interview answers."
        )

    return {
        "overall_feedback": overall_feedback.strip(),
        "suggestions": suggestions.strip(),
        "scores_per_question": scores,
        "total_score": sum(scores),
        "raw_output": raw_feedback,
    }
