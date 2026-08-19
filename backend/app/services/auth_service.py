"""Authentication and user provisioning logic."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair
from app.utils.errors import AuthenticationError, ConflictError
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


class AuthService:
    """Verifies credentials and issues access tokens."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def authenticate(self, email: str, password: str) -> User:
        """Return the user matching the credentials, or raise 401."""
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password")
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated")
        return user

    def issue_token(self, user: User) -> TokenPair:
        """Return a fresh access/refresh token pair for ``user``."""
        settings = get_settings()
        return TokenPair(
            access_token=create_access_token(user.email, role=user.role.value, user_id=user.id),
            refresh_token=create_refresh_token(
                user.email, role=user.role.value, user_id=user.id
            ),
            expires_in=settings.access_token_expire_minutes * 60,
        )

    def refresh(self, refresh_token: str) -> tuple[User, TokenPair]:
        """Exchange a valid refresh token for a new token pair.

        The user is re-read on every refresh so a deactivated account stops
        being able to mint access tokens.
        """
        payload = decode_refresh_token(refresh_token)
        user_id = payload.get("uid")
        if not isinstance(user_id, int):
            raise AuthenticationError("Refresh token is missing a user id")
        user = self.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User is no longer active")
        return user, self.issue_token(user)

    def create_user(self, *, email: str, full_name: str, password: str, role: Role) -> User:
        """Provision a new staff user."""
        if self.users.get_by_email(email) is not None:
            raise ConflictError(f"A user with email '{email}' already exists")
        user = self.users.add(
            User(
                email=email.lower(),
                full_name=full_name,
                hashed_password=hash_password(password),
                role=role,
            )
        )
        self.session.commit()
        return user

    def list_users(self) -> Sequence[User]:
        """Return active users, for reviewer pickers in the UI."""
        return self.users.list_active()
