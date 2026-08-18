"""Factory for feature flag domain objects."""

import re

from app.models.enums import FlagEnvironment
from app.models.feature_flag import FeatureFlag, FeatureFlagState
from app.schemas.feature_flag import FeatureFlagCreate

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


def slugify_key(name: str) -> str:
    """Turn a human flag name into a snake_case SDK key."""
    return _NON_SLUG_CHARS.sub("_", name.strip().lower()).strip("_")


class FeatureFlagFactory:
    """Creates flags together with a state row for every environment."""

    @classmethod
    def build(cls, payload: FeatureFlagCreate) -> FeatureFlag:
        """Create an unpersisted flag with all environments initialised."""
        key = payload.key.strip() if payload.key else slugify_key(payload.name)
        flag = FeatureFlag(
            key=slugify_key(key),
            name=payload.name.strip(),
            description=payload.description.strip(),
            default_enabled=payload.default_enabled,
        )
        flag.environments = [
            cls.build_state(
                environment=environment,
                enabled=payload.default_enabled,
                rollout_percentage=100 if payload.default_enabled else 0,
            )
            for environment in FlagEnvironment
        ]
        return flag

    @staticmethod
    def build_state(
        *, environment: FlagEnvironment, enabled: bool = False, rollout_percentage: int = 0
    ) -> FeatureFlagState:
        """Create an unpersisted per-environment state row."""
        return FeatureFlagState(
            environment=environment,
            enabled=enabled,
            rollout_percentage=rollout_percentage,
        )
