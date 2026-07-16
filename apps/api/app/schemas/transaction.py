"""Validation and response schemas for transactions, splits, and tags."""

from __future__ import annotations

from datetime import date as _date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.common import ORMReadModel, TimestampedRead

TransactionType = Literal[
    "purchase",
    "refund",
    "payment",
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

Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Merchant = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]


class SplitInput(BaseModel):
    """A single category allocation, in signed integer cents."""

    model_config = ConfigDict(extra="forbid")

    category_id: int
    amount_cents: int


class SplitRead(TimestampedRead):
    transaction_id: int
    category_id: int
    amount_cents: int


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
    amount_cents: int
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
    merchant: Merchant | None = None
    amount_cents: int | None = None
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
    amount_cents: int
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


class TransactionDeletedRead(ORMReadModel):
    """Lightweight acknowledgement for a soft delete/restore."""

    id: int
    deleted: bool
