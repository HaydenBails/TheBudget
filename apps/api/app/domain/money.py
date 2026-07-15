"""Exact integer-cent money operations.

Decimal text is accepted only at an input boundary. All returned values and
arithmetic operands are integer cents; floats are deliberately unsupported.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_DECIMAL_AMOUNT = re.compile(r"(?P<sign>[+-]?)(?P<whole>0|[1-9]\d*)(?:\.(?P<fraction>\d{1,2}))?")


def _require_cents(value: int) -> int:
    if type(value) is not int:
        raise TypeError("cent amounts must be integers")
    return value


def parse_cents(value: str) -> int:
    """Parse strict decimal currency text into integer cents.

    Accepted examples are ``"12"``, ``"12.3"``, ``"12.34"``, and
    ``"-0.05"``. Currency symbols, grouping separators, surrounding
    whitespace, exponent notation, and more than two fractional digits are
    rejected instead of guessed.
    """

    if not isinstance(value, str):
        raise TypeError("currency input must be a decimal string")

    match = _DECIMAL_AMOUNT.fullmatch(value)
    if match is None:
        raise ValueError("currency input must be unambiguous decimal text")

    fraction = (match.group("fraction") or "").ljust(2, "0")
    cents = int(match.group("whole")) * 100 + int(fraction or "0")
    return -cents if match.group("sign") == "-" else cents


def add_cents(left: int, right: int) -> int:
    """Add two exact integer-cent amounts."""

    return _require_cents(left) + _require_cents(right)


def sum_cents(amounts: Iterable[int]) -> int:
    """Sum exact integer-cent amounts, rejecting non-integer members."""

    total = 0
    for amount in amounts:
        total += _require_cents(amount)
    return total
