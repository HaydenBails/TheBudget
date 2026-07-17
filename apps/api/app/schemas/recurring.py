"""Validation and response schemas for recurring charges (product plan §12)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import TimestampedRead

RecurringStatus = Literal["keep", "review", "cancel", "ended", "ignored"]


class RecurringSeriesUpdate(BaseModel):
    """User-mutable recurring-series fields; detection owns the rest."""

    model_config = ConfigDict(extra="forbid")

    status: RecurringStatus | None = None
    confirmed_by_user: bool | None = None
    reminder_lead_days: int | None = None
    display_name: str | None = None


class RecurringSeriesRead(TimestampedRead):
    """Serialized persisted recurring series with explicit profile ownership."""

    profile_id: int
    account_id: int | None
    category_id: int | None
    merchant_key: str
    display_name: str
    amount_cents: int
    amount_min_cents: int
    amount_max_cents: int
    cadence: Literal["weekly", "biweekly", "monthly", "quarterly", "annual"]
    interval_days: int
    confidence: Literal["high", "medium", "low"]
    status: RecurringStatus
    confirmed_by_user: bool
    reminder_lead_days: int
    occurrence_count: int
    first_charge_date: date
    last_charge_date: date
    next_expected_date: date
    rationale: str


class RecurringDetectResult(BaseModel):
    """Summary of a detection run."""

    model_config = ConfigDict(from_attributes=True)

    detected: int
    created: int
    updated: int
    series: list[RecurringSeriesRead]
