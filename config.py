import os
from dotenv import load_dotenv

load_dotenv()  # <-- Обязательно!

# 🔐 API settings
WHISPER_API_URL = "https://api.lemonfox.ai/v1/audio/transcriptions"
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")

# ⚙️ Default transcription parameters
DEFAULT_LANGUAGE = "english"
DEFAULT_RESPONSE_FORMAT = "verbose_json"
DEFAULT_TIMESTAMP_GRANULARITIES = ["segment"]
DEFAULT_MIN_SPEAKERS = 2
DEFAULT_MAX_SPEAKERS = 5
DEFAULT_OUTPUT_FORMAT = "markdown"
DEFAULT_SPEAKER_LABELS = True
DEFAULT_TRANSLATE = False
