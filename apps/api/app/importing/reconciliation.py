"""Exact monetary parsing and statement reconciliation primitives."""

from __future__ import annotations

import re
from collections.abc import Iterable
from decimal import Decimal

from app.domain.money import sum_cents
from app.importing.contracts import ReconciliationResult, TransactionCandidate
from app.importing.errors import InvalidExchangeRateError

_EXCHANGE_RATE = re.compile(r"(?:0|[1-9]\d*)(?:\.\d{1,8})?")
_EXCHANGE_RATE_SCALE = Decimal("0.00000001")


def parse_exchange_rate(value: str) -> Decimal:
    """Parse a positive plain-decimal rate at a fixed eight-place precision."""

    if not isinstance(value, str):
        raise InvalidExchangeRateError("exchange rate must be decimal text, never float")
    if _EXCHANGE_RATE.fullmatch(value) is None:
        raise InvalidExchangeRateError(
            "exchange rate must be positive plain decimal text with at most 8 places"
        )
    rate = Decimal(value)
    if rate <= 0:
        raise InvalidExchangeRateError("exchange rate must be greater than zero")
    return rate.quantize(_EXCHANGE_RATE_SCALE)


def reconcile_totals(
    expected_cents: int,
    transactions: Iterable[TransactionCandidate],
    *,
    tolerance_cents: int = 1,
) -> ReconciliationResult:
    """Compare an issuer total with parsed signed cents without rounding."""

    if type(expected_cents) is not int:
        raise TypeError("expected_cents must be integer cents")
    if type(tolerance_cents) is not int or tolerance_cents < 0:
        raise ValueError("tolerance_cents must be a non-negative integer")
    candidates = tuple(transactions)
    parsed_cents = sum_cents(candidate.amount_cents for candidate in candidates)
    delta_cents = parsed_cents - expected_cents
    status = "reconciled" if abs(delta_cents) <= tolerance_cents else "needs_review"
    return ReconciliationResult(
        status=status,
        expected_cents=expected_cents,
        parsed_cents=parsed_cents,
        delta_cents=delta_cents,
        tolerance_cents=tolerance_cents,
        transaction_count=len(candidates),
    )
