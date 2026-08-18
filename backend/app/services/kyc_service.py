"""Business logic for the KYC review queue."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session

from app.factories.kyc_factory import KycReviewFactory
from app.models.audit import AuditLog
from app.models.base import utcnow
from app.models.enums import (
    AuditAction,
    AuditEntity,
    KycStatus,
    RiskLevel,
    Role,
)
from app.models.kyc_review import KycNote, KycReview
from app.models.user import User
from app.repositories.kyc_repository import KycReviewRepository
from app.repositories.user_repository import UserRepository
from app.schemas.kyc import KycQueueCounts, KycReviewCreate
from app.services.audit_service import AuditService
from app.utils.errors import ConflictError, NotFoundError, ValidationError

TERMINAL_STATUSES: frozenset[KycStatus] = frozenset({KycStatus.APPROVED, KycStatus.REJECTED})


class KycService:
    """Orchestrates the compliance review workflow and its audit trail."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.reviews = KycReviewRepository(session)
        self.users = UserRepository(session)
        self.audit = AuditService(session)

    def list_reviews(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        status: KycStatus | None = None,
        risk_level: RiskLevel | None = None,
        reviewer_id: int | None = None,
        unassigned: bool = False,
        submitted_from: datetime | None = None,
        submitted_to: datetime | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[KycReview], int]:
        """Return a filtered page of the queue plus the total match count."""
        statement = self.reviews.build_query(
            status=status,
            risk_level=risk_level,
            reviewer_id=reviewer_id,
            unassigned=unassigned,
            submitted_from=submitted_from,
            submitted_to=submitted_to,
            search=search,
        )
        return self.reviews.paginate(statement, page=page, page_size=page_size)

    def queue_counts(self) -> KycQueueCounts:
        """Return dashboard counts per status."""
        counts = self.reviews.counts_by_status()
        return KycQueueCounts(
            pending=counts.get(KycStatus.PENDING, 0),
            in_review=counts.get(KycStatus.IN_REVIEW, 0),
            approved=counts.get(KycStatus.APPROVED, 0),
            rejected=counts.get(KycStatus.REJECTED, 0),
            escalated=counts.get(KycStatus.ESCALATED, 0),
            total=sum(counts.values()),
        )

    def get_review(self, review_id: int) -> KycReview:
        """Return one case or raise ``NotFoundError``."""
        review = self.reviews.get(review_id)
        if review is None:
            raise NotFoundError(f"KYC review {review_id} was not found")
        return review

    def create_review(self, payload: KycReviewCreate, *, actor: User) -> KycReview:
        """Open a new case and audit its creation."""
        review = self.reviews.add(KycReviewFactory.build(payload))
        self.audit.record(
            entity_type=AuditEntity.KYC_REVIEW,
            entity_id=review.id,
            action=AuditAction.CREATED,
            actor=actor,
            new_value=review.case_reference,
        )
        self.session.commit()
        return review

    def approve(self, review_id: int, *, reason: str, actor: User) -> KycReview:
        """Approve a case."""
        return self._decide(review_id, KycStatus.APPROVED, reason=reason, actor=actor)

    def reject(self, review_id: int, *, reason: str, actor: User) -> KycReview:
        """Reject a case; a reason is mandatory."""
        if not reason.strip():
            raise ValidationError("A rejection reason is required")
        return self._decide(review_id, KycStatus.REJECTED, reason=reason, actor=actor)

    def escalate(self, review_id: int, *, reason: str, actor: User) -> KycReview:
        """Escalate a case to senior compliance."""
        return self._decide(review_id, KycStatus.ESCALATED, reason=reason, actor=actor)

    def assign(self, review_id: int, *, reviewer_id: int, actor: User) -> KycReview:
        """Assign a case to a reviewer, moving a pending case into review."""
        review = self.get_review(review_id)
        reviewer = self._require_reviewer(reviewer_id)
        previous_reviewer = review.assigned_reviewer
        previous_status = review.status

        values: dict[str, object] = {"assigned_reviewer_id": reviewer.id}
        if review.status == KycStatus.PENDING:
            values["status"] = KycStatus.IN_REVIEW
        self.reviews.update(review, values)

        self.audit.record(
            entity_type=AuditEntity.KYC_REVIEW,
            entity_id=review.id,
            action=AuditAction.ASSIGNED,
            actor=actor,
            field="assigned_reviewer",
            previous_value=previous_reviewer.email if previous_reviewer else None,
            new_value=reviewer.email,
        )
        if review.status != previous_status:
            self.audit.record(
                entity_type=AuditEntity.KYC_REVIEW,
                entity_id=review.id,
                action=AuditAction.STATUS_CHANGED,
                actor=actor,
                field="status",
                previous_value=previous_status,
                new_value=review.status,
            )
        self.session.commit()
        return review

    def bulk_assign(
        self, review_ids: Sequence[int], *, reviewer_id: int, actor: User
    ) -> list[int]:
        """Assign several cases to one reviewer, auditing each case separately."""
        reviewer = self._require_reviewer(reviewer_id)
        reviews = self.reviews.get_many(review_ids)
        found_ids = {review.id for review in reviews}
        missing = sorted(set(review_ids) - found_ids)
        if missing:
            raise NotFoundError(
                "Some KYC reviews were not found", details={"missing_ids": missing}
            )

        for review in reviews:
            previous_reviewer = review.assigned_reviewer
            previous_status = review.status
            values: dict[str, object] = {"assigned_reviewer_id": reviewer.id}
            if review.status == KycStatus.PENDING:
                values["status"] = KycStatus.IN_REVIEW
            self.reviews.update(review, values)
            self.audit.record(
                entity_type=AuditEntity.KYC_REVIEW,
                entity_id=review.id,
                action=AuditAction.ASSIGNED,
                actor=actor,
                field="assigned_reviewer",
                previous_value=previous_reviewer.email if previous_reviewer else None,
                new_value=reviewer.email,
            )
            if review.status != previous_status:
                self.audit.record(
                    entity_type=AuditEntity.KYC_REVIEW,
                    entity_id=review.id,
                    action=AuditAction.STATUS_CHANGED,
                    actor=actor,
                    field="status",
                    previous_value=previous_status,
                    new_value=review.status,
                )
        self.session.commit()
        return sorted(found_ids)

    def add_note(self, review_id: int, *, body: str, actor: User) -> KycNote:
        """Attach a reviewer note to a case and audit it."""
        review = self.get_review(review_id)
        note = self.reviews.add_note(
            KycReviewFactory.build_note(review_id=review.id, author_id=actor.id, body=body)
        )
        self.audit.record(
            entity_type=AuditEntity.KYC_REVIEW,
            entity_id=review.id,
            action=AuditAction.NOTE_ADDED,
            actor=actor,
            field="notes",
            new_value=body,
        )
        self.session.commit()
        return note

    def audit_trail(self, review_id: int) -> Sequence[AuditLog]:
        """Return the audit entries for one case."""
        review = self.get_review(review_id)
        return self.audit.trail_for(AuditEntity.KYC_REVIEW, review.id)

    def _decide(
        self, review_id: int, new_status: KycStatus, *, reason: str, actor: User
    ) -> KycReview:
        review = self.get_review(review_id)
        if review.status in TERMINAL_STATUSES:
            raise ConflictError(
                f"Case {review.case_reference} is already {review.status.value}",
                details={"current_status": review.status.value},
            )
        previous_status = review.status
        values: dict[str, object] = {"status": new_status, "decision_reason": reason}
        if new_status in TERMINAL_STATUSES:
            values["decided_at"] = utcnow()
        self.reviews.update(review, values)
        self.audit.record(
            entity_type=AuditEntity.KYC_REVIEW,
            entity_id=review.id,
            action=AuditAction.STATUS_CHANGED,
            actor=actor,
            field="status",
            previous_value=previous_status,
            new_value=new_status,
            reason=reason,
        )
        self.session.commit()
        return review

    def _require_reviewer(self, reviewer_id: int) -> User:
        reviewer = self.users.get(reviewer_id)
        if reviewer is None or not reviewer.is_active:
            raise NotFoundError(f"User {reviewer_id} was not found")
        if reviewer.role not in (Role.ADMIN, Role.REVIEWER):
            raise ValidationError(
                "Cases can only be assigned to reviewers or admins",
                details={"role": reviewer.role.value},
            )
        return reviewer
