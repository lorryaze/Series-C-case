"""KYC review models: the case, its documents and reviewer notes."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import DocumentType, KycStatus, RiskLevel
from app.models.user import User


class KycReview(Base, TimestampMixin):
    """A customer onboarding case awaiting compliance review."""

    __tablename__ = "kyc_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_reference: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    customer_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_country: Mapped[str] = mapped_column(String(2), nullable=False)
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    status: Mapped[KycStatus] = mapped_column(
        SAEnum(KycStatus, native_enum=False),
        default=KycStatus.PENDING,
        index=True,
        nullable=False,
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, native_enum=False), index=True, nullable=False
    )
    risk_summary: Mapped[str] = mapped_column(Text, nullable=False)
    sanctions_hit: Mapped[bool] = mapped_column(default=False, nullable=False)
    pep_match: Mapped[bool] = mapped_column(default=False, nullable=False)

    primary_document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, native_enum=False), nullable=False
    )
    assigned_reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_reviewer: Mapped[User | None] = relationship(User, lazy="joined")
    documents: Mapped[list["KycDocument"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", lazy="selectin"
    )
    notes: Mapped[list["KycNote"]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="KycNote.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<KycReview {self.case_reference} status={self.status.value}>"


class KycDocument(Base):
    """Metadata for a document submitted with a KYC case.

    Only metadata is stored; binary storage is intentionally out of scope for the
    prototype and would plug in behind this model.
    """

    __tablename__ = "kyc_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("kyc_reviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, native_enum=False), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    review: Mapped[KycReview] = relationship(back_populates="documents")


class KycNote(Base):
    """A free-text note left on a case by a reviewer."""

    __tablename__ = "kyc_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("kyc_reviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    review: Mapped[KycReview] = relationship(back_populates="notes")
    author: Mapped[User] = relationship(User, lazy="joined")
