from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
import jwt

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with a generated salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("ascii"),
        )
    except Exception:
        return False


def create_access_token(
    user_id: str,
    email: str,
    secret_key: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Creates a signed, short-lived JWT access token for API requests."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    secret_key: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Creates a longer-lived JWT refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str, secret_key: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token."""
    return jwt.decode(token, secret_key, algorithms=[JWT_ALGORITHM])

