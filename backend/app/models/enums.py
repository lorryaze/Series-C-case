"""Domain enumerations shared by models, schemas and services."""

from enum import Enum


class Role(str, Enum):
    """Platform roles, ordered from most to least privileged."""

    ADMIN = "admin"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class KycStatus(str, Enum):
    """Lifecycle states of a KYC review."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class RiskLevel(str, Enum):
    """Risk banding derived from the numeric risk score."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DocumentType(str, Enum):
    """Identity document types accepted during onboarding."""

    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"
    PROOF_OF_ADDRESS = "proof_of_address"
    BUSINESS_REGISTRATION = "business_registration"


class RefundStatus(str, Enum):
    """Lifecycle states of a refund request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INFO_REQUESTED = "info_requested"


class RefundReason(str, Enum):
    """Reason categories captured when a refund is requested."""

    DUPLICATE_CHARGE = "duplicate_charge"
    SERVICE_NOT_RENDERED = "service_not_rendered"
    FRAUD = "fraud"
    CUSTOMER_REQUEST = "customer_request"
    PROCESSING_ERROR = "processing_error"


class FlagEnvironment(str, Enum):
    """Deployment environments a feature flag can target."""

    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"


class AuditAction(str, Enum):
    """Coarse classification of an audited mutation."""

    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    NOTE_ADDED = "note_added"
    TOGGLED = "toggled"
    DELETED = "deleted"


class AuditEntity(str, Enum):
    """Entity types that participate in the shared audit trail."""

    KYC_REVIEW = "kyc_review"
    REFUND = "refund"
    FEATURE_FLAG = "feature_flag"
    USER = "user"


RISK_LEVEL_THRESHOLDS: tuple[tuple[int, RiskLevel], ...] = (
    (25, RiskLevel.LOW),
    (50, RiskLevel.MEDIUM),
    (75, RiskLevel.HIGH),
    (100, RiskLevel.CRITICAL),
)


def risk_level_for_score(score: int) -> RiskLevel:
    """Map a 0-100 risk score onto its risk band."""
    for upper_bound, level in RISK_LEVEL_THRESHOLDS:
        if score <= upper_bound:
            return level
    return RiskLevel.CRITICAL
