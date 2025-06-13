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

# 🔐 Required API keys
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")

# 🚨 Validate required keys presence
if not WHISPER_API_KEY:
    raise RuntimeError("❌ WHISPER_API_KEY is missing in environment variables.")
if not WHISPER_API_URL:
    raise RuntimeError("❌ WHISPER_API_URL is missing in environment variables.")

# 🤖 Claude API configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = os.getenv("CLAUDE_API_URL", "https://api.anthropic.com/v1/messages")

# Логирование статуса Claude API (не блокируем запуск если нет ключа)
if CLAUDE_API_KEY:
    logger.info("🧠 Claude API key found - AI analysis available")
else:
    logger.warning("⚠️ CLAUDE_API_KEY not found - Claude analysis will be unavailable")

# 🤖 Telegram bot token - required for prod mode
BOT_TOKEN = os.getenv("BOT_TOKEN")
if ENV == "prod" and not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is required in production mode.")


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

# 👥 Security - allowed usernames from environment variable
# Set via: fly secrets set ALLOWED_USERNAMES="user1,user2,user3" -a whisperapi
ALLOWED_USERNAMES_STR = os.getenv("ALLOWED_USERNAMES", "")
ALLOWED_USERNAMES = {
    username.strip().lower()
    for username in ALLOWED_USERNAMES_STR.split(",")
    if username.strip()
}

# Validate that at least one user exists in prod
if ENV == "prod" and not ALLOWED_USERNAMES:
    raise RuntimeError(
        "❌ ALLOWED_USERNAMES must be set in production mode. Use: fly secrets set ALLOWED_USERNAMES='user1,user2' -a whisperapi")

# Warning for development mode if no users set
if ENV == "dev" and not ALLOWED_USERNAMES:
    logger.warning("⚠️ No ALLOWED_USERNAMES set for development. Set via environment variable or .env.local file.")

# 🔑 JWT settings with secure defaults
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    if ENV == "prod":
        raise RuntimeError("❌ JWT_SECRET_KEY is required in production mode.")
    else:
        # Generate random key for dev mode
        JWT_SECRET_KEY = secrets.token_urlsafe(32)
        print(f"⚠️ Using generated JWT key for dev mode: {JWT_SECRET_KEY}")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_MINUTES = safe_int(os.getenv("JWT_EXPIRES_MINUTES"), 30)

# 📊 Value validation and correction
if JWT_EXPIRES_MINUTES < 1:
    JWT_EXPIRES_MINUTES = 30
    print("⚠️ JWT_EXPIRES_MINUTES must be positive, using default 30")

if DEFAULT_MIN_SPEAKERS < 1 or DEFAULT_MIN_SPEAKERS > DEFAULT_MAX_SPEAKERS:
    print("⚠️ Invalid speaker range, using defaults")
    DEFAULT_MIN_SPEAKERS = 1
    DEFAULT_MAX_SPEAKERS = 8

# 📋 Configuration summary for debugging
if ENV == "dev":
    print(f"🔧 Config loaded: ENV={ENV}, Users={len(ALLOWED_USERNAMES)}, JWT_expires={JWT_EXPIRES_MINUTES}min")
    if ALLOWED_USERNAMES:
        print(f"👥 Allowed users: {', '.join(sorted(ALLOWED_USERNAMES))}")
    else:
        print("⚠️ No users configured - access will be denied")

    # Claude status for dev mode
    claude_status = "✅ Available" if CLAUDE_API_KEY else "❌ Not configured"
    print(f"🧠 Claude API: {claude_status}")