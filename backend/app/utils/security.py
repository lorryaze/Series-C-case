"""Password hashing and JWT access-token helpers."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config import get_settings
from app.utils.errors import AuthenticationError

_BCRYPT_ROUNDS = 12
_BCRYPT_MAX_BYTES = 72


def _encode(plain_password: str) -> bytes:
    """Encode a password, truncated to bcrypt's 72-byte input limit."""
    return plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for ``plain_password``."""
    return bcrypt.hashpw(_encode(plain_password), bcrypt.gensalt(_BCRYPT_ROUNDS)).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check ``plain_password`` against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(_encode(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    subject: str,
    *,
    role: str,
    user_id: int,
    expires_delta: timedelta | None = None,
) -> str:
    """Mint a signed access token for a user."""
    settings = get_settings()
    expires_delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "uid": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token, raising on any problem."""
    settings = get_settings()
    try:
        decoded: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Access token has expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Access token is invalid") from exc
    return decoded
