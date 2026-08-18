"""Audit trail schemas."""

from datetime import datetime

from app.models.enums import AuditAction, AuditEntity
from app.schemas.common import ORMModel


class AuditLogRead(ORMModel):
    """One entry of the shared audit trail."""

    id: int
    entity_type: AuditEntity
    entity_id: int
    action: AuditAction
    field: str | None
    previous_value: str | None
    new_value: str | None
    reason: str | None
    actor_id: int | None
    actor_email: str
    created_at: datetime
