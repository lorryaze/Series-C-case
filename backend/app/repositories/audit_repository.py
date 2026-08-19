"""Data access for the shared audit trail."""

from collections.abc import Sequence

from sqlalchemy import Select, select

from app.models.audit import AuditLog
from app.models.enums import AuditEntity
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    """Append-only queries over ``audit_logs``."""

    model = AuditLog

    def entity_query(self, entity_type: AuditEntity, entity_id: int) -> Select[tuple[AuditLog]]:
        """Return the newest-first query for one entity's trail."""
        return (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        )

    def recent_query(
        self, *, entity_type: AuditEntity | None = None
    ) -> Select[tuple[AuditLog]]:
        """Return the newest-first query across entities."""
        statement = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        if entity_type is not None:
            statement = statement.where(AuditLog.entity_type == entity_type)
        return statement

    def list_for_entity(
        self, entity_type: AuditEntity, entity_id: int, *, limit: int = 200
    ) -> Sequence[AuditLog]:
        """Return the trail for one entity, newest first."""
        statement = self.entity_query(entity_type, entity_id).limit(limit)
        return self.session.execute(statement).scalars().unique().all()
