"""Factories for KYC domain objects."""

from datetime import datetime
from secrets import token_hex

from app.models.base import utcnow
from app.models.enums import DocumentType, KycStatus, risk_level_for_score
from app.models.kyc_review import KycDocument, KycNote, KycReview
from app.schemas.kyc import KycReviewCreate


class KycReviewFactory:
    """Creates KYC aggregates with their derived fields already consistent."""

    @staticmethod
    def next_reference(now: datetime | None = None) -> str:
        """Generate a case reference such as ``KYC-2026-1f4c8a``."""
        now = now or utcnow()
        return f"KYC-{now.year}-{token_hex(3)}"

    @classmethod
    def build(cls, payload: KycReviewCreate) -> KycReview:
        """Create an unpersisted review from an API payload."""
        submitted_at = payload.submitted_at or utcnow()
        return KycReview(
            case_reference=cls.next_reference(submitted_at),
            customer_name=payload.customer_name,
            customer_email=str(payload.customer_email).lower(),
            customer_country=payload.customer_country.upper(),
            business_name=payload.business_name,
            submitted_at=submitted_at,
            status=KycStatus.PENDING,
            risk_score=payload.risk_score,
            risk_level=risk_level_for_score(payload.risk_score),
            risk_summary=payload.risk_summary,
            sanctions_hit=payload.sanctions_hit,
            pep_match=payload.pep_match,
            primary_document_type=payload.primary_document_type,
        )

    @staticmethod
    def build_document(
        *, document_type: DocumentType, file_name: str, verified: bool = False
    ) -> KycDocument:
        """Create an unpersisted document metadata row."""
        return KycDocument(document_type=document_type, file_name=file_name, verified=verified)

    @staticmethod
    def build_note(*, review_id: int, author_id: int, body: str) -> KycNote:
        """Create an unpersisted reviewer note."""
        return KycNote(review_id=review_id, author_id=author_id, body=body)
