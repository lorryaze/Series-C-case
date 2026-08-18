"""Generic repository implementing the data-access half of every tool."""

from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """CRUD and pagination primitives shared by all concrete repositories.

    Subclasses add query methods specific to their aggregate; nothing above this
    layer issues SQL directly.
    """

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> ModelT | None:
        """Return an entity by primary key, or ``None``."""
        return self.session.get(self.model, entity_id)

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[ModelT]:
        """Return entities in insertion order."""
        statement: Select[tuple[ModelT]] = select(self.model).offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        return self.session.execute(statement).scalars().all()

    def count(self) -> int:
        """Return the total number of stored entities."""
        statement = select(func.count()).select_from(self.model)
        return int(self.session.execute(statement).scalar_one())

    def add(self, entity: ModelT) -> ModelT:
        """Persist a new entity and refresh it from the database."""
        self.session.add(entity)
        self.session.flush()
        self.session.refresh(entity)
        return entity

    def add_all(self, entities: Sequence[ModelT]) -> Sequence[ModelT]:
        """Persist several entities in one flush."""
        self.session.add_all(entities)
        self.session.flush()
        return entities

    def update(self, entity: ModelT, values: dict[str, Any]) -> ModelT:
        """Apply ``values`` to ``entity`` and flush the change."""
        for field, value in values.items():
            setattr(entity, field, value)
        self.session.flush()
        self.session.refresh(entity)
        return entity

    def delete(self, entity: ModelT) -> None:
        """Remove an entity."""
        self.session.delete(entity)
        self.session.flush()

    def commit(self) -> None:
        """Commit the unit of work."""
        self.session.commit()

    def paginate(
        self, statement: Select[tuple[ModelT]], *, page: int, page_size: int
    ) -> tuple[Sequence[ModelT], int]:
        """Return one page of ``statement`` plus the unpaginated total."""
        total_statement = select(func.count()).select_from(statement.subquery())
        total = int(self.session.execute(total_statement).scalar_one())
        page_statement = statement.limit(page_size).offset((page - 1) * page_size)
        items = self.session.execute(page_statement).scalars().unique().all()
        return items, total
