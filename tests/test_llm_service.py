import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("OpenAi_API_key", "test-key")

project_root = Path(__file__).resolve().parents[1]
mock_interview_root = project_root / "Mock_INTERVIEW"
if str(mock_interview_root) not in sys.path:
    sys.path.insert(0, str(mock_interview_root))

from CORE import llm_service


class LLMServiceTests(unittest.TestCase):
    def test_generate_completion_uses_openai_client(self):
        fake_response = SimpleNamespace(content="  hello world  ")

        with patch("CORE.llm_service.OPENAI_API_KEY", "test-key"):
            with patch("CORE.llm_service.ChatOpenAI") as mock_client:
                mock_client.return_value.invoke.return_value = fake_response

                result = llm_service.generate_completion("Say hello")

                self.assertEqual(result, "hello world")
                mock_client.return_value.invoke.assert_called_once()

    def test_feedback_completion_uses_feedback_provider_settings(self):
        fake_response = SimpleNamespace(content="feedback")

        with patch.object(llm_service, "QUESTION_OPENAI_API_KEY", "question-key"):
            with patch.object(llm_service, "FEEDBACK_OPENAI_API_KEY", "feedback-key"):
                with patch.object(llm_service, "FEEDBACK_OPENAI_BASE_URL", "https://api.groq.com/openai/v1"):
                    with patch.object(llm_service, "FEEDBACK_OPENAI_MODEL", "openai/gpt-oss-120b"):
                        with patch.object(llm_service, "ChatOpenAI") as mock_client:
                            mock_client.return_value.invoke.return_value = fake_response

                            result = llm_service.generate_completion(
                                "Generate feedback",
                                allow_demo_fallback=False,
                                use_feedback_key=True,
                            )

                            self.assertEqual(result, "feedback")
                            mock_client.assert_called_once()
                            self.assertEqual(
                                mock_client.call_args.kwargs["api_key"],
                                "feedback-key",
                            )
                            self.assertEqual(
                                mock_client.call_args.kwargs["base_url"],
                                "https://api.groq.com/openai/v1",
                            )
                            self.assertEqual(
                                mock_client.call_args.kwargs["model"],
                                "openai/gpt-oss-120b",
                            )

    def test_live_completion_requires_api_key_instead_of_demo_feedback(self):
        with patch.object(llm_service, "OPENAI_API_KEY", None):
            with patch.object(llm_service, "QUESTION_OPENAI_API_KEY", None):
                with patch.object(llm_service, "FEEDBACK_OPENAI_API_KEY", None):
                    with patch.object(llm_service, "_demo_completion") as demo_completion:
                        with self.assertRaisesRegex(RuntimeError, "API key is required"):
                            llm_service.generate_completion(
                                "Generate feedback",
                                allow_demo_fallback=False,
                            )

                        demo_completion.assert_not_called()

    def test_live_completion_errors_instead_of_using_demo_fallback(self):
        with patch.object(llm_service, "OPENAI_API_KEY", "test-key"):
            with patch.object(llm_service, "ChatOpenAI") as mock_client:
                with patch.object(llm_service, "_demo_completion") as demo_completion:
                    mock_client.return_value.invoke.side_effect = RuntimeError("provider unavailable")

                    with self.assertRaisesRegex(RuntimeError, "AI feedback generation failed"):
                        llm_service.generate_completion(
                            "Generate feedback",
                            allow_demo_fallback=False,
                        )

                    demo_completion.assert_not_called()


if __name__ == "__main__":
    unittest.main()
