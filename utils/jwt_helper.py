from jose import jwt, JWTError
from datetime import datetime, timedelta
from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRES_MINUTES

def create_access_token(username: str) -> str:
    """
    Generate a JWT token for the given username.
    """
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRES_MINUTES)
    payload = {
        "sub": username,
        "exp": expire
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_access_token(token: str) -> str:
    """
    Verify a JWT token and return the username if valid.
    Raises JWTError if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise JWTError("No username in token")
        return username
    except JWTError as e:
        raise
