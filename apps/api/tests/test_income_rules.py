"""Unit tests for pure income occurrence generation."""

from __future__ import annotations

from datetime import date

from app.services.income_rules import (
    generate_occurrence_dates,
    next_occurrence_on_or_after,
)


def test_weekly_occurrences_in_range() -> None:
    dates = generate_occurrence_dates(
        date(2026, 6, 1), "weekly", date(2026, 6, 1), date(2026, 6, 30)
    )
    assert dates == [date(2026, 6, d) for d in (1, 8, 15, 22, 29)]


def test_biweekly_occurrences_respect_start() -> None:
    dates = generate_occurrence_dates(
        date(2026, 6, 5), "biweekly", date(2026, 6, 1), date(2026, 7, 31)
    )
    assert dates == [
        date(2026, 6, 5),
        date(2026, 6, 19),
        date(2026, 7, 3),
        date(2026, 7, 17),
        date(2026, 7, 31),
    ]


def test_monthly_occurrences_clamp_end_of_month() -> None:
    dates = generate_occurrence_dates(
        date(2026, 1, 31), "monthly", date(2026, 1, 1), date(2026, 4, 30)
    )
    # Feb clamps to the 28th; the schedule anchors on the 31st.
    assert dates == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]


def test_end_date_bounds_occurrences() -> None:
    dates = generate_occurrence_dates(
        date(2026, 6, 1), "weekly", date(2026, 6, 1), date(2026, 6, 30), end=date(2026, 6, 15)
    )
    assert dates == [date(2026, 6, 1), date(2026, 6, 8), date(2026, 6, 15)]


def test_range_before_start_is_empty() -> None:
    assert generate_occurrence_dates(
        date(2026, 6, 10), "weekly", date(2026, 5, 1), date(2026, 6, 1)
    ) == []


def test_next_occurrence_on_or_after() -> None:
    weekly = next_occurrence_on_or_after(date(2026, 6, 1), "weekly", date(2026, 6, 10))
    assert weekly == date(2026, 6, 15)
    monthly = next_occurrence_on_or_after(date(2026, 6, 1), "monthly", date(2026, 6, 1))
    assert monthly == date(2026, 6, 1)


def test_next_occurrence_returns_none_past_end() -> None:
    assert (
        next_occurrence_on_or_after(
            date(2026, 6, 1), "weekly", date(2026, 7, 1), end=date(2026, 6, 20)
        )
        is None
    )
