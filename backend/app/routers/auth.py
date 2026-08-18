"""Authentication and user endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import AuthServiceDep
from app.middleware.auth import CurrentUser, require_admin
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead, UserSummary

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for an access token",
    description=(
        "Authenticates a staff user and returns a JWT access token plus the user "
        "profile. Demo credentials: admin@fintech.com / reviewer@fintech.com / "
        "viewer@fintech.com with password `demo123`."
    ),
)
def login(payload: LoginRequest, auth_service: AuthServiceDep) -> TokenResponse:
    """Authenticate a user and mint an access token."""
    user = auth_service.authenticate(str(payload.email), payload.password)
    token, expires_in = auth_service.issue_token(user)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the authenticated user",
    description="Resolves the bearer token to the current user, including their role.",
)
def read_current_user(current_user: CurrentUser) -> UserRead:
    """Return the caller's own profile."""
    return UserRead.model_validate(current_user)


@router.get(
    "/users",
    response_model=list[UserSummary],
    summary="List active users",
    description="Used to populate reviewer pickers. Any authenticated role may read this.",
)
def list_users(current_user: CurrentUser, auth_service: AuthServiceDep) -> list[UserSummary]:
    """Return all active users."""
    return [UserSummary.model_validate(user) for user in auth_service.list_users()]


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a staff user",
    description="Admin only. Creates a user with the given role and a bcrypt-hashed password.",
)
def create_user(
    payload: UserCreate,
    auth_service: AuthServiceDep,
    _: Annotated[User, Depends(require_admin)],
) -> UserRead:
    """Create a new staff user."""
    user = auth_service.create_user(
        email=str(payload.email),
        full_name=payload.full_name,
        password=payload.password,
        role=payload.role,
    )
    return UserRead.model_validate(user)
