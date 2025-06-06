import os
from dotenv import load_dotenv

# 🔄 Load environment variables from .env.local
load_dotenv(dotenv_path=".env.local")

# 🌍 Deployment environment: "dev" or "prod"
ENV = os.getenv("ENV", "dev").lower()

# 🔐 Required API keys
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")

# 🚨 Validate required keys
if not INTERNAL_API_KEY:
    raise RuntimeError("❌ INTERNAL_API_KEY is missing in environment variables.")
if not WHISPER_API_KEY:
    raise RuntimeError("❌ WHISPER_API_KEY is missing in environment variables.")
if not WHISPER_API_URL:
    raise RuntimeError("❌ WHISPER_API_URL is missing in environment variables.")

# ⚙️ Default transcription parameters
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "english")
DEFAULT_RESPONSE_FORMAT = os.getenv("DEFAULT_RESPONSE_FORMAT", "verbose_json")
DEFAULT_TIMESTAMP_GRANULARITIES = os.getenv("DEFAULT_TIMESTAMP_GRANULARITIES", "segment").split(",")
DEFAULT_MIN_SPEAKERS = int(os.getenv("DEFAULT_MIN_SPEAKERS", 1))
DEFAULT_MAX_SPEAKERS = int(os.getenv("DEFAULT_MAX_SPEAKERS", 8))
DEFAULT_OUTPUT_FORMAT = os.getenv("DEFAULT_OUTPUT_FORMAT", "markdown")
DEFAULT_SPEAKER_LABELS = os.getenv("DEFAULT_SPEAKER_LABELS", "true").lower() == "true"
DEFAULT_TRANSLATE = os.getenv("DEFAULT_TRANSLATE", "false").lower() == "true"

# 👥 Allowed Telegram usernames for Mini App access
ALLOWED_USERNAMES = {
    username.strip().lower()
    for username in os.getenv("ALLOWED_USERNAMES", "").split(",")
    if username.strip()
}

# 🤖 Telegram bot token (optional)
BOT_TOKEN = os.getenv("BOT_TOKEN")
