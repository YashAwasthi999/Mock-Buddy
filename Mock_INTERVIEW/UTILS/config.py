import os
from pathlib import Path

try:
    import streamlit as st
except ImportError:
    st = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def _get_first_env(*keys):
    for key in keys:
        value = os.getenv(key)
        if value in (None, "") and st is not None:
            try:
                value = st.secrets.get(key)
            except Exception:
                value = None
        if value not in (None, ""):
            return value
    return None


QUESTION_OPENAI_API_KEY = _get_first_env(
    "QUESTION_OPENAI_API_KEY",
    "QUESTION_API_KEY",
    "OpenAi_API_key",
    "OPENAI_API_KEY",
    "OpenAI_API_key",
)
FEEDBACK_OPENAI_API_KEY = _get_first_env(
    "FEEDBACK_OPENAI_API_KEY",
    "FEEDBACK_API_KEY",
    "FEEDBACK_OPENAI_APIKEY",
    "OpenAi_API_key",
    "OPENAI_API_KEY",
    "OpenAI_API_key",
)
OPENAI_API_KEY = QUESTION_OPENAI_API_KEY

OPENAI_BASE_URL = _get_first_env("OPENAI_BASE_URL", "OPENAI_BASEURL") or "https://api.openai.com/v1"
_FEEDBACK_BASE_URL = _get_first_env(
    "FEEDBACK_OPENAI_BASE_URL",
    "FEEDBACK_OPENAI_BASEURL",
)
if _FEEDBACK_BASE_URL:
    FEEDBACK_OPENAI_BASE_URL = _FEEDBACK_BASE_URL
elif FEEDBACK_OPENAI_API_KEY and FEEDBACK_OPENAI_API_KEY.startswith("gsk_"):
    FEEDBACK_OPENAI_BASE_URL = "https://api.groq.com/openai/v1"
else:
    FEEDBACK_OPENAI_BASE_URL = OPENAI_BASE_URL
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
OPENAI_MODEL = _get_first_env("OPENAI_MODEL", "MODEL") or (
    GROQ_DEFAULT_MODEL if "groq.com" in OPENAI_BASE_URL.lower() else "gpt-3.5-turbo"
)
FEEDBACK_OPENAI_MODEL = _get_first_env("FEEDBACK_OPENAI_MODEL", "FEEDBACK_MODEL") or (
    GROQ_DEFAULT_MODEL
    if "groq.com" in FEEDBACK_OPENAI_BASE_URL.lower()
    else OPENAI_MODEL
)

ELEVENLABS_API_KEY = _get_first_env("Eleven_labs_API_key", "Elevenlabs_API_key", "ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = _get_first_env("Elevenlabs_voice_id", "ELEVENLABS_VOICE_ID") or "Viraj"

QUESTION_DEMO_MODE = not bool(QUESTION_OPENAI_API_KEY or OPENAI_API_KEY)
FEEDBACK_DEMO_MODE = not bool(FEEDBACK_OPENAI_API_KEY or OPENAI_API_KEY)
DEMO_MODE = QUESTION_DEMO_MODE or FEEDBACK_DEMO_MODE

RECORDING_SAMPLE_RATE = 44100
RECORDING_CHANNELS = 1
RECORDING_DURATION_SECONDS = 10
TEMP_AUDIO_FILENAME = str(
    Path(__file__).resolve().parents[2]
    / "Mock_INTERVIEW"
    / "DATA"
    / "uploads"
    / "temp_user_response.wav"
)