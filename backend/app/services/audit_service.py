"""Shared audit trail service used by all tools."""

from typing import Any, Sequence

from sqlalchemy.orm import Session

from app.factories.audit_factory import AuditLogFactory
from app.models.audit import AuditLog
from app.models.enums import AuditAction, AuditEntity
from app.models.user import User
from app.repositories.audit_repository import AuditRepository


class AuditService:
    """Records and reads the compliance trail.

    Tool services depend on this rather than writing ``AuditLog`` rows directly,
    so a new tool inherits a complete audit trail for free.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AuditRepository(session)

    def record(
        self,
        *,
        entity_type: AuditEntity,
        entity_id: int,
        action: AuditAction,
        actor: User,
        field: str | None = None,
        previous_value: Any = None,
        new_value: Any = None,
        reason: str | None = None,
    ) -> AuditLog:
        """Append a single entry to the trail."""
        entry = AuditLogFactory.build(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            field=field,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason,
        )
        return self.repository.add(entry)

    def record_field_changes(
        self,
        *,
        entity_type: AuditEntity,
        entity_id: int,
        actor: User,
        changes: dict[str, tuple[Any, Any]],
        action: AuditAction = AuditAction.UPDATED,
        reason: str | None = None,
    ) -> list[AuditLog]:
        """Append one entry per changed field, skipping no-op changes."""
        entries: list[AuditLog] = []
        for field, (previous_value, new_value) in changes.items():
            if previous_value == new_value:
                continue
            entries.append(
                self.record(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    action=action,
                    actor=actor,
                    field=field,
                    previous_value=previous_value,
                    new_value=new_value,
                    reason=reason,
                )
            )
        return entries

    def trail_for(
        self, entity_type: AuditEntity, entity_id: int, *, limit: int = 200
    ) -> Sequence[AuditLog]:
        """Return the trail for one entity, newest first."""
        return self.repository.list_for_entity(entity_type, entity_id, limit=limit)

    def recent(
        self, *, entity_type: AuditEntity | None = None, limit: int = 100
    ) -> Sequence[AuditLog]:
        """Return the most recent entries across the platform."""
        return self.repository.list_recent(entity_type=entity_type, limit=limit)
