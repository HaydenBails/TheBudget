"""Validation and response schemas for merchant auto-categorization rules."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.common import TimestampedRead

MatchType = Literal["exact", "prefix", "contains"]
Pattern = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class MerchantRuleCreate(BaseModel):
    """Fields accepted when creating a merchant rule."""

    model_config = ConfigDict(extra="forbid")

    pattern: Pattern
    category_id: int
    match_type: MatchType = "contains"


class MerchantRuleUpdate(BaseModel):
    """Mutable merchant-rule fields."""

    model_config = ConfigDict(extra="forbid")

    pattern: Pattern | None = None
    category_id: int | None = None
    match_type: MatchType | None = None
    is_active: bool | None = None


class MerchantRuleRead(TimestampedRead):
    """Serialized persisted merchant rule."""

    profile_id: int
    category_id: int
    pattern: str
    match_type: MatchType
    hit_count: int
    is_active: bool
    is_default: bool


class MerchantRuleApplyResult(BaseModel):
    """Summary of applying rules to uncategorized transactions."""

    model_config = ConfigDict(from_attributes=True)

    categorized: int


class MerchantRuleLearnResult(BaseModel):
    """Summary of learning rules from already-categorized transactions."""

    model_config = ConfigDict(from_attributes=True)

    created: int
    updated: int
