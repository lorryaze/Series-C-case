"""KYC review schemas."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import DocumentType, KycStatus, RiskLevel
from app.schemas.audit import AuditLogRead
from app.schemas.common import ORMModel, Page, page_count
from app.schemas.user import UserSummary


class KycDocumentRead(ORMModel):
    """Metadata of a document attached to a case."""

    id: int
    document_type: DocumentType
    file_name: str
    verified: bool
    uploaded_at: datetime


class KycNoteRead(ORMModel):
    """A reviewer note on a case."""

    id: int
    body: str
    created_at: datetime
    author: UserSummary


class KycReviewListItem(ORMModel):
    """Row shown in the review queue table."""

    id: int
    case_reference: str
    customer_name: str
    submitted_at: datetime
    risk_score: int
    risk_level: RiskLevel
    primary_document_type: DocumentType
    status: KycStatus
    assigned_reviewer: UserSummary | None


class KycReviewDetail(KycReviewListItem):
    """Full case view, including risk detail, documents and notes."""

    customer_email: EmailStr
    customer_country: str
    business_name: str | None
    risk_summary: str
    sanctions_hit: bool
    pep_match: bool
    decision_reason: str | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    documents: list[KycDocumentRead]
    notes: list[KycNoteRead]


class KycQueueCounts(BaseModel):
    """Queue size per status, used by the dashboard cards."""

    pending: int = 0
    in_review: int = 0
    approved: int = 0
    rejected: int = 0
    escalated: int = 0
    total: int = 0


class KycReviewCreate(BaseModel):
    """Payload for opening a new KYC case."""

    customer_name: str = Field(min_length=2, max_length=255)
    customer_email: EmailStr
    customer_country: str = Field(min_length=2, max_length=2, examples=["US"])
    business_name: str | None = None
    risk_score: int = Field(ge=0, le=100)
    risk_summary: str = Field(min_length=3)
    primary_document_type: DocumentType
    sanctions_hit: bool = False
    pep_match: bool = False
    submitted_at: datetime | None = Field(
        default=None, description="Defaults to now when omitted"
    )


class DecisionRequest(BaseModel):
    """Reason attached to a review decision."""

    reason: str = Field(min_length=3, max_length=2000)


class AssignRequest(BaseModel):
    """Assign a single case to a reviewer."""

    reviewer_id: int


class BulkAssignRequest(BaseModel):
    """Assign several cases to one reviewer in a single action."""

    review_ids: list[int] = Field(min_length=1)
    reviewer_id: int


class BulkAssignResponse(BaseModel):
    """Outcome of a bulk assignment."""

    assigned: int
    review_ids: list[int]


class NoteCreate(BaseModel):
    """Payload for adding a reviewer note."""

    body: str = Field(min_length=1, max_length=2000)


class KycAuditTrail(Page[AuditLogRead]):
    """One page of audit entries for a case, newest first."""

    review_id: int

    @classmethod
    def for_case(
        cls,
        review_id: int,
        entries: Sequence[AuditLogRead],
        *,
        total: int,
        page: int,
        page_size: int,
    ) -> "KycAuditTrail":
        """Assemble a paginated trail response for one case."""
        return cls(
            review_id=review_id,
            items=list(entries),
            total=total,
            page=page,
            page_size=page_size,
            pages=page_count(total, page_size),
        )
