"""Data access for users."""

from typing import Sequence

from sqlalchemy import select

from app.models.enums import Role
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Queries over the ``users`` table."""

    model = User

    def get_by_email(self, email: str) -> User | None:
        """Return the user with ``email`` (case-insensitive), or ``None``."""
        statement = select(User).where(User.email == email.lower())
        return self.session.execute(statement).scalars().first()

    def list_by_role(self, role: Role) -> Sequence[User]:
        """Return active users holding ``role``, ordered by name."""
        statement = (
            select(User)
            .where(User.role == role, User.is_active.is_(True))
            .order_by(User.full_name)
        )
        return self.session.execute(statement).scalars().all()

    def list_active(self) -> Sequence[User]:
        """Return all active users, ordered by name."""
        statement = select(User).where(User.is_active.is_(True)).order_by(User.full_name)
        return self.session.execute(statement).scalars().all()
