"""Validation and response schemas for income schedules (product plan §10)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.common import TimestampedRead

IncomeName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
AmountCents = Annotated[int, Field(gt=0, le=(1 << 53) - 1)]
Frequency = Literal["weekly", "biweekly", "monthly"]


class IncomeScheduleCreate(BaseModel):
    """Fields accepted when creating an income schedule."""

    model_config = ConfigDict(extra="forbid")

    name: IncomeName
    amount_cents: AmountCents
    frequency: Frequency
    start_date: date
    end_date: date | None = None
    is_active: bool = True
    notes: str | None = None


class IncomeScheduleUpdate(BaseModel):
    """Mutable income-schedule fields; omission leaves the stored value."""

    model_config = ConfigDict(extra="forbid")

    name: IncomeName | None = None
    amount_cents: AmountCents | None = None
    frequency: Frequency | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None
    notes: str | None = None


class IncomeScheduleRead(TimestampedRead):
    """Serialized persisted income schedule with a derived next-expected date."""

    profile_id: int
    name: str
    amount_cents: int
    frequency: Frequency
    start_date: date
    end_date: date | None
    is_active: bool
    notes: str | None
    # Derived (not stored): first occurrence on or after today within the range.
    next_expected_date: date | None = None


class IncomeOccurrenceRead(BaseModel):
    """One forecast income receipt returned by the occurrences endpoint."""

    model_config = ConfigDict(from_attributes=True)

    schedule_id: int
    name: str
    occurrence_date: date
    amount_cents: int


class IncomeSummaryRead(BaseModel):
    """Expected-vs-recorded income for a selected period (§10)."""

    model_config = ConfigDict(from_attributes=True)

    period_start: date
    period_end: date
    expected_cents: int
    expected_remaining_cents: int
    occurrences: list[IncomeOccurrenceRead]
