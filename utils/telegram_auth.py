import hmac
import hashlib
import logging
import os
import json
import time
from urllib.parse import parse_qsl
from config import BOT_TOKEN, ENV

logger = logging.getLogger(__name__)

# Максимальный возраст данных от Telegram (в секундах)
MAX_AUTH_AGE = 24 * 60 * 60  # 24 часа


def verify_telegram_init_data(init_data: str) -> dict:
    """
    Verify the Telegram WebApp initData hash and return parsed data if valid.
    In development mode (ENV=dev), always return a test username for local testing.

    Args:
        init_data: URL-encoded string from Telegram WebApp

    Returns:
        dict: {"username": str, "user_data": dict, "user_id": int}

    Raises:
        ValueError: If validation fails
    """
    if ENV == "dev":
        # WARNING: This stub is for local development only!
        dev_username = os.getenv("DEV_USERNAME")
        logger.info(f"🔧 DEV mode: using username '{dev_username}'")
        return {
            "username": dev_username,
            "user_data": {"username": dev_username, "id": 12345},
            "user_id": 12345
        }

    # Проверяем что BOT_TOKEN установлен
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set")
        raise ValueError("Server configuration error")

    # Parse initData from URL-encoded string to dictionary
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception as e:
        logger.error(f"Failed to parse initData: {e}")
        raise ValueError("Invalid initData format")

    hash_received = parsed.pop("hash", None)
    if not hash_received:
        logger.error("Missing hash in initData")
        raise ValueError("Missing hash in initData")

    # Проверяем срок действия данных
    auth_date = parsed.get("auth_date")
    if auth_date:
        try:
            auth_timestamp = int(auth_date)
            current_time = int(time.time())
            age = current_time - auth_timestamp

            if age > MAX_AUTH_AGE:
                logger.warning(f"Auth data too old: {age} seconds")
                raise ValueError("Authentication data expired")

            logger.debug(f"Auth data age: {age} seconds")
        except (ValueError, TypeError):
            logger.error(f"Invalid auth_date format: {auth_date}")
            raise ValueError("Invalid auth_date")

    # Build data check string in alphabetical order
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    # Генерируем secret key согласно документации Telegram
    try:
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate hash: {e}")
        raise ValueError("Hash calculation failed")

    # Securely compare calculated hash and received hash
    if not hmac.compare_digest(calculated_hash, hash_received):
        logger.error("Hash validation failed")
        # НЕ логируем сами хеши в продакшене для безопасности
        if ENV == "dev":
            logger.debug(f"Expected: {calculated_hash}, Got: {hash_received}")
            logger.debug(f"Data check string: {data_check_string}")
        raise ValueError("Invalid initData signature")

    logger.info("Telegram signature validation successful")

    # Извлекаем и валидируем данные пользователя
    try:
        user_json = parsed.get("user", "{}")
        user_data = json.loads(user_json)

        # Проверяем обязательные поля
        user_id = user_data.get("id")
        if not isinstance(user_id, int):
            logger.error(f"Invalid user_id type: {type(user_id)}")
            raise ValueError("Invalid user_id")

        username = user_data.get("username", "").strip().lower()
        if not username:
            logger.error("Username missing in user data")
            raise ValueError("Username required")

        logger.info(f"✅ User authenticated: {username} (ID: {user_id})")

        return {
            "username": username,
            "user_data": user_data,
            "user_id": user_id
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse user JSON: {e}")
        raise ValueError("Invalid user data format")
    except Exception as e:
        logger.error(f"User data validation failed: {e}")
        raise ValueError("User data validation failed")