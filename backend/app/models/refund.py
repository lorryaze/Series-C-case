"""Refund request model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import RefundReason, RefundStatus
from app.models.user import User


class Refund(Base, TimestampMixin):
    """A customer refund request moving through the approval workflow."""

    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(primary_key=True)
    refund_reference: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    customer_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    transaction_reference: Mapped[str] = mapped_column(String(64), nullable=False)

    amount: Mapped[float] = mapped_column(Numeric(12, 2), index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    reason: Mapped[RefundReason] = mapped_column(
        SAEnum(RefundReason, native_enum=False), index=True, nullable=False
    )
    reason_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RefundStatus] = mapped_column(
        SAEnum(RefundStatus, native_enum=False),
        default=RefundStatus.PENDING,
        index=True,
        nullable=False,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    processed_by: Mapped[User | None] = relationship(User, lazy="joined")

    @property
    def processing_hours(self) -> float | None:
        """Hours between request and decision, or ``None`` while still open."""
        if self.processed_at is None:
            return None
        return (self.processed_at - self.requested_at).total_seconds() / 3600

    def __repr__(self) -> str:
        return f"<Refund {self.refund_reference} {self.amount} {self.status.value}>"
