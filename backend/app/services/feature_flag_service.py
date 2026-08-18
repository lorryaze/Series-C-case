"""Business logic for the feature flags admin panel."""

from typing import Sequence

from sqlalchemy.orm import Session

from app.factories.feature_flag_factory import FeatureFlagFactory
from app.models.audit import AuditLog
from app.models.enums import AuditAction, AuditEntity, FlagEnvironment
from app.models.feature_flag import FeatureFlag, FeatureFlagState
from app.models.user import User
from app.repositories.feature_flag_repository import FeatureFlagRepository
from app.schemas.feature_flag import (
    FeatureFlagCreate,
    FeatureFlagStateUpdate,
    FeatureFlagUpdate,
)
from app.services.audit_service import AuditService
from app.utils.errors import ConflictError, NotFoundError, ValidationError


class FeatureFlagService:
    """Manages flag definitions and their per-environment rollout."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.flags = FeatureFlagRepository(session)
        self.audit = AuditService(session)

    def list_flags(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        environment: FlagEnvironment | None = None,
        enabled: bool | None = None,
    ) -> tuple[Sequence[FeatureFlag], int]:
        """Return a filtered page of flags plus the total match count."""
        statement = self.flags.build_query(
            search=search, environment=environment, enabled=enabled
        )
        return self.flags.paginate(statement, page=page, page_size=page_size)

    def get_flag(self, flag_id: int) -> FeatureFlag:
        """Return one flag or raise ``NotFoundError``."""
        flag = self.flags.get(flag_id)
        if flag is None:
            raise NotFoundError(f"Feature flag {flag_id} was not found")
        return flag

    def create_flag(self, payload: FeatureFlagCreate, *, actor: User) -> FeatureFlag:
        """Create a flag, initialised in every environment."""
        flag = FeatureFlagFactory.build(payload)
        if self.flags.get_by_key(flag.key) is not None:
            raise ConflictError(
                f"A feature flag with key '{flag.key}' already exists",
                details={"key": flag.key},
            )
        flag.modified_by_id = actor.id
        flag = self.flags.add(flag)
        self.audit.record(
            entity_type=AuditEntity.FEATURE_FLAG,
            entity_id=flag.id,
            action=AuditAction.CREATED,
            actor=actor,
            new_value=flag.key,
        )
        self.session.commit()
        return flag

    def update_flag(
        self, flag_id: int, payload: FeatureFlagUpdate, *, actor: User
    ) -> FeatureFlag:
        """Update flag metadata, auditing each changed field."""
        flag = self.get_flag(flag_id)
        updates = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not updates:
            raise ValidationError("No fields to update were provided")

        changes = {field: (getattr(flag, field), value) for field, value in updates.items()}
        self.flags.update(flag, {**updates, "modified_by_id": actor.id})
        self.audit.record_field_changes(
            entity_type=AuditEntity.FEATURE_FLAG,
            entity_id=flag.id,
            actor=actor,
            changes=changes,
        )
        self.session.commit()
        return flag

    def toggle(
        self, flag_id: int, *, environment: FlagEnvironment, enabled: bool, actor: User
    ) -> FeatureFlag:
        """Flip a flag on or off in one environment."""
        return self.update_state(
            flag_id,
            environment=environment,
            payload=FeatureFlagStateUpdate(enabled=enabled),
            actor=actor,
            action=AuditAction.TOGGLED,
        )

    def update_state(
        self,
        flag_id: int,
        *,
        environment: FlagEnvironment,
        payload: FeatureFlagStateUpdate,
        actor: User,
        action: AuditAction = AuditAction.UPDATED,
    ) -> FeatureFlag:
        """Update enablement and/or rollout percentage in one environment."""
        flag = self.get_flag(flag_id)
        updates = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not updates:
            raise ValidationError("Provide 'enabled' and/or 'rollout_percentage'")

        state = flag.state_for(environment)
        if state is None:
            state = self.flags.add_state(
                FeatureFlagFactory.build_state(environment=environment)
            )
            state.flag_id = flag.id
            self.session.flush()

        changes = {
            f"{environment.value}.{field}": (getattr(state, field), value)
            for field, value in updates.items()
        }
        for field, value in updates.items():
            setattr(state, field, value)
        self.flags.update(flag, {"modified_by_id": actor.id})
        self.audit.record_field_changes(
            entity_type=AuditEntity.FEATURE_FLAG,
            entity_id=flag.id,
            actor=actor,
            changes=changes,
            action=action,
        )
        self.session.commit()
        self.session.refresh(flag)
        return flag

    def history(self, flag_id: int) -> Sequence[AuditLog]:
        """Return the changelog for one flag."""
        flag = self.get_flag(flag_id)
        return self.audit.trail_for(AuditEntity.FEATURE_FLAG, flag.id)

    def state_for(self, flag: FeatureFlag, environment: FlagEnvironment) -> FeatureFlagState:
        """Return a flag's state in ``environment``, or fail if uninitialised."""
        state = flag.state_for(environment)
        if state is None:
            raise NotFoundError(
                f"Flag '{flag.key}' has no state for environment {environment.value}"
            )
        return state
