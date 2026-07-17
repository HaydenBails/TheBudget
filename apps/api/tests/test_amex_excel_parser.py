from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, replace
from decimal import Decimal
from pathlib import Path

import pytest

from app.importing.errors import UnsupportedDocumentError
from app.importing.spreadsheet import ExtractedWorkbook, stage_spreadsheet
from app.parsers import AmexExcelParser

REPOSITORY_ROOT = Path(__file__).parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "fixtures" / "statements" / "amex"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(scope="module")
def workbook(tmp_path_factory: pytest.TempPathFactory) -> ExtractedWorkbook:
    temp_root = tmp_path_factory.mktemp("amex-xlsx")
    with (FIXTURE_ROOT / "amex_excel_matrix.xlsx").open("rb") as stream:
        with stage_spreadsheet(
            stream, filename="amex_excel_matrix.xlsx", content_type=XLSX_MIME, temp_root=temp_root
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


def test_matches_reviewed_canonical_json(workbook: ExtractedWorkbook) -> None:
    parser = AmexExcelParser()
    expected = json.loads(
        (FIXTURE_ROOT / "amex_excel_matrix.expected.json").read_text(encoding="utf-8")
    )
    assert parser.detect(workbook).matched is True
    metadata = parser.extract_metadata(workbook)
    transactions = parser.extract_transactions(workbook)
    reconciliation = parser.reconcile(metadata, transactions)
    md = asdict(metadata)
    md.pop("section_totals_cents", None)
    md["period_start"] = metadata.period_start.isoformat()
    md["period_end"] = metadata.period_end.isoformat()
    result = {
        "metadata": md,
        "transactions": [_canonical(c) for c in transactions],
        "reconciliation": asdict(reconciliation),
    }
    assert result == expected


def test_signs_types_and_masked_account(workbook: ExtractedWorkbook) -> None:
    parser = AmexExcelParser()
    metadata = parser.extract_metadata(workbook)
    assert metadata.account_last4 == "9005"  # last 4 of XXXX-XXXXXX-19005
    by_desc = {c.raw_description: c for c in parser.extract_transactions(workbook)}
    # Charges are positive debits; payments/refunds are negative credits.
    assert by_desc["SYNTHETIC MARKET"].amount_cents == 123456
    assert by_desc["SYNTHETIC MARKET"].direction == "debit"
    assert by_desc["ANNUAL MEMBERSHIP FEE"].txn_type == "fee"
    payment = by_desc["PAYMENT RECEIVED - THANK YOU"]
    assert (payment.txn_type, payment.amount_cents) == ("payment", -150000)
    refund = by_desc["SYNTHETIC RETURN"]
    assert (refund.txn_type, refund.amount_cents) == ("refund", -2500)


def test_foreign_currency_row(workbook: ExtractedWorkbook) -> None:
    cloud = next(
        c for c in AmexExcelParser().extract_transactions(workbook)
        if c.raw_description == "SYNTHETIC CLOUD"
    )
    assert cloud.amount_cents == 1345
    assert cloud.original_currency == "EUR"
    assert cloud.original_amount_cents == 1000
    assert cloud.exchange_rate == Decimal("1.34500000")


def test_repeated_rows_get_distinct_occurrence_indexes(workbook: ExtractedWorkbook) -> None:
    repeated = [
        c for c in AmexExcelParser().extract_transactions(workbook)
        if c.raw_description == "SYNTHETIC CAFE"
    ]
    assert [c.occurrence_index for c in repeated] == [0, 1]


def test_reconciles_net_and_sections(workbook: ExtractedWorkbook) -> None:
    parser = AmexExcelParser()
    metadata = parser.extract_metadata(workbook)
    transactions = parser.extract_transactions(workbook)
    assert parser.reconcile(metadata, transactions).status == "reconciled"
    # A debit/credit swap that nets to zero still fails the section check.
    assert parser.reconcile(
        replace(
            metadata,
            expected_debits_cents=metadata.expected_debits_cents + 100,
            expected_credits_cents=metadata.expected_credits_cents - 100,
        ),
        transactions,
    ).status == "needs_review"


def test_non_amex_workbook_is_rejected() -> None:
    other = ExtractedWorkbook(
        document_id="x", sha256="a" * 64, sanitized_filename="x.xlsx", byte_count=10,
        sheet_count=1, sheets={"Transaction Details": (("Some Other Bank",), ("Date", "Amount"))},
    )
    parser = AmexExcelParser()
    assert parser.detect(other).matched is False
    with pytest.raises(UnsupportedDocumentError):
        parser.extract_transactions(other)


def test_staging_rejects_non_xlsx_and_non_zip(tmp_path: Path) -> None:
    import io

    with pytest.raises(UnsupportedDocumentError, match="\\.xlsx extension"):
        with stage_spreadsheet(
            io.BytesIO(b"x"), filename="statement.pdf", content_type=XLSX_MIME, temp_root=tmp_path
        ):
            pass
    with pytest.raises(UnsupportedDocumentError, match="not an .xlsx"):
        with stage_spreadsheet(
            io.BytesIO(b"not a zip"),
            filename="statement.xlsx",
            content_type=XLSX_MIME,
            temp_root=tmp_path,
        ):
            pass


def test_fixture_is_synthetic_and_privacy_safe() -> None:
    path = FIXTURE_ROOT / "amex_excel_matrix.xlsx"
    # Read the raw shared strings without interpreting the workbook.
    with zipfile.ZipFile(path) as archive:
        blob = "".join(
            archive.read(name).decode("utf-8", "ignore")
            for name in archive.namelist()
            if name.endswith(".xml")
        )
    import re

    assert "SYNTHETIC" in blob
    assert re.search(r"(?<!\d)\d{12,19}(?!\d)", blob) is None
