"""Refund schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import RefundReason, RefundStatus
from app.schemas.audit import AuditLogRead
from app.schemas.common import ORMModel
from app.schemas.user import UserSummary


class RefundListItem(ORMModel):
    """Row shown in the refunds table."""

    id: int
    refund_reference: str
    customer_name: str
    amount: Decimal
    currency: str
    reason: RefundReason
    status: RefundStatus
    requested_at: datetime
    processed_at: datetime | None


class CustomerRefundHistoryItem(ORMModel):
    """A prior refund for the same customer."""

    id: int
    refund_reference: str
    amount: Decimal
    status: RefundStatus
    requested_at: datetime


class RefundDetail(RefundListItem):
    """Full refund view including approval chain and customer history."""

    customer_email: EmailStr
    transaction_reference: str
    reason_detail: str | None
    decision_reason: str | None
    processed_by: UserSummary | None
    processing_hours: float | None
    created_at: datetime
    updated_at: datetime
    customer_history: list[CustomerRefundHistoryItem] = []
    approval_chain: list[AuditLogRead] = []


class RefundSummary(BaseModel):
    """Summary cards on top of the refunds dashboard."""

    total_count: int
    total_amount: Decimal
    pending_count: int
    pending_amount: Decimal
    approved_count: int
    approved_amount: Decimal
    rejected_count: int
    rejected_amount: Decimal
    info_requested_count: int
    average_processing_hours: float | None


class RefundTrendPoint(BaseModel):
    """One day of the refunds-over-time chart."""

    day: date
    count: int
    amount: Decimal


class RefundCreate(BaseModel):
    """Payload for filing a refund request."""

    customer_name: str = Field(min_length=2, max_length=255)
    customer_email: EmailStr
    transaction_reference: str = Field(min_length=3, max_length=64)
    amount: Decimal = Field(gt=0, le=Decimal("1000000"))
    currency: str = Field(default="USD", min_length=3, max_length=3)
    reason: RefundReason
    reason_detail: str | None = None
    requested_at: datetime | None = None


class RefundDecisionRequest(BaseModel):
    """Reason attached to a refund decision or information request."""

    reason: str = Field(min_length=3, max_length=2000)
