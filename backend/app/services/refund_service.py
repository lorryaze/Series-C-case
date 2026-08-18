"""Business logic for the refunds dashboard."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Sequence

from sqlalchemy.orm import Session

from app.factories.refund_factory import RefundFactory
from app.models.audit import AuditLog
from app.models.base import utcnow
from app.models.enums import AuditAction, AuditEntity, RefundReason, RefundStatus
from app.models.refund import Refund
from app.models.user import User
from app.repositories.refund_repository import RefundRepository
from app.schemas.refund import RefundCreate, RefundSummary, RefundTrendPoint
from app.services.audit_service import AuditService
from app.utils.errors import ConflictError, NotFoundError

TERMINAL_STATUSES: frozenset[RefundStatus] = frozenset(
    {RefundStatus.APPROVED, RefundStatus.REJECTED}
)


class RefundService:
    """Orchestrates refund decisions, dashboard metrics and the audit trail."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.refunds = RefundRepository(session)
        self.audit = AuditService(session)

    def list_refunds(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        status: RefundStatus | None = None,
        reason: RefundReason | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        requested_from: datetime | None = None,
        requested_to: datetime | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[Refund], int]:
        """Return a filtered page of refunds plus the total match count."""
        statement = self.refunds.build_query(
            status=status,
            reason=reason,
            min_amount=min_amount,
            max_amount=max_amount,
            requested_from=requested_from,
            requested_to=requested_to,
            search=search,
        )
        return self.refunds.paginate(statement, page=page, page_size=page_size)

    def summary(self) -> RefundSummary:
        """Return the summary-card metrics."""
        aggregates = {agg.status: agg for agg in self.refunds.aggregates_by_status()}

        def count_of(status: RefundStatus) -> int:
            aggregate = aggregates.get(status)
            return aggregate.count if aggregate else 0

        def amount_of(status: RefundStatus) -> Decimal:
            aggregate = aggregates.get(status)
            return aggregate.amount if aggregate else Decimal("0")

        return RefundSummary(
            total_count=sum(agg.count for agg in aggregates.values()),
            total_amount=sum(
                (agg.amount for agg in aggregates.values()), start=Decimal("0")
            ),
            pending_count=count_of(RefundStatus.PENDING),
            pending_amount=amount_of(RefundStatus.PENDING),
            approved_count=count_of(RefundStatus.APPROVED),
            approved_amount=amount_of(RefundStatus.APPROVED),
            rejected_count=count_of(RefundStatus.REJECTED),
            rejected_amount=amount_of(RefundStatus.REJECTED),
            info_requested_count=count_of(RefundStatus.INFO_REQUESTED),
            average_processing_hours=self.refunds.average_processing_hours(),
        )

    def trend(self, *, days: int = 30) -> list[RefundTrendPoint]:
        """Return a dense daily series of refund volume for the last ``days`` days."""
        since = utcnow() - timedelta(days=days - 1)
        totals = {day: (count, amount) for day, count, amount in self.refunds.daily_totals(since=since)}
        series: list[RefundTrendPoint] = []
        for offset in range(days):
            day = (since + timedelta(days=offset)).date()
            count, amount = totals.get(day, (0, Decimal("0")))
            series.append(RefundTrendPoint(day=day, count=count, amount=amount))
        return series

    def get_refund(self, refund_id: int) -> Refund:
        """Return one refund or raise ``NotFoundError``."""
        refund = self.refunds.get(refund_id)
        if refund is None:
            raise NotFoundError(f"Refund {refund_id} was not found")
        return refund

    def customer_history(self, refund: Refund) -> Sequence[Refund]:
        """Return the customer's other refunds."""
        return self.refunds.history_for_customer(refund.customer_email, exclude_id=refund.id)

    def approval_chain(self, refund: Refund) -> Sequence[AuditLog]:
        """Return the audited decision chain for a refund."""
        return self.audit.trail_for(AuditEntity.REFUND, refund.id)

    def create_refund(self, payload: RefundCreate, *, actor: User) -> Refund:
        """File a new refund request."""
        refund = self.refunds.add(RefundFactory.build(payload))
        self.audit.record(
            entity_type=AuditEntity.REFUND,
            entity_id=refund.id,
            action=AuditAction.CREATED,
            actor=actor,
            new_value=refund.refund_reference,
        )
        self.session.commit()
        return refund

    def approve(self, refund_id: int, *, reason: str, actor: User) -> Refund:
        """Approve a refund."""
        return self._decide(refund_id, RefundStatus.APPROVED, reason=reason, actor=actor)

    def reject(self, refund_id: int, *, reason: str, actor: User) -> Refund:
        """Reject a refund; a reason is mandatory."""
        return self._decide(refund_id, RefundStatus.REJECTED, reason=reason, actor=actor)

    def request_more_info(self, refund_id: int, *, reason: str, actor: User) -> Refund:
        """Ask the requester for more information, keeping the case open."""
        return self._decide(
            refund_id, RefundStatus.INFO_REQUESTED, reason=reason, actor=actor
        )

    def _decide(
        self, refund_id: int, new_status: RefundStatus, *, reason: str, actor: User
    ) -> Refund:
        refund = self.get_refund(refund_id)
        if refund.status in TERMINAL_STATUSES:
            raise ConflictError(
                f"Refund {refund.refund_reference} is already {refund.status.value}",
                details={"current_status": refund.status.value},
            )
        previous_status = refund.status
        values: dict[str, object] = {"status": new_status, "decision_reason": reason}
        if new_status in TERMINAL_STATUSES:
            values["processed_at"] = utcnow()
            values["processed_by_id"] = actor.id
        self.refunds.update(refund, values)
        self.audit.record(
            entity_type=AuditEntity.REFUND,
            entity_id=refund.id,
            action=AuditAction.STATUS_CHANGED,
            actor=actor,
            field="status",
            previous_value=previous_status,
            new_value=new_status,
            reason=reason,
        )
        self.session.commit()
        return refund
