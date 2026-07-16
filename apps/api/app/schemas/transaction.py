"""Validation and response schemas for transactions, splits, and tags."""

from __future__ import annotations

from datetime import date as _date
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.common import ORMReadModel, TimestampedRead

TransactionType = Literal[
    "purchase",
    "refund",
    "payment",
    "transfer",
    "cash_advance",
    "fee",
    "interest",
    "income",
    "adjustment",
    "unknown",
]
Direction = Literal["debit", "credit"]
CategorizationStatus = Literal[
    "suggested", "confirmed", "rule_applied", "manual", "uncategorized"
]
Source = Literal["pdf_import", "csv_import", "manual"]

# JSON numbers cross the API boundary into JavaScript clients. Restrict cents to
# the signed integer range that JavaScript can represent exactly so no client can
# silently round a persisted amount while the database retains BigInteger storage.
MAX_SAFE_CENTS = (1 << 53) - 1
CentAmount = Annotated[int, Field(ge=-MAX_SAFE_CENTS, le=MAX_SAFE_CENTS)]
ExchangeRate = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)]

Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Merchant = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
ExclusionReason = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
TransactionIds = Annotated[list[int], Field(min_length=1, max_length=500)]


class SplitInput(BaseModel):
    """A single category allocation, in signed integer cents."""

    model_config = ConfigDict(extra="forbid")

    category_id: int
    amount_cents: CentAmount


class SplitRead(TimestampedRead):
    transaction_id: int
    category_id: int
    amount_cents: CentAmount


class TagCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: TagName


class TagRead(TimestampedRead):
    profile_id: int
    name: str


class TransactionCreate(BaseModel):
    """Fields accepted when creating a transaction under a scoped profile."""

    model_config = ConfigDict(extra="forbid")

    account_id: int
    date: _date
    posted_date: _date | None = None
    raw_description: Description
    merchant: Merchant = ""
    amount_cents: CentAmount
    currency: Literal["CAD"] = "CAD"
    direction: Direction
    type: TransactionType = "unknown"
    category_id: int | None = None
    notes: str | None = None
    source: Source = "manual"


class TransactionUpdate(BaseModel):
    """Mutable transaction fields; omission leaves the stored value unchanged."""

    model_config = ConfigDict(extra="forbid")

    date: _date | None = None
    posted_date: _date | None = None
    raw_description: Description | None = None
    merchant: Merchant | None = None
    amount_cents: CentAmount | None = None
    direction: Direction | None = None
    type: TransactionType | None = None
    category_id: int | None = None
    categorization_status: CategorizationStatus | None = None
    included_in_spending: bool | None = None
    exclusion_reason: str | None = None
    notes: str | None = None


class TransactionRead(TimestampedRead):
    profile_id: int
    account_id: int
    category_id: int | None
    date: _date
    posted_date: _date | None
    raw_description: str
    merchant: str
    amount_cents: CentAmount
    currency: Literal["CAD"]
    direction: Direction
    type: TransactionType
    categorization_status: CategorizationStatus
    included_in_spending: bool
    exclusion_reason: str | None
    recurring_series_id: int | None
    notes: str | None
    source: Source
    import_id: int | None
    source_row_reference: str | None = None
    transaction_fingerprint: str | None = None
    original_foreign_amount_cents: CentAmount | None = None
    original_foreign_currency: str | None = None
    exchange_rate: ExchangeRate | None = None
    deleted_at: datetime | None


class TransactionDetailRead(TransactionRead):
    """A transaction plus its editable split and tag allocations."""

    splits: list[SplitRead]
    tags: list[TagRead]


class TransactionSplitsReplace(BaseModel):
    """Replace all split allocations; an empty list clears existing splits."""

    model_config = ConfigDict(extra="forbid")

    splits: list[SplitInput]


class TransactionTagsReplace(BaseModel):
    """Replace all tags; an empty list clears existing tags."""

    model_config = ConfigDict(extra="forbid")

    tags: list[TagCreate]


class _TransactionBulkBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_ids: TransactionIds

    @field_validator("transaction_ids")
    @classmethod
    def transaction_ids_are_unique_and_positive(cls, value: list[int]) -> list[int]:
        if any(transaction_id <= 0 for transaction_id in value):
            raise ValueError("transaction IDs must be positive integers")
        if len(set(value)) != len(value):
            raise ValueError("transaction IDs must be unique")
        return value


class TransactionBulkCategorize(_TransactionBulkBase):
    """Assign one category (or null for uncategorized) to many transactions."""

    action: Literal["categorize"]
    category_id: int | None


class TransactionBulkSpendingInclusion(_TransactionBulkBase):
    """Include or exclude many transactions from core spending totals."""

    action: Literal["set_spending_inclusion"]
    included_in_spending: bool
    exclusion_reason: ExclusionReason | None = None

    @model_validator(mode="after")
    def excluded_rows_have_a_reason(self):
        if not self.included_in_spending and self.exclusion_reason is None:
            raise ValueError("exclusion_reason is required when excluding transactions")
        return self


TransactionBulkAction = Annotated[
    TransactionBulkCategorize | TransactionBulkSpendingInclusion,
    Field(discriminator="action"),
]


class TransactionBulkResult(BaseModel):
    """Atomic bulk-update result with an exact affected-row count."""

    updated_count: int
    transactions: list[TransactionRead]


class TransactionDeletedRead(ORMReadModel):
    """Lightweight acknowledgement for a soft delete/restore."""

    id: int
    deleted: bool
