"""Schemas shared across every tool's API."""

from collections.abc import Sequence
from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

ItemT = TypeVar("ItemT")


def page_count(total: int, page_size: int) -> int:
    """Return how many pages ``total`` records span."""
    return ceil(total / page_size) if page_size else 0


class ORMModel(BaseModel):
    """Base for response schemas read directly off ORM instances."""

    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[ItemT]):
    """A single page of results plus the pagination envelope."""

    items: list[ItemT]
    total: int = Field(description="Total matching records, ignoring pagination")
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(
        cls, items: Sequence[ItemT], *, total: int, page: int, page_size: int
    ) -> "Page[ItemT]":
        """Assemble a page response from a result slice."""
        return cls(
            items=list(items),
            total=total,
            page=page,
            page_size=page_size,
            pages=page_count(total, page_size),
        )


class ErrorDetail(BaseModel):
    """Body of the platform's structured error envelope."""

    code: str
    message: str
    details: dict[str, object] = {}
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Shape returned by every failing endpoint."""

    error: ErrorDetail


class MessageResponse(BaseModel):
    """Simple acknowledgement payload."""

    message: str
