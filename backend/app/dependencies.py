"""Service providers wired into routers through FastAPI's ``Depends()``."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.feature_flag_service import FeatureFlagService
from app.services.kyc_service import KycService
from app.services.refund_service import RefundService

DbSession = Annotated[Session, Depends(get_db)]


def get_auth_service(session: DbSession) -> AuthService:
    """Provide the authentication service."""
    return AuthService(session)


def get_kyc_service(session: DbSession) -> KycService:
    """Provide the KYC review service."""
    return KycService(session)


def get_refund_service(session: DbSession) -> RefundService:
    """Provide the refunds service."""
    return RefundService(session)


def get_feature_flag_service(session: DbSession) -> FeatureFlagService:
    """Provide the feature flag service."""
    return FeatureFlagService(session)


def get_audit_service(session: DbSession) -> AuditService:
    """Provide the shared audit service."""
    return AuditService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
KycServiceDep = Annotated[KycService, Depends(get_kyc_service)]
RefundServiceDep = Annotated[RefundService, Depends(get_refund_service)]
FeatureFlagServiceDep = Annotated[FeatureFlagService, Depends(get_feature_flag_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
