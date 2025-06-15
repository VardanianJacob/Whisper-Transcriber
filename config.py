import os
import secrets
import logging
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger(__name__)

# 🔄 Load environment variables from .env.local
load_dotenv(dotenv_path=".env.local")

# 🌍 Deployment environment: "dev" or "prod"
ENV = os.getenv("ENV", "dev").lower()

# 🤖 Claude API configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = os.getenv("CLAUDE_API_URL", "https://api.anthropic.com/v1/messages")

# Логирование статуса Claude API (не блокируем запуск если нет ключа)
if CLAUDE_API_KEY:
    logger.info("🧠 Claude API key found - AI analysis available")
else:
    logger.warning("⚠️ CLAUDE_API_KEY not found - Claude analysis will be unavailable")

# 🤖 Telegram bot token - required for sending reports
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.warning("⚠️ TELEGRAM_BOT_TOKEN not found - report sending will be unavailable")

# 🔐 Whisper API - обязательные для транскрипции
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
WHISPER_API_URL = os.getenv("WHISPER_API_URL", "https://api.openai.com/v1/audio/transcriptions")

# Проверяем обязательные ключи
if not WHISPER_API_KEY:
    raise RuntimeError("❌ WHISPER_API_KEY is missing in environment variables.")
if not WHISPER_API_URL:
    raise RuntimeError("❌ WHISPER_API_URL is missing in environment variables.")

logger.info("🎤 Whisper API configured successfully")


# ⚙️ Default transcription parameters with safe parsing
def safe_int(value, default):
    """Safe conversion to int with fallback."""
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default


def safe_bool(value, default):
    """Safe conversion to bool."""
    if value is None:
        return default
    return str(value).lower() in ("true", "1", "yes", "on")


def safe_list(value, default, separator=","):
    """Safe conversion to list with filtering."""
    if not value:
        return default
    items = [item.strip() for item in value.split(separator) if item.strip()]
    return items if items else default


DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "english")
DEFAULT_RESPONSE_FORMAT = os.getenv("DEFAULT_RESPONSE_FORMAT", "verbose_json")
DEFAULT_TIMESTAMP_GRANULARITIES = safe_list(
    os.getenv("DEFAULT_TIMESTAMP_GRANULARITIES"),
    ["segment"]
)
DEFAULT_MIN_SPEAKERS = safe_int(os.getenv("DEFAULT_MIN_SPEAKERS"), 1)
DEFAULT_MAX_SPEAKERS = safe_int(os.getenv("DEFAULT_MAX_SPEAKERS"), 8)
DEFAULT_OUTPUT_FORMAT = os.getenv("DEFAULT_OUTPUT_FORMAT", "markdown")
DEFAULT_SPEAKER_LABELS = safe_bool(os.getenv("DEFAULT_SPEAKER_LABELS"), True)
DEFAULT_TRANSLATE = safe_bool(os.getenv("DEFAULT_TRANSLATE"), False)

# 👥 Security - allowed usernames (опционально для dev)
ALLOWED_USERNAMES_STR = os.getenv("ALLOWED_USERNAMES", "")
ALLOWED_USERNAMES = {
    username.strip().lower()
    for username in ALLOWED_USERNAMES_STR.split(",")
    if username.strip()
}

# В dev режиме не требуем пользователей
if ENV == "prod" and not ALLOWED_USERNAMES:
    logger.warning("⚠️ ALLOWED_USERNAMES not set in production mode")

if ENV == "dev" and not ALLOWED_USERNAMES:
    logger.info("ℹ️ No ALLOWED_USERNAMES set for development - all users allowed")

# 🔑 JWT settings with secure defaults
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET:
    if ENV == "prod":
        logger.warning("⚠️ JWT_SECRET not found, generating temporary key")
    # Generate random key
    JWT_SECRET = secrets.token_urlsafe(32)
    logger.info(f"🔑 Using generated JWT key: {JWT_SECRET[:10]}...")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_MINUTES = safe_int(os.getenv("JWT_EXPIRES_MINUTES"), 30)

# 📊 Value validation and correction
if JWT_EXPIRES_MINUTES < 1:
    JWT_EXPIRES_MINUTES = 30
    logger.warning("⚠️ JWT_EXPIRES_MINUTES must be positive, using default 30")

if DEFAULT_MIN_SPEAKERS < 1 or DEFAULT_MIN_SPEAKERS > DEFAULT_MAX_SPEAKERS:
    logger.warning("⚠️ Invalid speaker range, using defaults")
    DEFAULT_MIN_SPEAKERS = 1
    DEFAULT_MAX_SPEAKERS = 8


# 📋 Configuration class for server.py
class Config:
    """Configuration class for FastAPI server"""
    JWT_SECRET = JWT_SECRET
    JWT_ALGORITHM = JWT_ALGORITHM
    JWT_EXPIRES_MINUTES = JWT_EXPIRES_MINUTES

    CLAUDE_API_KEY = CLAUDE_API_KEY
    CLAUDE_API_URL = CLAUDE_API_URL

    WHISPER_API_KEY = WHISPER_API_KEY
    WHISPER_API_URL = WHISPER_API_URL

    TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN

    DEFAULT_LANGUAGE = DEFAULT_LANGUAGE
    DEFAULT_OUTPUT_FORMAT = DEFAULT_OUTPUT_FORMAT
    DEFAULT_MIN_SPEAKERS = DEFAULT_MIN_SPEAKERS
    DEFAULT_MAX_SPEAKERS = DEFAULT_MAX_SPEAKERS

    ENV = ENV
    ALLOWED_USERNAMES = ALLOWED_USERNAMES


# 📋 Configuration summary for debugging
if ENV == "dev":
    logger.info(f"🔧 Config loaded: ENV={ENV}, Users={len(ALLOWED_USERNAMES)}, JWT_expires={JWT_EXPIRES_MINUTES}min")
    if ALLOWED_USERNAMES:
        logger.info(f"👥 Allowed users: {', '.join(sorted(ALLOWED_USERNAMES))}")
    else:
        logger.info("ℹ️ No users configured - all users allowed in dev mode")

    # Claude status for dev mode
    claude_status = "✅ Available" if CLAUDE_API_KEY else "❌ Not configured"
    telegram_status = "✅ Available" if TELEGRAM_BOT_TOKEN else "❌ Not configured"
    logger.info(f"🧠 Claude API: {claude_status}")
    logger.info(f"📱 Telegram Bot: {telegram_status}")