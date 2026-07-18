from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.importing.csv_statement import ExtractedCsv, stage_csv
from app.importing.errors import UnsupportedDocumentError
from app.parsers import TdCsvParser

REPOSITORY_ROOT = Path(__file__).parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "fixtures" / "statements" / "td"
CSV_MIME = "text/csv"


@pytest.fixture(scope="module")
def statement(tmp_path_factory: pytest.TempPathFactory) -> ExtractedCsv:
    temp_root = tmp_path_factory.mktemp("td-csv")
    with (FIXTURE_ROOT / "td_account_activity.csv").open("rb") as stream:
        with stage_csv(
            stream, filename="td_account_activity.csv", content_type=CSV_MIME, temp_root=temp_root
        ) as extracted:
            return extracted


def _canonical(candidate) -> dict[str, object]:
    return {
        "source_index": candidate.source_index,
        "occurrence_index": candidate.occurrence_index,
        "transaction_date": candidate.transaction_date.isoformat(),
        "posted_date": candidate.posted_date.isoformat() if candidate.posted_date else None,
        "raw_description": candidate.raw_description,
        "amount_cents": candidate.amount_cents,
        "txn_type": candidate.txn_type,
        "direction": candidate.direction,
        "original_currency": candidate.original_currency,
        "original_amount_cents": candidate.original_amount_cents,
        "exchange_rate": str(candidate.exchange_rate) if candidate.exchange_rate else None,
    }


def test_matches_reviewed_canonical_json(statement: ExtractedCsv) -> None:
    parser = TdCsvParser()
    expected = json.loads(
        (FIXTURE_ROOT / "td_account_activity.expected.json").read_text(encoding="utf-8")
    )
    assert parser.detect(statement).matched is True
    metadata = parser.extract_metadata(statement)
    transactions = parser.extract_transactions(statement)
    reconciliation = parser.reconcile(metadata, transactions)

    assert metadata.issuer == expected["metadata"]["issuer"]
    assert metadata.period_start.isoformat() == expected["metadata"]["period_start"]
    assert metadata.period_end.isoformat() == expected["metadata"]["period_end"]
    assert metadata.expected_activity_cents == expected["metadata"]["expected_activity_cents"]
    assert [_canonical(t) for t in transactions] == expected["transactions"]
    assert reconciliation.status == "reconciled"
    assert reconciliation.delta_cents == 0


def _csv(rows: tuple[tuple[str, ...], ...]) -> ExtractedCsv:
    return ExtractedCsv("d", "sha", "stmt.csv", 100, len(rows), rows)


def test_charge_is_debit_and_credit_is_money_in() -> None:
    doc = _csv(
        (
            ("07/01/2026", "PAYROLL DEPOSIT PAY", "", "1000.00", "2000.00"),
            ("07/02/2026", "GROCERY STORE", "50.00", "", "1950.00"),
        )
    )
    parser = TdCsvParser()
    txns = parser.extract_transactions(doc)
    by_desc = {t.raw_description: t for t in txns}
    assert by_desc["PAYROLL DEPOSIT PAY"].amount_cents == -100000
    assert by_desc["PAYROLL DEPOSIT PAY"].direction == "credit"
    assert by_desc["PAYROLL DEPOSIT PAY"].txn_type == "income"
    assert by_desc["GROCERY STORE"].amount_cents == 5000
    assert by_desc["GROCERY STORE"].direction == "debit"
    assert by_desc["GROCERY STORE"].txn_type == "purchase"


def test_inconsistent_running_balance_declines_reconciliation() -> None:
    doc = _csv(
        (
            ("07/01/2026", "PAYROLL DEPOSIT PAY", "", "1000.00", "2000.00"),
            ("07/02/2026", "GROCERY STORE", "50.00", "", "9999.99"),  # broken chain
        )
    )
    parser = TdCsvParser()
    metadata = parser.extract_metadata(doc)
    reconciliation = parser.reconcile(metadata, parser.extract_transactions(doc))
    assert metadata.expected_activity_cents is None
    assert reconciliation.status == "needs_review"


def test_detects_and_skips_a_header_row() -> None:
    doc = _csv(
        (
            ("Date", "Description", "Charge", "Credit", "Balance"),
            ("07/01/2026", "PAYROLL DEPOSIT PAY", "", "1000.00", "2000.00"),
            ("07/02/2026", "GROCERY STORE", "50.00", "", "1950.00"),
        )
    )
    parser = TdCsvParser()
    assert parser.detect(doc).matched is True
    assert len(parser.extract_transactions(doc)) == 2


def test_non_td_shape_is_not_matched() -> None:
    doc = _csv(
        (
            ("some", "unrelated", "csv", "file"),
            ("with", "no", "date", "column"),
        )
    )
    assert TdCsvParser().detect(doc).matched is False


def test_boundary_rejects_non_csv_extension(tmp_path) -> None:
    payload = tmp_path / "not.txtish"
    payload.write_bytes(b"07/01/2026,X,1.00,,1.00\n")
    with payload.open("rb") as stream:
        with pytest.raises(UnsupportedDocumentError):
            with stage_csv(stream, filename="statement.xlsx", content_type="text/csv"):
                pass


def test_binary_upload_is_rejected(tmp_path) -> None:
    payload = tmp_path / "binary.csv"
    payload.write_bytes(b"\x00\x01\x02binary")
    with payload.open("rb") as stream:
        with pytest.raises(UnsupportedDocumentError):
            with stage_csv(stream, filename="statement.csv", content_type="text/csv"):
                pass
