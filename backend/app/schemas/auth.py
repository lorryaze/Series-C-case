"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    """Credentials submitted by the login form."""

    email: EmailStr = Field(examples=["admin@fintech.com"])
    password: str = Field(min_length=1, examples=["demo123"])


class TokenResponse(BaseModel):
    """Access token plus the authenticated user's profile."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")
    user: UserRead
