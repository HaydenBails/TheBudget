"""Unit tests for the pure recurring-charge detection heuristics."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.recurring_rules import (
    RecurringObservation,
    detect_recurring_series,
    normalize_merchant,
)


def _obs(tid: int, day: date, merchant: str, cents: int, **kw: object) -> RecurringObservation:
    return RecurringObservation(
        transaction_id=tid,
        txn_date=day,
        merchant=merchant,
        raw_description=merchant,
        amount_cents=cents,
        category_id=kw.get("category_id"),  # type: ignore[arg-type]
        account_id=kw.get("account_id"),  # type: ignore[arg-type]
    )


def _monthly(merchant: str, cents: int, months: int, start: date, first_id: int = 1):
    out = []
    for i in range(months):
        month_index = start.month - 1 + i
        day = date(start.year + month_index // 12, month_index % 12 + 1, start.day)
        out.append(_obs(first_id + i, day, merchant, cents))
    return out


def test_normalize_merchant_strips_digits_and_punctuation() -> None:
    assert normalize_merchant("NETFLIX #12345", "") == "NETFLIX"
    assert normalize_merchant("", "SPOTIFY P1*STORE-99") == "SPOTIFY P STORE"
    assert normalize_merchant("A Very Long Merchant Name With Many Tokens", "") == (
        "A VERY LONG MERCHANT"
    )


def test_monthly_fixed_subscription_is_high_confidence() -> None:
    series = detect_recurring_series(_monthly("NETFLIX", 2099, 4, date(2026, 1, 15)))
    assert len(series) == 1
    s = series[0]
    assert s.merchant_key == "NETFLIX"
    assert s.cadence == "monthly"
    assert s.confidence == "high"
    assert s.occurrence_count == 4
    assert s.amount_cents == 2099
    assert s.next_expected_date == date(2026, 4, 15) + timedelta(days=s.interval_days)


def test_two_occurrences_are_low_confidence() -> None:
    obs = [
        _obs(1, date(2026, 6, 1), "GYM MEMBERSHIP", 5000),
        _obs(2, date(2026, 6, 15), "GYM MEMBERSHIP", 5000),
    ]
    series = detect_recurring_series(obs)
    assert len(series) == 1
    assert series[0].cadence == "biweekly"
    assert series[0].confidence == "low"


def test_weekly_cadence_detected() -> None:
    obs = [
        _obs(i + 1, date(2026, 6, 1) + timedelta(days=7 * i), "CLOUD BACKUP", 999)
        for i in range(4)
    ]
    series = detect_recurring_series(obs)
    assert series and series[0].cadence == "weekly"
    assert series[0].confidence == "high"


def test_irregular_frequent_merchant_is_not_recurring() -> None:
    # Groceries several times a week at irregular gaps must be excluded (§12.1).
    days = [0, 2, 3, 9, 10, 11, 17, 20]
    obs = [
        _obs(i + 1, date(2026, 6, 1) + timedelta(days=d), "LOBLAWS", 4000 + i * 100)
        for i, d in enumerate(days)
    ]
    assert detect_recurring_series(obs) == []


def test_variable_utility_is_recurring_but_medium_confidence() -> None:
    obs = _monthly("HYDRO ONE", 9000, 1, date(2026, 1, 10))
    obs += [_obs(2, date(2026, 2, 10), "HYDRO ONE", 12000)]
    obs += [_obs(3, date(2026, 3, 10), "HYDRO ONE", 7000)]
    series = detect_recurring_series(obs)
    assert len(series) == 1
    s = series[0]
    assert s.cadence == "monthly"
    assert s.confidence == "medium"  # regular interval, but amounts vary
    assert s.amount_min_cents == 7000
    assert s.amount_max_cents == 12000


def test_results_are_sorted_by_next_expected_date() -> None:
    obs = _monthly("NETFLIX", 2099, 3, date(2026, 1, 5), first_id=1)
    obs += _monthly("SPOTIFY", 1099, 3, date(2026, 1, 20), first_id=100)
    series = detect_recurring_series(obs)
    assert [s.merchant_key for s in series] == ["NETFLIX", "SPOTIFY"]
    assert series[0].next_expected_date <= series[1].next_expected_date


def test_distinct_merchants_are_not_merged() -> None:
    obs = _monthly("NETFLIX", 2099, 3, date(2026, 1, 5), first_id=1)
    obs += _monthly("SPOTIFY", 1099, 3, date(2026, 1, 6), first_id=100)
    series = detect_recurring_series(obs)
    assert {s.merchant_key for s in series} == {"NETFLIX", "SPOTIFY"}
