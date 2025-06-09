import logging
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRES_MINUTES

logger = logging.getLogger(__name__)

# JWT issuer identifier
JWT_ISSUER = "whisper-api"
JWT_AUDIENCE = "whisper-api-users"


def create_access_token(username: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a JWT token for the given username.

    Args:
        username: User identifier (must be non-empty)
        additional_claims: Optional extra claims to include

    Returns:
        str: Encoded JWT token

    Raises:
        ValueError: If username is invalid
        JWTError: If token creation fails
    """
    if not username or not isinstance(username, str):
        raise ValueError("Username must be a non-empty string")

    username = username.strip()
    if not username:
        raise ValueError("Username cannot be empty or whitespace")

    now = datetime.utcnow()
    expire = now + timedelta(minutes=JWT_EXPIRES_MINUTES)

    payload = {
        "sub": username,  # Subject (username)
        "exp": expire,  # Expiration time
        "iat": now,  # Issued at
        "iss": JWT_ISSUER,  # Issuer
        "aud": JWT_AUDIENCE,  # Audience
        "type": "access"  # Token type
    }

    # Add any additional claims
    if additional_claims:
        payload.update(additional_claims)

    try:
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.info(f"Access token created for user: {username}")
        return token
    except Exception as e:
        logger.error(f"Failed to create token for {username}: {e}")
        raise JWTError(f"Token creation failed: {str(e)}")


def verify_access_token(token: str) -> str:
    """
    Verify a JWT token and return the username if valid.

    Args:
        token: JWT token string

    Returns:
        str: Username from token

    Raises:
        ValueError: If token format is invalid
        JWTError: If token is invalid, expired, or malformed
    """
    if not token or not isinstance(token, str):
        raise ValueError("Token must be a non-empty string")

    token = token.strip()
    if not token:
        raise ValueError("Token cannot be empty")

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER
        )

        username = payload.get("sub")
        if not username:
            logger.warning("Token missing 'sub' claim")
            raise JWTError("Invalid token: missing username")

        # Verify token type if present
        token_type = payload.get("type")
        if token_type and token_type != "access":
            logger.warning(f"Invalid token type: {token_type}")
            raise JWTError("Invalid token type")

        logger.debug(f"Token verified for user: {username}")
        return username

    except jwt.ExpiredSignatureError:
        logger.info("Token has expired")
        raise JWTError("Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise JWTError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise JWTError(f"Token verification failed: {str(e)}")


def decode_token_payload(token: str) -> Dict[str, Any]:
    """
    Decode JWT token without verification (for debugging/inspection).

    Args:
        token: JWT token string

    Returns:
        dict: Token payload

    Raises:
        JWTError: If token cannot be decoded
    """
    if not token:
        raise ValueError("Token cannot be empty")

    try:
        # Decode without verification for inspection
        payload = jwt.get_unverified_claims(token)
        return payload
    except Exception as e:
        logger.error(f"Failed to decode token payload: {e}")
        raise JWTError(f"Cannot decode token: {str(e)}")


def is_token_expired(token: str) -> bool:
    """
    Check if token is expired without full verification.

    Args:
        token: JWT token string

    Returns:
        bool: True if expired, False otherwise
    """
    try:
        payload = decode_token_payload(token)
        exp = payload.get("exp")
        if not exp:
            return True

        exp_datetime = datetime.utcfromtimestamp(exp)
        return datetime.utcnow() > exp_datetime
    except:
        return True  # Assume expired if we can't decode