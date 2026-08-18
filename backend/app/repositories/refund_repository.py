"""Data access for refunds."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Sequence

from sqlalchemy import Select, cast, func, select
from sqlalchemy.types import String

from app.models.enums import RefundReason, RefundStatus
from app.models.refund import Refund
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class RefundStatusAggregate:
    """Per-status count and summed amount."""

    status: RefundStatus
    count: int
    amount: Decimal


class RefundRepository(BaseRepository[Refund]):
    """Queries over ``refunds``, including dashboard aggregates."""

    model = Refund

    def build_query(
        self,
        *,
        status: RefundStatus | None = None,
        reason: RefundReason | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        requested_from: datetime | None = None,
        requested_to: datetime | None = None,
        search: str | None = None,
    ) -> Select[tuple[Refund]]:
        """Compose the filtered refunds query used by the table view."""
        statement = select(Refund)
        if status is not None:
            statement = statement.where(Refund.status == status)
        if reason is not None:
            statement = statement.where(Refund.reason == reason)
        if min_amount is not None:
            statement = statement.where(Refund.amount >= min_amount)
        if max_amount is not None:
            statement = statement.where(Refund.amount <= max_amount)
        if requested_from is not None:
            statement = statement.where(Refund.requested_at >= requested_from)
        if requested_to is not None:
            statement = statement.where(Refund.requested_at <= requested_to)
        if search:
            pattern = f"%{search.lower()}%"
            statement = statement.where(
                func.lower(Refund.customer_name).like(pattern)
                | func.lower(Refund.refund_reference).like(pattern)
                | func.lower(Refund.transaction_reference).like(pattern)
            )
        return statement.order_by(Refund.requested_at.desc(), Refund.id.desc())

    def aggregates_by_status(self) -> list[RefundStatusAggregate]:
        """Return count and summed amount per status."""
        statement = select(
            Refund.status, func.count(), func.coalesce(func.sum(Refund.amount), 0)
        ).group_by(Refund.status)
        return [
            RefundStatusAggregate(status, int(count), Decimal(str(amount)))
            for status, count, amount in self.session.execute(statement).all()
        ]

    def average_processing_hours(self) -> float | None:
        """Mean hours between request and decision for processed refunds."""
        statement = select(Refund.requested_at, Refund.processed_at).where(
            Refund.processed_at.is_not(None)
        )
        rows = self.session.execute(statement).all()
        if not rows:
            return None
        durations = [
            (processed_at - requested_at).total_seconds() / 3600
            for requested_at, processed_at in rows
            if processed_at is not None
        ]
        if not durations:
            return None
        return round(sum(durations) / len(durations), 2)

    def daily_totals(self, *, since: datetime) -> list[tuple[date, int, Decimal]]:
        """Return per-day count and amount for refunds requested since ``since``."""
        day = func.date(cast(Refund.requested_at, String))
        statement = (
            select(day, func.count(), func.coalesce(func.sum(Refund.amount), 0))
            .where(Refund.requested_at >= since)
            .group_by(day)
            .order_by(day)
        )
        rows = self.session.execute(statement).all()
        return [
            (date.fromisoformat(str(day_value)), int(count), Decimal(str(amount)))
            for day_value, count, amount in rows
        ]

    def history_for_customer(
        self, customer_email: str, *, exclude_id: int, limit: int = 10
    ) -> Sequence[Refund]:
        """Return a customer's other refunds, newest first."""
        statement = (
            select(Refund)
            .where(Refund.customer_email == customer_email.lower(), Refund.id != exclude_id)
            .order_by(Refund.requested_at.desc())
            .limit(limit)
        )
        return self.session.execute(statement).scalars().unique().all()

    def get_by_reference(self, refund_reference: str) -> Refund | None:
        """Return a refund by its human-readable reference."""
        statement = select(Refund).where(Refund.refund_reference == refund_reference)
        return self.session.execute(statement).scalars().first()
