"""Issuer-neutral, persistence-free statement parser contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

TransactionType = Literal[
    "purchase",
    "payment",
    "transfer",
    "refund",
    "cash_advance",
    "interest",
    "fee",
    "income",
]
TransactionDirection = Literal["debit", "credit"]
ReconciliationStatus = Literal["reconciled", "needs_review"]


@dataclass(frozen=True, slots=True, repr=False)
class ExtractedDocument:
    """Ephemeral text extracted from one validated server-side PDF."""

    document_id: str
    sha256: str
    sanitized_filename: str
    byte_count: int
    page_count: int
    pages: tuple[str, ...] = field(repr=False)


@dataclass(frozen=True, slots=True)
class ParserDetection:
    """One parser's deterministic detection result."""

    matched: bool
    confidence: Decimal
    reason_code: str

    def __post_init__(self) -> None:
        if type(self.matched) is not bool:
            raise TypeError("matched must be a boolean")
        if not isinstance(self.confidence, Decimal):
            raise TypeError("confidence must be Decimal")
        if not self.confidence.is_finite() or not (
            Decimal("0") <= self.confidence <= Decimal("1")
        ):
            raise ValueError("confidence must be between zero and one")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError("reason_code must not be empty")


@dataclass(frozen=True, slots=True, repr=False)
class StatementMetadata:
    """Issuer-neutral statement facts; never contains a full account number."""

    issuer: str
    account_last4: str | None
    period_start: date | None
    period_end: date | None
    currency: str = "CAD"
    expected_activity_cents: int | None = None
    expected_debits_cents: int | None = None
    expected_credits_cents: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.issuer, str) or not self.issuer.strip():
            raise ValueError("issuer must not be empty")
        if not isinstance(self.currency, str) or re.fullmatch(r"[A-Z]{3}", self.currency) is None:
            raise ValueError("currency must be a three-letter uppercase code")
        if self.period_start is not None and type(self.period_start) is not date:
            raise TypeError("period_start must be a date")
        if self.period_end is not None and type(self.period_end) is not date:
            raise TypeError("period_end must be a date")
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_start > self.period_end
        ):
            raise ValueError("statement period start must not follow its end")
        if self.account_last4 is not None and (
            len(self.account_last4) != 4 or not self.account_last4.isdigit()
        ):
            raise ValueError("account_last4 must contain exactly four digits")
        for name in (
            "expected_activity_cents",
            "expected_debits_cents",
            "expected_credits_cents",
        ):
            value = getattr(self, name)
            if value is not None and type(value) is not int:
                raise TypeError(f"{name} must be integer cents")


@dataclass(frozen=True, slots=True, repr=False)
class TransactionCandidate:
    """Canonical transaction extracted from a statement, before persistence."""

    source_index: int
    occurrence_index: int
    transaction_date: date
    posted_date: date | None
    raw_description: str = field(repr=False)
    amount_cents: int
    txn_type: TransactionType
    direction: TransactionDirection
    original_currency: str | None = None
    original_amount_cents: int | None = None
    exchange_rate: Decimal | None = None

    def __post_init__(self) -> None:
        if type(self.source_index) is not int or self.source_index < 0:
            raise ValueError("source_index must be non-negative")
        if type(self.occurrence_index) is not int or self.occurrence_index < 0:
            raise ValueError("occurrence_index must be non-negative")
        if type(self.transaction_date) is not date:
            raise TypeError("transaction_date must be a date")
        if self.posted_date is not None and type(self.posted_date) is not date:
            raise TypeError("posted_date must be a date")
        if not isinstance(self.raw_description, str) or not self.raw_description.strip():
            raise ValueError("raw_description must not be empty")
        if type(self.amount_cents) is not int:
            raise TypeError("amount_cents must be integer cents")
        if self.amount_cents == 0:
            raise ValueError("amount_cents must be nonzero")
        if self.txn_type not in {
            "purchase", "payment", "transfer", "refund", "cash_advance",
            "interest", "fee", "income",
        }:
            raise ValueError("txn_type is not supported")
        if self.direction not in {"debit", "credit"}:
            raise ValueError("direction is not supported")
        if (self.direction == "debit") != (self.amount_cents > 0):
            raise ValueError("direction must match the signed cent amount")
        if self.original_amount_cents is not None and type(self.original_amount_cents) is not int:
            raise TypeError("original_amount_cents must be integer cents")
        if self.original_amount_cents == 0:
            raise ValueError("original_amount_cents must be nonzero")
        if self.original_amount_cents is not None and (
            (self.direction == "debit") != (self.original_amount_cents > 0)
        ):
            raise ValueError("original amount sign must match direction")
        if self.exchange_rate is not None and not isinstance(self.exchange_rate, Decimal):
            raise TypeError("exchange_rate must be Decimal")
        foreign_values = (
            self.original_currency,
            self.original_amount_cents,
            self.exchange_rate,
        )
        if any(value is not None for value in foreign_values) != all(
            value is not None for value in foreign_values
        ):
            raise ValueError(
                "foreign currency, amount, and exchange rate must be supplied together"
            )
        if (
            self.original_currency is not None
            and re.fullmatch(r"[A-Z]{3}", self.original_currency) is None
        ):
            raise ValueError("original_currency must be a three-letter uppercase code")
        if self.exchange_rate is not None and (
            not self.exchange_rate.is_finite()
            or self.exchange_rate <= 0
            or self.exchange_rate.as_tuple().exponent < -8
        ):
            raise ValueError("exchange_rate must be positive, finite, and use at most 8 places")


@dataclass(frozen=True, slots=True, repr=False)
class ReconciliationResult:
    """Exact-cent reconciliation summary safe to persist or log."""

    status: ReconciliationStatus
    expected_cents: int
    parsed_cents: int
    delta_cents: int
    tolerance_cents: int
    transaction_count: int
