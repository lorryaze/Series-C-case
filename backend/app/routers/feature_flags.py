"""Feature flags admin endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import FeatureFlagServiceDep
from app.middleware.auth import CurrentUser, require_admin
from app.models.enums import FlagEnvironment
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page
from app.schemas.feature_flag import (
    FeatureFlagCreate,
    FeatureFlagHistory,
    FeatureFlagRead,
    FeatureFlagStateUpdate,
    FeatureFlagToggle,
    FeatureFlagUpdate,
)

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])

AdminDep = Annotated[User, Depends(require_admin)]


@router.get(
    "",
    response_model=Page[FeatureFlagRead],
    summary="List feature flags",
    description=(
        "Returns flags with their per-environment state. Supports free-text search over "
        "name, key and description, and filtering by environment and enabled state."
    ),
)
def list_flags(
    current_user: CurrentUser,
    flag_service: FeatureFlagServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    search: str | None = None,
    environment: FlagEnvironment | None = None,
    enabled: bool | None = None,
) -> Page[FeatureFlagRead]:
    """Return one page of feature flags."""
    flags, total = flag_service.list_flags(
        page=page,
        page_size=page_size,
        search=search,
        environment=environment,
        enabled=enabled,
    )
    return Page[FeatureFlagRead].build(
        [FeatureFlagRead.model_validate(flag) for flag in flags],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=FeatureFlagRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a feature flag",
    description=(
        "Admin only. The SDK key is slugified from the name when omitted, and a state row "
        "is initialised for every environment."
    ),
)
def create_flag(
    payload: FeatureFlagCreate, flag_service: FeatureFlagServiceDep, actor: AdminDep
) -> FeatureFlagRead:
    """Create a feature flag."""
    return FeatureFlagRead.model_validate(flag_service.create_flag(payload, actor=actor))


@router.get(
    "/{flag_id}",
    response_model=FeatureFlagRead,
    summary="Read one feature flag",
    description="Returns a single flag with its state in every environment.",
)
def read_flag(
    flag_id: int, current_user: CurrentUser, flag_service: FeatureFlagServiceDep
) -> FeatureFlagRead:
    """Return one flag."""
    return FeatureFlagRead.model_validate(flag_service.get_flag(flag_id))


@router.patch(
    "/{flag_id}",
    response_model=FeatureFlagRead,
    summary="Edit flag metadata",
    description="Admin only. Updates name, description or default state; each change is audited.",
)
def update_flag(
    flag_id: int,
    payload: FeatureFlagUpdate,
    flag_service: FeatureFlagServiceDep,
    actor: AdminDep,
) -> FeatureFlagRead:
    """Update flag metadata."""
    return FeatureFlagRead.model_validate(
        flag_service.update_flag(flag_id, payload, actor=actor)
    )


@router.post(
    "/{flag_id}/toggle",
    response_model=FeatureFlagRead,
    summary="Toggle a flag in one environment",
    description="Admin only. Flips the flag on or off for the given environment.",
)
def toggle_flag(
    flag_id: int,
    payload: FeatureFlagToggle,
    flag_service: FeatureFlagServiceDep,
    actor: AdminDep,
) -> FeatureFlagRead:
    """Toggle a flag."""
    flag = flag_service.toggle(
        flag_id, environment=payload.environment, enabled=payload.enabled, actor=actor
    )
    return FeatureFlagRead.model_validate(flag)


@router.patch(
    "/{flag_id}/environments/{environment}",
    response_model=FeatureFlagRead,
    summary="Set per-environment state and rollout",
    description=(
        "Admin only. Sets the enabled state and/or the rollout percentage (0-100) for one "
        "environment."
    ),
)
def update_flag_state(
    flag_id: int,
    environment: FlagEnvironment,
    payload: FeatureFlagStateUpdate,
    flag_service: FeatureFlagServiceDep,
    actor: AdminDep,
) -> FeatureFlagRead:
    """Update a flag's state in one environment."""
    flag = flag_service.update_state(
        flag_id, environment=environment, payload=payload, actor=actor
    )
    return FeatureFlagRead.model_validate(flag)


@router.get(
    "/{flag_id}/history",
    response_model=FeatureFlagHistory,
    summary="Read a flag's changelog",
    description="Who changed what and when, newest first, from the shared audit trail.",
)
def read_flag_history(
    flag_id: int, current_user: CurrentUser, flag_service: FeatureFlagServiceDep
) -> FeatureFlagHistory:
    """Return the changelog of one flag."""
    entries = flag_service.history(flag_id)
    return FeatureFlagHistory(
        flag_id=flag_id,
        entries=[AuditLogRead.model_validate(entry) for entry in entries],
    )
