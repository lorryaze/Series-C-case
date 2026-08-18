"""Refunds dashboard endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import RefundServiceDep
from app.middleware.auth import CurrentUser, require_reviewer
from app.models.enums import RefundReason, RefundStatus
from app.models.refund import Refund
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page
from app.schemas.refund import (
    CustomerRefundHistoryItem,
    RefundCreate,
    RefundDecisionRequest,
    RefundDetail,
    RefundListItem,
    RefundSummary,
    RefundTrendPoint,
)
from app.services.refund_service import RefundService

router = APIRouter(prefix="/refunds", tags=["refunds"])

ReviewerDep = Annotated[User, Depends(require_reviewer)]


@router.get(
    "",
    response_model=Page[RefundListItem],
    summary="List refund requests",
    description=(
        "Returns a paginated, filterable list. Filters: status, reason category, "
        "amount range, requested-date range and free-text search over customer name, "
        "refund reference and transaction reference."
    ),
)
def list_refunds(
    current_user: CurrentUser,
    refund_service: RefundServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
    status_filter: Annotated[RefundStatus | None, Query(alias="status")] = None,
    reason: RefundReason | None = None,
    min_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    max_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    requested_from: datetime | None = None,
    requested_to: datetime | None = None,
    search: str | None = None,
) -> Page[RefundListItem]:
    """Return one page of refunds."""
    refunds, total = refund_service.list_refunds(
        page=page,
        page_size=page_size,
        status=status_filter,
        reason=reason,
        min_amount=min_amount,
        max_amount=max_amount,
        requested_from=requested_from,
        requested_to=requested_to,
        search=search,
    )
    return Page[RefundListItem].build(
        [RefundListItem.model_validate(refund) for refund in refunds],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/summary",
    response_model=RefundSummary,
    summary="Dashboard summary metrics",
    description=(
        "Counts and summed amounts per status plus the average processing time in hours, "
        "used by the summary cards."
    ),
)
def read_summary(current_user: CurrentUser, refund_service: RefundServiceDep) -> RefundSummary:
    """Return refund summary metrics."""
    return refund_service.summary()


@router.get(
    "/trend",
    response_model=list[RefundTrendPoint],
    summary="Refund volume over time",
    description="Dense daily series (zero-filled) of refund count and amount for the chart.",
)
def read_trend(
    current_user: CurrentUser,
    refund_service: RefundServiceDep,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[RefundTrendPoint]:
    """Return the daily refund trend."""
    return refund_service.trend(days=days)


@router.post(
    "",
    response_model=RefundDetail,
    status_code=status.HTTP_201_CREATED,
    summary="File a refund request",
    description="Reviewer or admin only. New requests start in the pending state.",
)
def create_refund(
    payload: RefundCreate, refund_service: RefundServiceDep, actor: ReviewerDep
) -> RefundDetail:
    """Create a refund request."""
    refund = refund_service.create_refund(payload, actor=actor)
    return _to_detail(refund_service, refund)


@router.get(
    "/{refund_id}",
    response_model=RefundDetail,
    summary="Read one refund",
    description=(
        "Full refund detail including the transaction reference, the customer's other "
        "refunds and the audited approval chain."
    ),
)
def read_refund(
    refund_id: int, current_user: CurrentUser, refund_service: RefundServiceDep
) -> RefundDetail:
    """Return one refund."""
    return _to_detail(refund_service, refund_service.get_refund(refund_id))


@router.post(
    "/{refund_id}/approve",
    response_model=RefundDetail,
    summary="Approve a refund",
    description="Reviewer or admin only. Stamps the processor and processing time.",
)
def approve_refund(
    refund_id: int,
    payload: RefundDecisionRequest,
    refund_service: RefundServiceDep,
    actor: ReviewerDep,
) -> RefundDetail:
    """Approve a refund."""
    refund = refund_service.approve(refund_id, reason=payload.reason, actor=actor)
    return _to_detail(refund_service, refund)


@router.post(
    "/{refund_id}/reject",
    response_model=RefundDetail,
    summary="Reject a refund",
    description="Reviewer or admin only. A rejection reason is mandatory.",
)
def reject_refund(
    refund_id: int,
    payload: RefundDecisionRequest,
    refund_service: RefundServiceDep,
    actor: ReviewerDep,
) -> RefundDetail:
    """Reject a refund."""
    refund = refund_service.reject(refund_id, reason=payload.reason, actor=actor)
    return _to_detail(refund_service, refund)


@router.post(
    "/{refund_id}/request-info",
    response_model=RefundDetail,
    summary="Request more information",
    description="Reviewer or admin only. Keeps the refund open and records what is needed.",
)
def request_more_info(
    refund_id: int,
    payload: RefundDecisionRequest,
    refund_service: RefundServiceDep,
    actor: ReviewerDep,
) -> RefundDetail:
    """Ask the requester for more information."""
    refund = refund_service.request_more_info(refund_id, reason=payload.reason, actor=actor)
    return _to_detail(refund_service, refund)


def _to_detail(refund_service: RefundService, refund: Refund) -> RefundDetail:
    """Assemble the detail response, including history and approval chain."""
    detail = RefundDetail.model_validate(refund)
    detail.customer_history = [
        CustomerRefundHistoryItem.model_validate(item)
        for item in refund_service.customer_history(refund)
    ]
    detail.approval_chain = [
        AuditLogRead.model_validate(entry) for entry in refund_service.approval_chain(refund)
    ]
    return detail
