import hmac
import hashlib
import logging
import os
import json
from urllib.parse import parse_qsl
from config import BOT_TOKEN, ENV

logger = logging.getLogger(__name__)


def verify_telegram_init_data(init_data: str) -> dict:
    """
    Verify the Telegram WebApp initData hash and return parsed data if valid.
    In development mode (ENV=dev), always return a test username for local testing.
    """
    if ENV == "dev":
        # WARNING: This stub is for local development only!
        # Never use in production!
        dev_username = os.getenv("DEV_USERNAME")
        return {"username": dev_username}  # Username should exist in ALLOWED_USERNAMES

    # Parse initData from URL-encoded string to dictionary
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_received = parsed.pop("hash", None)

    if not hash_received:
        raise ValueError("Missing hash in initData")

    # Build data check string in alphabetical order
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    # ИСПРАВЛЕНО: Правильная генерация secret key согласно документации Telegram
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # Securely compare calculated hash and received hash
    if not hmac.compare_digest(calculated_hash, hash_received):
        logger.error(f"Hash mismatch. Expected: {calculated_hash}, Got: {hash_received}")
        logger.error(f"Data check string: {data_check_string}")
        raise ValueError("Invalid initData signature")

    logger.info(f"Parsed initData: {parsed}")

    # ИСПРАВЛЕНО: Извлекаем username из JSON строки user
    try:
        user_data = json.loads(parsed.get("user", "{}"))
        username = user_data.get("username", "").lower()
        logger.info(f"🔍 Extracted username: {username}")

        # Возвращаем структуру которую ожидает server.py
        return {"username": username, "user_data": user_data}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse user data: {e}")
        raise ValueError("Invalid user data in initData")