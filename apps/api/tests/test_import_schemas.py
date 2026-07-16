"""Validation coverage for privacy-safe import persistence contracts."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import ImportBatchCreate, ImportStagedTransactionCreate


def _batch(**changes):
    values = {
        "account_id": 1,
        "issuer": "TD",
        "source_filename": "statement.pdf",
        "file_sha256": "a" * 64,
        "logical_statement_key": "b" * 64,
        "parser_name": "td_pdf",
        "parser_version": "1.0",
        "validation_status": "validated",
    }
    values.update(changes)
    return ImportBatchCreate(**values)


def _staged(**changes):
    values = {
        "account_id": 1,
        "source_row_reference": "page-1:row-2",
        "date": date(2026, 7, 1),
        "raw_description": "COFFEE SHOP",
        "merchant": "Coffee Shop",
        "amount_cents": 425,
        "direction": "debit",
        "type": "purchase",
        "included_in_spending": True,
        "transaction_fingerprint": "c" * 64,
    }
    values.update(changes)
    return ImportStagedTransactionCreate(**values)


@pytest.mark.parametrize(
    "filename",
    [
        "../statement.pdf",
        "C:\\statement.pdf",
        "..",
        "statement\ncopy.pdf",
        "statement\x00copy.pdf",
        "statement\u202ecopy.pdf",
    ],
)
def test_batch_rejects_client_paths(filename: str) -> None:
    with pytest.raises(ValidationError):
        _batch(source_filename=filename)


def test_batch_enforces_dates_reconciliation_and_safe_cents() -> None:
    with pytest.raises(ValidationError):
        _batch(statement_start_date=date(2026, 7, 2), statement_end_date=date(2026, 7, 1))
    with pytest.raises(ValidationError):
        _batch(expected_total_cents=100, parsed_total_cents=125, reconciliation_delta_cents=24)
    with pytest.raises(ValidationError):
        _batch(parsed_total_cents=1 << 53)


def test_staged_foreign_money_is_exact_and_coherent() -> None:
    row = _staged(
        original_foreign_amount_cents=300,
        original_foreign_currency="USD",
        exchange_rate="1.41666667",
    )
    assert row.exchange_rate == Decimal("1.41666667")
    with pytest.raises(ValidationError):
        _staged(exchange_rate=1.25)
    with pytest.raises(ValidationError):
        _staged(original_foreign_amount_cents=300)
