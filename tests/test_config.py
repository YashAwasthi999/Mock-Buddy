import importlib
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOCK_INTERVIEW_ROOT = PROJECT_ROOT / "Mock_INTERVIEW"
if str(MOCK_INTERVIEW_ROOT) not in sys.path:
    sys.path.insert(0, str(MOCK_INTERVIEW_ROOT))


class ConfigTests(unittest.TestCase):
    def test_config_does_not_crash_when_env_keys_are_missing(self):
        for key in [
            "OpenAi_API_key",
            "OPENAI_API_KEY",
            "Eleven_labs_API_key",
            "Elevenlabs_API_key",
            "ELEVENLABS_API_KEY",
            "Elevenlabs_voice_id",
            "ELEVENLABS_VOICE_ID",
        ]:
            os.environ[key] = ""

        sys.modules.pop("UTILS.config", None)
        config = importlib.import_module("UTILS.config")

        self.assertTrue(config.OPENAI_API_KEY in (None, ""))
        self.assertTrue(config.ELEVENLABS_API_KEY in (None, ""))


if __name__ == "__main__":
    unittest.main()
