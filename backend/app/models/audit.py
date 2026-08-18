"""Shared audit trail model, written to by every tool."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AuditAction, AuditEntity
from app.models.user import User


class AuditLog(Base):
    """An immutable record of a single mutation performed by a user.

    Rows are append-only: services never update or delete audit entries, which is
    what makes the trail usable as compliance evidence.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[AuditEntity] = mapped_column(
        SAEnum(AuditEntity, native_enum=False), index=True, nullable=False
    )
    entity_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, native_enum=False), nullable=False
    )
    field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    actor: Mapped[User | None] = relationship(User, lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<AuditLog {self.entity_type.value}#{self.entity_id} "
            f"{self.action.value} field={self.field!r}>"
        )
