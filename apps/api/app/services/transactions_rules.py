"""Pure domain rules for transactions: spending inclusion and split integrity.

Kept free of ORM/session state so they can be unit-tested and reused by the
transaction service (BE-10) and later analytics.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.services.errors import SplitSumError

# Types that count toward core spending by default (product plan §7.2).
# Refunds are included so they reduce net spending in their category; payments,
# transfers, cash advances, fees, interest, and income are excluded by default.
_DEFAULT_INCLUDED_TYPES = frozenset({"purchase", "refund"})


def default_included_for_type(transaction_type: str) -> bool:
    """Return the default spending-inclusion decision for a transaction type."""

    return transaction_type in _DEFAULT_INCLUDED_TYPES


def validate_splits_sum(parent_amount_cents: int, split_amounts: Iterable[int]) -> None:
    """Raise ``SplitSumError`` unless the splits sum exactly to the parent.

    Amounts are integer cents; equality is exact (no floating point).
    """

    total = sum(split_amounts)
    if total != parent_amount_cents:
        raise SplitSumError(
            "split amounts must sum to the transaction amount: "
            f"got {total} cents, expected {parent_amount_cents} cents"
        )
