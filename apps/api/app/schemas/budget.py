"""Validation and response schemas for monthly budgets."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.common import TimestampedRead

# Calendar month the budget applies to, e.g. "2026-07".
PeriodMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
# Money is integer cents; a budget limit is a strictly positive magnitude.
LimitCents = Annotated[int, Field(gt=0, le=(1 << 53) - 1)]


class BudgetCreate(BaseModel):
    """Fields accepted when setting a budget under a scoped profile."""

    model_config = ConfigDict(extra="forbid")

    category_id: int | None = None
    period_month: PeriodMonth
    limit_cents: LimitCents


class BudgetUpdate(BaseModel):
    """Mutable budget fields; category and month identify the target and are fixed."""

    model_config = ConfigDict(extra="forbid")

    limit_cents: LimitCents | None = None


class BudgetRead(TimestampedRead):
    """Serialized persisted budget with explicit profile ownership."""

    profile_id: int
    category_id: int | None
    period_month: str
    limit_cents: int
