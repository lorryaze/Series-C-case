"""Authentication and user endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.config import get_settings
from app.dependencies import AuthServiceDep
from app.middleware.auth import CurrentUser, require_admin
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead, UserSummary
from app.utils.errors import AuthenticationError, RateLimitedError
from app.utils.rate_limit import RateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()
login_rate_limiter = RateLimiter(
    max_events=_settings.login_rate_limit_attempts,
    window_seconds=_settings.login_rate_limit_window_seconds,
)


def _rate_limit_key(request: Request, email: str) -> str:
    """Bucket login attempts per client address and account."""
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}|{email.lower()}"


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for an access token",
    description=(
        "Authenticates a staff user and returns a JWT access token, a refresh token "
        "and the user profile. Failed attempts are rate limited per client address "
        "and account (HTTP 429). Demo credentials: admin@fintech.com / "
        "reviewer@fintech.com / viewer@fintech.com with password `demo123`."
    ),
)
def login(
    payload: LoginRequest, request: Request, auth_service: AuthServiceDep
) -> TokenResponse:
    """Authenticate a user and mint a token pair."""
    key = _rate_limit_key(request, str(payload.email))
    retry_after = login_rate_limiter.retry_after(key)
    if retry_after is not None:
        raise RateLimitedError(
            "Too many failed login attempts. Try again later.",
            details={"retry_after_seconds": retry_after},
        )
    try:
        user = auth_service.authenticate(str(payload.email), payload.password)
    except AuthenticationError:
        login_rate_limiter.record(key)
        raise
    login_rate_limiter.reset(key)
    tokens = auth_service.issue_token(user)
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserRead.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new access token",
    description=(
        "Redeems a refresh token issued by `/auth/login` for a new token pair. "
        "Access tokens are rejected here, and deactivated accounts cannot refresh."
    ),
)
def refresh(payload: RefreshRequest, auth_service: AuthServiceDep) -> TokenResponse:
    """Rotate a refresh token into a new token pair."""
    user, tokens = auth_service.refresh(payload.refresh_token)
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
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
