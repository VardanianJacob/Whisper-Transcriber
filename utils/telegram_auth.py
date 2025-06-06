import hmac
import hashlib
import logging
from urllib.parse import parse_qsl
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

def verify_telegram_init_data(init_data: str) -> dict:
    """✅ Verify Telegram WebApp initData hash and return parsed data if valid."""
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_received = parsed.pop("hash", None)

    if not hash_received:
        raise ValueError("Missing hash in initData")

    # 🔐 Собираем строку для подписи
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    # 🔑 Генерируем секретный ключ и хеш
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # ❌ Проверка валидности
    if not hmac.compare_digest(calculated_hash, hash_received):
        raise ValueError("Invalid initData signature")

    # ✅ Логируем распарсенные данные
    logger.info(f"✅ Parsed initData: {parsed}")

    return parsed  # содержит user id, username и пр.
