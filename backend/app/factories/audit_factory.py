"""Factory for audit log entries."""

from typing import Any

from app.models.audit import AuditLog
from app.models.enums import AuditAction, AuditEntity
from app.models.user import User


def _stringify(value: Any) -> str | None:
    """Render an audited value as text, preserving ``None``."""
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


class AuditLogFactory:
    """Builds audit entries so every tool records changes identically."""

    @staticmethod
    def build(
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
        """Create an unpersisted audit entry."""
        return AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            field=field,
            previous_value=_stringify(previous_value),
            new_value=_stringify(new_value),
            reason=reason,
            actor_id=actor.id,
            actor_email=actor.email,
        )
