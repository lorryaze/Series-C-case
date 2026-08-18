"""Cross-tool audit trail endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import AuditServiceDep
from app.middleware.auth import CurrentUser
from app.models.enums import AuditEntity
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "",
    response_model=list[AuditLogRead],
    summary="Read recent platform activity",
    description=(
        "Returns the most recent audit entries across every tool, optionally filtered by "
        "entity type. Any authenticated role may read the trail; nobody can modify it."
    ),
)
def list_recent_activity(
    current_user: CurrentUser,
    audit_service: AuditServiceDep,
    entity_type: AuditEntity | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[AuditLogRead]:
    """Return recent audit entries."""
    entries = audit_service.recent(entity_type=entity_type, limit=limit)
    return [AuditLogRead.model_validate(entry) for entry in entries]


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=list[AuditLogRead],
    summary="Read the trail for one entity",
    description="Returns every audited change for a single entity, newest first.",
)
def list_entity_trail(
    entity_type: AuditEntity,
    entity_id: int,
    current_user: CurrentUser,
    audit_service: AuditServiceDep,
) -> list[AuditLogRead]:
    """Return the trail for one entity."""
    entries = audit_service.trail_for(entity_type, entity_id)
    return [AuditLogRead.model_validate(entry) for entry in entries]
