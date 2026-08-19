"""User schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Role
from app.schemas.common import ORMModel


class UserRead(ORMModel):
    """Public representation of a staff user."""

    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool


class UserSummary(ORMModel):
    """Compact user reference embedded in other resources."""

    id: int
    full_name: str
    email: EmailStr
    role: Role


class UserCreate(BaseModel):
    """Payload for provisioning a user (admin only)."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    role: Role
