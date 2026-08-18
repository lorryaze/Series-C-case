"""Data access for KYC reviews."""

from datetime import datetime
from typing import Sequence

from sqlalchemy import Select, func, select

from app.models.enums import KycStatus, RiskLevel
from app.models.kyc_review import KycNote, KycReview
from app.repositories.base import BaseRepository


class KycReviewRepository(BaseRepository[KycReview]):
    """Queries over ``kyc_reviews``."""

    model = KycReview

    def build_query(
        self,
        *,
        status: KycStatus | None = None,
        risk_level: RiskLevel | None = None,
        reviewer_id: int | None = None,
        unassigned: bool = False,
        submitted_from: datetime | None = None,
        submitted_to: datetime | None = None,
        search: str | None = None,
    ) -> Select[tuple[KycReview]]:
        """Compose the filtered queue query used by the table view."""
        statement = select(KycReview)
        if status is not None:
            statement = statement.where(KycReview.status == status)
        if risk_level is not None:
            statement = statement.where(KycReview.risk_level == risk_level)
        if unassigned:
            statement = statement.where(KycReview.assigned_reviewer_id.is_(None))
        elif reviewer_id is not None:
            statement = statement.where(KycReview.assigned_reviewer_id == reviewer_id)
        if submitted_from is not None:
            statement = statement.where(KycReview.submitted_at >= submitted_from)
        if submitted_to is not None:
            statement = statement.where(KycReview.submitted_at <= submitted_to)
        if search:
            pattern = f"%{search.lower()}%"
            statement = statement.where(
                func.lower(KycReview.customer_name).like(pattern)
                | func.lower(KycReview.case_reference).like(pattern)
                | func.lower(KycReview.customer_email).like(pattern)
            )
        return statement.order_by(KycReview.submitted_at.desc(), KycReview.id.desc())

    def counts_by_status(self) -> dict[KycStatus, int]:
        """Return the number of cases in each status."""
        statement = select(KycReview.status, func.count()).group_by(KycReview.status)
        rows = self.session.execute(statement).all()
        return {status: count for status, count in rows}

    def get_many(self, review_ids: Sequence[int]) -> Sequence[KycReview]:
        """Return the cases matching ``review_ids``."""
        if not review_ids:
            return []
        statement = select(KycReview).where(KycReview.id.in_(review_ids))
        return self.session.execute(statement).scalars().unique().all()

    def get_by_reference(self, case_reference: str) -> KycReview | None:
        """Return a case by its human-readable reference."""
        statement = select(KycReview).where(KycReview.case_reference == case_reference)
        return self.session.execute(statement).scalars().first()

    def add_note(self, note: KycNote) -> KycNote:
        """Persist a reviewer note."""
        self.session.add(note)
        self.session.flush()
        self.session.refresh(note)
        return note
