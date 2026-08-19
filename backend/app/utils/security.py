"""Password hashing and JWT token helpers."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config import get_settings
from app.utils.errors import AuthenticationError

_BCRYPT_ROUNDS = 12
_BCRYPT_MAX_BYTES = 72

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


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


def _create_token(
    subject: str,
    *,
    role: str,
    user_id: int,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    """Mint a signed token carrying its own type claim."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "uid": user_id,
        "role": role,
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str,
    *,
    role: str,
    user_id: int,
    expires_delta: timedelta | None = None,
) -> str:
    """Mint a signed access token for a user."""
    settings = get_settings()
    return _create_token(
        subject,
        role=role,
        user_id=user_id,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=expires_delta or timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(
    subject: str,
    *,
    role: str,
    user_id: int,
    expires_delta: timedelta | None = None,
) -> str:
    """Mint a long-lived refresh token, only redeemable at the refresh endpoint."""
    settings = get_settings()
    return _create_token(
        subject,
        role=role,
        user_id=user_id,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=expires_delta or timedelta(minutes=settings.refresh_token_expire_minutes),
    )


def decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    """Decode a token and assert its type, raising on any problem.

    The ``typ`` claim keeps the two token families apart: a refresh token cannot
    be presented as a bearer credential, and an access token cannot be redeemed
    for a new one.
    """
    settings = get_settings()
    label = "Refresh token" if expected_type == REFRESH_TOKEN_TYPE else "Access token"
    try:
        decoded: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError(f"{label} has expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError(f"{label} is invalid") from exc
    if decoded.get("typ") != expected_type:
        raise AuthenticationError(f"{label} is invalid")
    return decoded


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token, raising on any problem."""
    return decode_token(token, expected_type=ACCESS_TOKEN_TYPE)


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a refresh token, raising on any problem."""
    return decode_token(token, expected_type=REFRESH_TOKEN_TYPE)
