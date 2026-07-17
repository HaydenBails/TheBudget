"""Pure, persistence-free income-schedule occurrence generation (§10).

Forecast occurrences are computed on demand for a bounded date range so the
system never persists infinite future records. Kept free of ORM/session state
so the date math can be unit-tested in isolation.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

Frequency = Literal["weekly", "biweekly", "monthly"]

# Hard cap on generated occurrences to bound any single range request.
_MAX_OCCURRENCES = 1000


@dataclass(frozen=True, slots=True)
class IncomeOccurrence:
    """One forecast income receipt on a specific date."""

    occurrence_date: date
    amount_cents: int


def _add_months(day: date, months: int) -> date:
    total = day.month - 1 + months
    year = day.year + total // 12
    month = total % 12 + 1
    clamped_day = min(day.day, calendar.monthrange(year, month)[1])
    return date(year, month, clamped_day)


def _nth_occurrence(start: date, frequency: Frequency, index: int) -> date:
    if frequency == "weekly":
        return start + timedelta(days=7 * index)
    if frequency == "biweekly":
        return start + timedelta(days=14 * index)
    return _add_months(start, index)


def generate_occurrence_dates(
    start: date,
    frequency: Frequency,
    range_from: date,
    range_to: date,
    *,
    end: date | None = None,
) -> list[date]:
    """Return occurrence dates within ``[range_from, range_to]`` (inclusive).

    Occurrences never precede ``start`` or follow ``end`` when an end is set.
    """

    if range_to < start:
        return []
    dates: list[date] = []
    for index in range(_MAX_OCCURRENCES):
        occurrence = _nth_occurrence(start, frequency, index)
        if occurrence > range_to or (end is not None and occurrence > end):
            break
        if occurrence >= range_from:
            dates.append(occurrence)
    return dates


def next_occurrence_on_or_after(
    start: date,
    frequency: Frequency,
    pivot: date,
    *,
    end: date | None = None,
) -> date | None:
    """Return the first occurrence on or after ``pivot``, or ``None`` past end."""

    for index in range(_MAX_OCCURRENCES):
        occurrence = _nth_occurrence(start, frequency, index)
        if end is not None and occurrence > end:
            return None
        if occurrence >= pivot:
            return occurrence
    return None
