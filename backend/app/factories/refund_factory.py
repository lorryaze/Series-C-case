"""Factory for refund domain objects."""

from datetime import datetime
from secrets import token_hex

from app.models.base import utcnow
from app.models.enums import RefundStatus
from app.models.refund import Refund
from app.schemas.refund import RefundCreate


class RefundFactory:
    """Creates refund aggregates with consistent references and defaults."""

    @staticmethod
    def next_reference(now: datetime | None = None) -> str:
        """Generate a refund reference such as ``RF-2026-9ab3c1``."""
        now = now or utcnow()
        return f"RF-{now.year}-{token_hex(3)}"

    @classmethod
    def build(cls, payload: RefundCreate) -> Refund:
        """Create an unpersisted refund from an API payload."""
        requested_at = payload.requested_at or utcnow()
        return Refund(
            refund_reference=cls.next_reference(requested_at),
            customer_name=payload.customer_name,
            customer_email=str(payload.customer_email).lower(),
            transaction_reference=payload.transaction_reference,
            amount=payload.amount,
            currency=payload.currency.upper(),
            reason=payload.reason,
            reason_detail=payload.reason_detail,
            status=RefundStatus.PENDING,
            requested_at=requested_at,
        )
