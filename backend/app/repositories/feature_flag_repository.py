"""Data access for feature flags."""

from sqlalchemy import Select, func, select

from app.models.enums import FlagEnvironment
from app.models.feature_flag import FeatureFlag, FeatureFlagState
from app.repositories.base import BaseRepository


class FeatureFlagRepository(BaseRepository[FeatureFlag]):
    """Queries over ``feature_flags`` and their per-environment state."""

    model = FeatureFlag

    def build_query(
        self,
        *,
        search: str | None = None,
        environment: FlagEnvironment | None = None,
        enabled: bool | None = None,
    ) -> Select[tuple[FeatureFlag]]:
        """Compose the filtered flag list query."""
        statement = select(FeatureFlag)
        if search:
            pattern = f"%{search.lower()}%"
            statement = statement.where(
                func.lower(FeatureFlag.name).like(pattern)
                | func.lower(FeatureFlag.key).like(pattern)
                | func.lower(FeatureFlag.description).like(pattern)
            )
        if environment is not None or enabled is not None:
            statement = statement.join(FeatureFlag.environments)
            if environment is not None:
                statement = statement.where(FeatureFlagState.environment == environment)
            if enabled is not None:
                statement = statement.where(FeatureFlagState.enabled.is_(enabled))
        return statement.order_by(FeatureFlag.name)

    def get_by_key(self, key: str) -> FeatureFlag | None:
        """Return a flag by its SDK key."""
        statement = select(FeatureFlag).where(FeatureFlag.key == key)
        return self.session.execute(statement).scalars().unique().first()

    def add_state(self, state: FeatureFlagState) -> FeatureFlagState:
        """Persist a per-environment state row."""
        self.session.add(state)
        self.session.flush()
        self.session.refresh(state)
        return state
