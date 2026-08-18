"""Feature flag models: the flag plus its per-environment state."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import FlagEnvironment
from app.models.user import User


class FeatureFlag(Base, TimestampMixin):
    """A named toggle owned by engineering, rolled out per environment."""

    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    default_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    modified_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    modified_by: Mapped[User | None] = relationship(User, lazy="joined")
    environments: Mapped[list["FeatureFlagState"]] = relationship(
        back_populates="flag", cascade="all, delete-orphan", lazy="selectin"
    )

    def state_for(self, environment: FlagEnvironment) -> "FeatureFlagState | None":
        """Return the state row for ``environment`` if one exists."""
        return next((s for s in self.environments if s.environment == environment), None)

    def __repr__(self) -> str:
        return f"<FeatureFlag {self.key}>"


class FeatureFlagState(Base, TimestampMixin):
    """Enablement and rollout percentage of a flag in one environment."""

    __tablename__ = "feature_flag_states"
    __table_args__ = (
        UniqueConstraint("flag_id", "environment", name="uq_flag_environment"),
        CheckConstraint(
            "rollout_percentage >= 0 AND rollout_percentage <= 100",
            name="ck_rollout_percentage_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    flag_id: Mapped[int] = mapped_column(
        ForeignKey("feature_flags.id", ondelete="CASCADE"), index=True, nullable=False
    )
    environment: Mapped[FlagEnvironment] = mapped_column(
        SAEnum(FlagEnvironment, native_enum=False), index=True, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    flag: Mapped[FeatureFlag] = relationship(back_populates="environments")

    def __repr__(self) -> str:
        return (
            f"<FeatureFlagState flag={self.flag_id} env={self.environment.value} "
            f"enabled={self.enabled} rollout={self.rollout_percentage}>"
        )
