"""Validation and response schemas for spending categories."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.common import TimestampedRead

CategoryName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
CategoryColor = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
CategoryIcon = Annotated[str, StringConstraints(max_length=16)]


class CategoryCreate(BaseModel):
    """Fields accepted when creating a category under a scoped profile."""

    model_config = ConfigDict(extra="forbid")

    name: CategoryName
    color: CategoryColor
    icon: CategoryIcon = ""
    parent_id: int | None = None
    excluded_from_spending: bool = False


class CategoryUpdate(BaseModel):
    """Mutable category fields; omission leaves the stored value unchanged."""

    model_config = ConfigDict(extra="forbid")

    name: CategoryName | None = None
    color: CategoryColor | None = None
    icon: CategoryIcon | None = None
    parent_id: int | None = None
    excluded_from_spending: bool | None = None
    sort_order: int | None = None
    is_archived: bool | None = None


class CategoryRead(TimestampedRead):
    """Serialized persisted category with explicit profile ownership."""

    profile_id: int
    slug: str
    name: str
    color: str
    icon: str
    parent_id: int | None
    excluded_from_spending: bool
    is_default: bool
    sort_order: int
    is_archived: bool
