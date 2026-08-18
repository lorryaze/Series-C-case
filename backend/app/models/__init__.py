"""SQLAlchemy models.

Importing this package registers every model on the shared ``Base`` metadata,
which Alembic autogeneration and ``Base.metadata.create_all`` both rely on.
"""

from app.models.audit import AuditLog
from app.models.base import Base
from app.models.feature_flag import FeatureFlag, FeatureFlagState
from app.models.kyc_review import KycDocument, KycNote, KycReview
from app.models.refund import Refund
from app.models.user import User

__all__ = [
    "AuditLog",
    "Base",
    "FeatureFlag",
    "FeatureFlagState",
    "KycDocument",
    "KycNote",
    "KycReview",
    "Refund",
    "User",
]
