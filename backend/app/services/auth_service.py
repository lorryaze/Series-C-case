"""Authentication and user provisioning logic."""

from typing import Sequence

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.errors import AuthenticationError, ConflictError
from app.utils.security import create_access_token, hash_password, verify_password


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

    def issue_token(self, user: User) -> tuple[str, int]:
        """Return a signed access token and its lifetime in seconds."""
        settings = get_settings()
        token = create_access_token(user.email, role=user.role.value, user_id=user.id)
        return token, settings.access_token_expire_minutes * 60

    def create_user(
        self, *, email: str, full_name: str, password: str, role: Role
    ) -> User:
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
