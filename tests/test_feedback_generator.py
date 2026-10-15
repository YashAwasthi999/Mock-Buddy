import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parents[1]
mock_interview_root = project_root / "Mock_INTERVIEW"
if str(mock_interview_root) not in sys.path:
    sys.path.insert(0, str(mock_interview_root))

from CORE.feedback_generator import generate_feedback_and_scores


class FeedbackGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.qa_pairs = [
            {"question": "Describe a project.", "answer": "I built a project."},
            {"question": "How did you test it?", "answer": "I wrote unit tests."},
        ]

    @patch("CORE.feedback_generator.generate_completion")
    def test_parses_ai_json_and_calculates_total_from_all_answers(self, generate_completion):
        generate_completion.return_value = json.dumps(
            {
                "overall_feedback": "The answers were relevant.",
                "suggestions": "Add measurable project outcomes.",
                "scores_per_question": [7, 9],
            }
        )

        result = generate_feedback_and_scores("Candidate resume", "Technical", self.qa_pairs)

        self.assertEqual(result["overall_feedback"], "The answers were relevant.")
        self.assertEqual(result["suggestions"], "Add measurable project outcomes.")
        self.assertEqual(result["scores_per_question"], [7, 9])
        self.assertEqual(result["total_score"], 16)
        generate_completion.assert_called_once()
        self.assertFalse(generate_completion.call_args.kwargs["allow_demo_fallback"])

    @patch("CORE.feedback_generator.generate_completion")
    def test_parses_legacy_labeled_feedback(self, generate_completion):
        generate_completion.return_value = (
            "Overall Feedback: Strong, relevant answers.\n"
            "Suggestions: Include more measurable outcomes.\n"
            "Scores per Question:\n"
            "Q1 Score: 8/10\n"
            "Q2 Score: 6/10\n"
            "Total Score: 14/20"
        )

        result = generate_feedback_and_scores("Candidate resume", "Technical", self.qa_pairs)

        self.assertEqual(result["scores_per_question"], [8, 6])
        self.assertEqual(result["total_score"], 14)

    @patch("CORE.feedback_generator.generate_completion")
    def test_rejects_missing_ai_scores_instead_of_returning_zeroes(self, generate_completion):
        generate_completion.return_value = json.dumps(
            {
                "overall_feedback": "The answers were relevant.",
                "suggestions": "Add more detail.",
                "scores_per_question": [8],
            }
        )

        with self.assertRaisesRegex(ValueError, "one score.*for each"):
            generate_feedback_and_scores("Candidate resume", "Technical", self.qa_pairs)


if __name__ == "__main__":
    unittest.main()
