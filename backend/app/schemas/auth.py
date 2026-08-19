"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    """Credentials submitted by the login form."""

    email: EmailStr = Field(examples=["admin@fintech.com"])
    password: str = Field(min_length=1, examples=["demo123"])


class RefreshRequest(BaseModel):
    """A refresh token being exchanged for a new access token."""

    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    """A freshly minted access token with its refresh companion."""

    access_token: str
    refresh_token: str
    expires_in: int = Field(description="Access token lifetime in seconds")


class TokenResponse(TokenPair):
    """Token pair plus the authenticated user's profile."""

    token_type: str = "bearer"
    user: UserRead
