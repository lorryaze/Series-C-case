"""Data access for the shared audit trail."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.enums import AuditEntity
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    """Append-only queries over ``audit_logs``."""

    model = AuditLog

    def list_for_entity(
        self, entity_type: AuditEntity, entity_id: int, *, limit: int = 200
    ) -> Sequence[AuditLog]:
        """Return the trail for one entity, newest first."""
        statement = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
        return self.session.execute(statement).scalars().unique().all()

    def list_recent(
        self, *, entity_type: AuditEntity | None = None, limit: int = 100
    ) -> Sequence[AuditLog]:
        """Return the most recent entries, optionally filtered by entity type."""
        statement = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        if entity_type is not None:
            statement = statement.where(AuditLog.entity_type == entity_type)
        return self.session.execute(statement.limit(limit)).scalars().unique().all()
