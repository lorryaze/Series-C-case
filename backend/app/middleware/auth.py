"""Authentication and role-based access control dependencies."""

from typing import Annotated, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.errors import AuthenticationError, PermissionDeniedError
from app.utils.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the caller from the bearer token, or fail with 401."""
    if credentials is None:
        raise AuthenticationError("Authorization header is missing")
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("uid")
    if not isinstance(user_id, int):
        raise AuthenticationError("Access token is missing a user id")
    user = UserRepository(session).get(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User is no longer active")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: Role) -> Callable[[User], User]:
    """Build a dependency that only admits callers holding one of ``allowed_roles``.

    Every mutating endpoint declares its permission with this guard, so RBAC is
    enforced server-side regardless of what the UI shows.
    """

    def dependency(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise PermissionDeniedError(
                "Your role does not permit this action",
                details={
                    "required_roles": [role.value for role in allowed_roles],
                    "your_role": current_user.role.value,
                },
            )
        return current_user

    return dependency


require_admin = require_roles(Role.ADMIN)
require_reviewer = require_roles(Role.ADMIN, Role.REVIEWER)

AdminUser = Annotated[User, Depends(require_admin)]
ReviewerUser = Annotated[User, Depends(require_reviewer)]
