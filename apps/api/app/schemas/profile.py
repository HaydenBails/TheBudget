"""Validation and response schemas for profiles."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.common import TimestampedRead

ProfileName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class ProfileCreate(BaseModel):
    """Fields accepted when creating a profile."""

    model_config = ConfigDict(extra="forbid")

    name: ProfileName
    base_currency: Literal["CAD"] = "CAD"


class ProfileUpdate(BaseModel):
    """Mutable profile fields; omission leaves the stored value unchanged."""

    model_config = ConfigDict(extra="forbid")

    name: ProfileName | None = None
    is_archived: bool | None = None


class ProfileRead(TimestampedRead):
    """Serialized persisted profile."""

    name: str
    base_currency: Literal["CAD"]
    is_archived: bool
