"""Feature flag schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import FlagEnvironment
from app.schemas.audit import AuditLogRead
from app.schemas.common import ORMModel
from app.schemas.user import UserSummary


class FeatureFlagStateRead(ORMModel):
    """Enablement of a flag within one environment."""

    environment: FlagEnvironment
    enabled: bool
    rollout_percentage: int


class FeatureFlagRead(ORMModel):
    """A flag with its per-environment states."""

    id: int
    key: str
    name: str
    description: str
    default_enabled: bool
    environments: list[FeatureFlagStateRead]
    modified_by: UserSummary | None
    created_at: datetime
    updated_at: datetime


class FeatureFlagCreate(BaseModel):
    """Payload for creating a flag; the key is derived from the name when omitted."""

    name: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=3, max_length=1000)
    key: str | None = Field(
        default=None,
        description="Slug used by SDKs; auto-generated from the name when omitted",
    )
    default_enabled: bool = False


class FeatureFlagUpdate(BaseModel):
    """Editable flag metadata."""

    name: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, min_length=3, max_length=1000)
    default_enabled: bool | None = None


class FeatureFlagStateUpdate(BaseModel):
    """Per-environment enablement and rollout change."""

    enabled: bool | None = None
    rollout_percentage: int | None = Field(default=None, ge=0, le=100)


class FeatureFlagToggle(BaseModel):
    """Flip a flag on or off in one environment."""

    environment: FlagEnvironment
    enabled: bool


class FeatureFlagHistory(BaseModel):
    """Changelog for one flag, newest first."""

    flag_id: int
    entries: list[AuditLogRead]
