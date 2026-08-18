"""KYC review queue endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import KycServiceDep
from app.middleware.auth import CurrentUser, require_reviewer
from app.models.enums import KycStatus, RiskLevel
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page
from app.schemas.kyc import (
    AssignRequest,
    BulkAssignRequest,
    BulkAssignResponse,
    DecisionRequest,
    KycAuditTrail,
    KycNoteRead,
    KycQueueCounts,
    KycReviewCreate,
    KycReviewDetail,
    KycReviewListItem,
    NoteCreate,
)

router = APIRouter(prefix="/kyc/reviews", tags=["kyc"])

ReviewerDep = Annotated[User, Depends(require_reviewer)]


@router.get(
    "",
    response_model=Page[KycReviewListItem],
    summary="List the KYC review queue",
    description=(
        "Returns a paginated, filterable queue. Filters combine with AND: status, "
        "risk level, assigned reviewer (or `unassigned=true`), submission date range "
        "and a free-text search over customer name, email and case reference."
    ),
)
def list_reviews(
    current_user: CurrentUser,
    kyc_service: KycServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
    status_filter: Annotated[KycStatus | None, Query(alias="status")] = None,
    risk_level: RiskLevel | None = None,
    reviewer_id: int | None = None,
    unassigned: bool = False,
    submitted_from: datetime | None = None,
    submitted_to: datetime | None = None,
    search: str | None = None,
) -> Page[KycReviewListItem]:
    """Return one page of the review queue."""
    reviews, total = kyc_service.list_reviews(
        page=page,
        page_size=page_size,
        status=status_filter,
        risk_level=risk_level,
        reviewer_id=reviewer_id,
        unassigned=unassigned,
        submitted_from=submitted_from,
        submitted_to=submitted_to,
        search=search,
    )
    return Page[KycReviewListItem].build(
        [KycReviewListItem.model_validate(review) for review in reviews],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/counts",
    response_model=KycQueueCounts,
    summary="Queue counts by status",
    description="Powers the dashboard cards: pending, in review, approved, rejected.",
)
def queue_counts(current_user: CurrentUser, kyc_service: KycServiceDep) -> KycQueueCounts:
    """Return the number of cases per status."""
    return kyc_service.queue_counts()


@router.post(
    "",
    response_model=KycReviewDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Open a new KYC case",
    description="Reviewer or admin only. The risk level is derived from the 0-100 risk score.",
)
def create_review(
    payload: KycReviewCreate, kyc_service: KycServiceDep, actor: ReviewerDep
) -> KycReviewDetail:
    """Create a KYC case."""
    review = kyc_service.create_review(payload, actor=actor)
    return KycReviewDetail.model_validate(review)


@router.get(
    "/{review_id}",
    response_model=KycReviewDetail,
    summary="Read one KYC case",
    description="Full case detail: customer, risk assessment, document metadata and notes.",
)
def read_review(
    review_id: int, current_user: CurrentUser, kyc_service: KycServiceDep
) -> KycReviewDetail:
    """Return one case."""
    return KycReviewDetail.model_validate(kyc_service.get_review(review_id))


@router.get(
    "/{review_id}/audit",
    response_model=KycAuditTrail,
    summary="Read a case's audit trail",
    description=(
        "Every status change, assignment and note on the case, newest first, with actor, "
        "timestamp and previous/new values. Readable by any authenticated role."
    ),
)
def read_audit_trail(
    review_id: int, current_user: CurrentUser, kyc_service: KycServiceDep
) -> KycAuditTrail:
    """Return the audit trail of a case."""
    entries = kyc_service.audit_trail(review_id)
    return KycAuditTrail(
        review_id=review_id,
        entries=[AuditLogRead.model_validate(entry) for entry in entries],
    )


@router.post(
    "/{review_id}/approve",
    response_model=KycReviewDetail,
    summary="Approve a case",
    description="Reviewer or admin only. Records the decision and reason in the audit trail.",
)
def approve_review(
    review_id: int,
    payload: DecisionRequest,
    kyc_service: KycServiceDep,
    actor: ReviewerDep,
) -> KycReviewDetail:
    """Approve a case."""
    review = kyc_service.approve(review_id, reason=payload.reason, actor=actor)
    return KycReviewDetail.model_validate(review)


@router.post(
    "/{review_id}/reject",
    response_model=KycReviewDetail,
    summary="Reject a case",
    description="Reviewer or admin only. A rejection reason is mandatory for compliance.",
)
def reject_review(
    review_id: int,
    payload: DecisionRequest,
    kyc_service: KycServiceDep,
    actor: ReviewerDep,
) -> KycReviewDetail:
    """Reject a case with a mandatory reason."""
    review = kyc_service.reject(review_id, reason=payload.reason, actor=actor)
    return KycReviewDetail.model_validate(review)


@router.post(
    "/{review_id}/escalate",
    response_model=KycReviewDetail,
    summary="Escalate a case",
    description="Reviewer or admin only. Moves the case to senior compliance for review.",
)
def escalate_review(
    review_id: int,
    payload: DecisionRequest,
    kyc_service: KycServiceDep,
    actor: ReviewerDep,
) -> KycReviewDetail:
    """Escalate a case."""
    review = kyc_service.escalate(review_id, reason=payload.reason, actor=actor)
    return KycReviewDetail.model_validate(review)


@router.post(
    "/{review_id}/assign",
    response_model=KycReviewDetail,
    summary="Assign a case to a reviewer",
    description="Reviewer or admin only. A pending case also moves to 'in review'.",
)
def assign_review(
    review_id: int,
    payload: AssignRequest,
    kyc_service: KycServiceDep,
    actor: ReviewerDep,
) -> KycReviewDetail:
    """Assign a case."""
    review = kyc_service.assign(review_id, reviewer_id=payload.reviewer_id, actor=actor)
    return KycReviewDetail.model_validate(review)


@router.post(
    "/bulk-assign",
    response_model=BulkAssignResponse,
    summary="Assign several cases at once",
    description="Reviewer or admin only. Each case is audited individually.",
)
def bulk_assign_reviews(
    payload: BulkAssignRequest, kyc_service: KycServiceDep, actor: ReviewerDep
) -> BulkAssignResponse:
    """Bulk-assign cases to one reviewer."""
    assigned_ids = kyc_service.bulk_assign(
        payload.review_ids, reviewer_id=payload.reviewer_id, actor=actor
    )
    return BulkAssignResponse(assigned=len(assigned_ids), review_ids=assigned_ids)


@router.post(
    "/{review_id}/notes",
    response_model=KycNoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a reviewer note",
    description="Reviewer or admin only. Notes are audited alongside status changes.",
)
def add_note(
    review_id: int,
    payload: NoteCreate,
    kyc_service: KycServiceDep,
    actor: ReviewerDep,
) -> KycNoteRead:
    """Attach a note to a case."""
    note = kyc_service.add_note(review_id, body=payload.body, actor=actor)
    return KycNoteRead.model_validate(note)
