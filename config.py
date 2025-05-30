import os
from dotenv import load_dotenv

load_dotenv()

# 🌍 Deployment environment
ENV = os.getenv("ENV", "dev")  # "dev" or "prod"

# 🔐 Access protection
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

# 🧠 Whisper API credentials
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")

# ⚙️ Default transcription parameters
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "english")
DEFAULT_RESPONSE_FORMAT = os.getenv("DEFAULT_RESPONSE_FORMAT", "verbose_json")
DEFAULT_TIMESTAMP_GRANULARITIES = os.getenv("DEFAULT_TIMESTAMP_GRANULARITIES", "segment").split(",")
DEFAULT_MIN_SPEAKERS = int(os.getenv("DEFAULT_MIN_SPEAKERS", 1))
DEFAULT_MAX_SPEAKERS = int(os.getenv("DEFAULT_MAX_SPEAKERS", 8))
DEFAULT_OUTPUT_FORMAT = os.getenv("DEFAULT_OUTPUT_FORMAT", "markdown")
DEFAULT_SPEAKER_LABELS = os.getenv("DEFAULT_SPEAKER_LABELS", "true").lower() == "true"
DEFAULT_TRANSLATE = os.getenv("DEFAULT_TRANSLATE", "false").lower() == "true"
