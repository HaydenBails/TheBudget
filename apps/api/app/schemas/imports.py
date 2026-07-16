"""Privacy-safe persistence contracts for statement import staging."""

from __future__ import annotations

import unicodedata
from datetime import date
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

from app.schemas.common import TimestampedRead
from app.schemas.transaction import CentAmount, Direction, TransactionType

HashHex = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, pattern=r"^[0-9a-f]{64}$"),
]
SafeName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
Description = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
Merchant = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
ExchangeRate = Annotated[
    Decimal,
    Field(gt=0, max_digits=18, decimal_places=8),
]
NonNegativeCount = Annotated[int, Field(ge=0)]

ImportStatus = Literal["staged", "ready", "committed", "cancelled", "failed"]
ValidationStatus = Literal[
    "validated", "validated_with_warnings", "needs_review", "failed"
]
ImportDuplicateDecision = Literal[
    "new", "blocked_file_hash", "blocked_logical_key", "potential_overlap"
]
StagedStatus = Literal["pending", "accepted", "skipped", "needs_review"]
StagedDuplicateDecision = Literal["new", "skip_exact", "potential_overlap", "keep"]
WarningSeverity = Literal["info", "warning", "error"]
LinkDecision = Literal["created", "linked_duplicate", "skipped"]


class ImportBatchCreate(BaseModel):
    """Structured metadata retained for one import attempt."""

    model_config = ConfigDict(extra="forbid")

    account_id: int
    issuer: ShortText
    source_filename: SafeName
    file_sha256: HashHex
    logical_statement_key: HashHex
    parser_name: ShortText
    parser_version: ShortText
    statement_start_date: date | None = None
    statement_end_date: date | None = None
    currency: Literal["CAD"] = "CAD"
    status: ImportStatus = "staged"
    validation_status: ValidationStatus
    duplicate_decision: ImportDuplicateDecision = "new"
    duplicate_of_import_id: int | None = None
    transaction_count: NonNegativeCount = 0
    purchase_count: NonNegativeCount = 0
    credit_count: NonNegativeCount = 0
    payment_count: NonNegativeCount = 0
    fee_interest_count: NonNegativeCount = 0
    unresolved_count: NonNegativeCount = 0
    expected_total_cents: CentAmount | None = None
    parsed_total_cents: CentAmount | None = None
    reconciliation_delta_cents: CentAmount | None = None
    purchase_total_cents: CentAmount | None = None
    credit_total_cents: CentAmount | None = None
    payment_total_cents: CentAmount | None = None
    fee_interest_total_cents: CentAmount | None = None

    @field_validator("source_filename")
    @classmethod
    def filename_is_a_sanitized_basename(cls, value: str) -> str:
        if (
            "/" in value
            or "\\" in value
            or value in {".", ".."}
            or any(unicodedata.category(char).startswith("C") for char in value)
        ):
            raise ValueError("source_filename must be a sanitized basename")
        return value

    @model_validator(mode="after")
    def dates_and_reconciliation_are_coherent(self):
        if (
            self.statement_start_date is not None
            and self.statement_end_date is not None
            and self.statement_start_date > self.statement_end_date
        ):
            raise ValueError("statement_start_date must not follow statement_end_date")
        if (
            self.expected_total_cents is not None
            and self.parsed_total_cents is not None
            and self.reconciliation_delta_cents
            != self.parsed_total_cents - self.expected_total_cents
        ):
            raise ValueError("reconciliation_delta_cents must equal parsed minus expected")
        return self


class ImportBatchRead(TimestampedRead):
    profile_id: int
    account_id: int
    issuer: str
    source_filename: str
    file_sha256: str
    logical_statement_key: str
    parser_name: str
    parser_version: str
    statement_start_date: date | None
    statement_end_date: date | None
    currency: Literal["CAD"]
    status: ImportStatus
    validation_status: ValidationStatus
    duplicate_decision: ImportDuplicateDecision
    duplicate_of_import_id: int | None
    transaction_count: int
    purchase_count: int
    credit_count: int
    payment_count: int
    fee_interest_count: int
    unresolved_count: int
    expected_total_cents: CentAmount | None
    parsed_total_cents: CentAmount | None
    reconciliation_delta_cents: CentAmount | None
    purchase_total_cents: CentAmount | None
    credit_total_cents: CentAmount | None
    payment_total_cents: CentAmount | None
    fee_interest_total_cents: CentAmount | None


class ImportStagedTransactionCreate(BaseModel):
    """Canonical structured candidate; never contains a full statement page."""

    model_config = ConfigDict(extra="forbid")

    account_id: int
    source_row_reference: ShortText
    date: date
    posted_date: date | None = None
    raw_description: Description
    merchant: Merchant = ""
    amount_cents: CentAmount
    currency: Literal["CAD"] = "CAD"
    direction: Direction
    type: TransactionType
    included_in_spending: bool
    exclusion_reason: str | None = None
    original_foreign_amount_cents: CentAmount | None = None
    original_foreign_currency: CurrencyCode | None = None
    exchange_rate: ExchangeRate | None = None
    transaction_fingerprint: HashHex
    occurrence_index: NonNegativeCount = 0
    duplicate_decision: StagedDuplicateDecision = "new"
    status: StagedStatus = "pending"

    @field_validator("exchange_rate", mode="before")
    @classmethod
    def exchange_rate_is_never_float(cls, value):
        if isinstance(value, float):
            raise ValueError("exchange_rate must use Decimal or decimal text, never float")
        return value

    @model_validator(mode="after")
    def money_fields_are_coherent(self):
        if self.amount_cents == 0:
            raise ValueError("amount_cents must be nonzero")
        if self.direction == "debit" and self.amount_cents < 0:
            raise ValueError("debit amounts must be positive")
        if self.direction == "credit" and self.amount_cents > 0:
            raise ValueError("credit amounts must be negative")
        has_foreign_amount = self.original_foreign_amount_cents is not None
        has_foreign_currency = self.original_foreign_currency is not None
        if has_foreign_amount != has_foreign_currency:
            raise ValueError("foreign amount and currency must be supplied together")
        if self.exchange_rate is not None and not has_foreign_amount:
            raise ValueError("exchange_rate requires a foreign amount and currency")
        return self


class ImportStagedTransactionRead(TimestampedRead):
    profile_id: int
    import_batch_id: int
    account_id: int
    source_row_reference: str
    date: date
    posted_date: date | None
    raw_description: str
    merchant: str
    amount_cents: CentAmount
    currency: Literal["CAD"]
    direction: Direction
    type: TransactionType
    included_in_spending: bool
    exclusion_reason: str | None
    original_foreign_amount_cents: CentAmount | None
    original_foreign_currency: str | None
    exchange_rate: ExchangeRate | None
    transaction_fingerprint: str
    occurrence_index: int
    duplicate_decision: StagedDuplicateDecision
    status: StagedStatus


class ImportWarningCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ShortText
    severity: WarningSeverity
    message: Description
    source_row_reference: ShortText | None = None


class ImportWarningRead(TimestampedRead):
    profile_id: int
    import_batch_id: int
    code: str
    severity: WarningSeverity
    message: str
    source_row_reference: str | None


class ImportTransactionLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    staged_transaction_id: int
    transaction_id: int
    decision: LinkDecision


class ImportTransactionLinkRead(TimestampedRead):
    profile_id: int
    import_batch_id: int
    account_id: int
    staged_transaction_id: int
    transaction_id: int
    decision: LinkDecision


class ImportCandidateResponse(BaseModel):
    """Preview row with no internal fingerprint or source document content."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_row_reference: str
    date: date
    posted_date: date | None
    raw_description: str
    merchant: str
    amount_cents: CentAmount
    currency: Literal["CAD"]
    direction: Direction
    type: TransactionType
    included_in_spending: bool
    exclusion_reason: str | None
    original_foreign_amount_cents: CentAmount | None
    original_foreign_currency: str | None
    exchange_rate: ExchangeRate | None
    occurrence_index: int
    duplicate_decision: StagedDuplicateDecision
    status: StagedStatus


class ImportWarningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    severity: WarningSeverity
    message: str
    source_row_reference: str | None


class ImportDetailResponse(BaseModel):
    """Privacy-safe structured import lifecycle response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int
    account_id: int
    issuer: str
    source_filename: str
    parser_name: str
    parser_version: str
    statement_start_date: date | None
    statement_end_date: date | None
    currency: Literal["CAD"]
    status: ImportStatus
    validation_status: ValidationStatus
    duplicate_decision: ImportDuplicateDecision
    duplicate_of_import_id: int | None
    transaction_count: int
    purchase_count: int
    credit_count: int
    payment_count: int
    fee_interest_count: int
    unresolved_count: int
    expected_total_cents: CentAmount | None
    parsed_total_cents: CentAmount | None
    reconciliation_delta_cents: CentAmount | None
    purchase_total_cents: CentAmount | None
    credit_total_cents: CentAmount | None
    payment_total_cents: CentAmount | None
    fee_interest_total_cents: CentAmount | None
    staged_transactions: list[ImportCandidateResponse]
    warnings: list[ImportWarningResponse]


class ImportPreviewResponse(ImportDetailResponse):
    suggested_account_id: int | None


class ImportCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acknowledge_needs_review: bool = False


class ImportCommitResponse(BaseModel):
    import_id: int
    status: Literal["committed"]
    created_count: int
    linked_duplicate_count: int
    transaction_ids: list[int]


class ImportCancelResponse(BaseModel):
    import_id: int
    status: Literal["cancelled"]


class ImportErrorResponse(BaseModel):
    detail: str
    code: str
    import_id: int | None = None
    duplicate_of_import_id: int | None = None
    status: ImportStatus | None = None


class ImportNotFoundResponse(BaseModel):
    detail: str
