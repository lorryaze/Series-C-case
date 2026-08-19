"""Cross-tool audit trail endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import AuditServiceDep
from app.middleware.auth import CurrentUser
from app.models.enums import AuditEntity
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page

router = APIRouter(prefix="/audit", tags=["audit"])

PageParam = Annotated[int, Query(ge=1)]
PageSizeParam = Annotated[int, Query(ge=1, le=200)]


@router.get(
    "",
    response_model=Page[AuditLogRead],
    summary="Read recent platform activity",
    description=(
        "Returns a page of audit entries across every tool, newest first, optionally "
        "filtered by entity type. Any authenticated role may read the trail; nobody can "
        "modify it."
    ),
)
def list_recent_activity(
    current_user: CurrentUser,
    audit_service: AuditServiceDep,
    entity_type: AuditEntity | None = None,
    page: PageParam = 1,
    page_size: PageSizeParam = 50,
) -> Page[AuditLogRead]:
    """Return one page of recent audit entries."""
    entries, total = audit_service.paginate_recent(
        entity_type=entity_type, page=page, page_size=page_size
    )
    return Page[AuditLogRead].build(
        [AuditLogRead.model_validate(entry) for entry in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=Page[AuditLogRead],
    summary="Read the trail for one entity",
    description="Returns a page of audited changes for a single entity, newest first.",
)
def list_entity_trail(
    entity_type: AuditEntity,
    entity_id: int,
    current_user: CurrentUser,
    audit_service: AuditServiceDep,
    page: PageParam = 1,
    page_size: PageSizeParam = 25,
) -> Page[AuditLogRead]:
    """Return one page of the trail for an entity."""
    entries, total = audit_service.paginate_trail_for(
        entity_type, entity_id, page=page, page_size=page_size
    )
    return Page[AuditLogRead].build(
        [AuditLogRead.model_validate(entry) for entry in entries],
        total=total,
        page=page,
        page_size=page_size,
    )
