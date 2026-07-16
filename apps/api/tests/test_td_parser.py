from __future__ import annotations

import json
import re
from dataclasses import asdict, replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pdfplumber
import pytest

from app.importing.contracts import ExtractedDocument, TransactionCandidate
from app.importing.document import stage_pdf
from app.importing.errors import ScannedDocumentError, UnsupportedDocumentError
from app.importing.fingerprints import transaction_fingerprint
from app.parsers import TdCreditCardParser

REPOSITORY_ROOT = Path(__file__).parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "fixtures" / "statements" / "td"


@pytest.fixture(scope="module")
def full_document(tmp_path_factory: pytest.TempPathFactory) -> ExtractedDocument:
    temp_root = tmp_path_factory.mktemp("td-stage")
    with (FIXTURE_ROOT / "td_full_matrix.pdf").open("rb") as stream:
        with stage_pdf(
            stream,
            filename="td_full_matrix.pdf",
            content_type="application/pdf",
            temp_root=temp_root,
        ) as document:
            return document


def _canonical_transaction(candidate: TransactionCandidate) -> dict[str, object]:
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


def _canonical_result(parser: TdCreditCardParser, document: ExtractedDocument) -> dict[str, object]:
    metadata = parser.extract_metadata(document)
    transactions = parser.extract_transactions(document)
    reconciliation = parser.reconcile(metadata, transactions)
    metadata_dict = asdict(metadata)
    metadata_dict.pop("section_totals_cents", None)
    metadata_dict["period_start"] = (
        metadata.period_start.isoformat() if metadata.period_start else None
    )
    metadata_dict["period_end"] = (
        metadata.period_end.isoformat() if metadata.period_end else None
    )
    return {
        "metadata": metadata_dict,
        "transactions": [_canonical_transaction(candidate) for candidate in transactions],
        "reconciliation": asdict(reconciliation),
    }


def test_full_synthetic_matrix_matches_reviewed_canonical_json(
    full_document: ExtractedDocument,
) -> None:
    parser = TdCreditCardParser()
    expected = json.loads(
        (FIXTURE_ROOT / "td_full_matrix.expected.json").read_text(encoding="utf-8")
    )
    assert parser.detect(full_document).matched is True
    assert parser.detect(full_document).confidence == Decimal("1")
    assert _canonical_result(parser, full_document) == expected


def test_first_middle_last_pages_and_non_transaction_sections_are_handled(
    full_document: ExtractedDocument,
) -> None:
    transactions = tuple(TdCreditCardParser().extract_transactions(full_document))
    assert len(transactions) == 8
    assert [candidate.source_index for candidate in transactions] == list(range(8))
    assert transactions[0].transaction_date == date(2026, 6, 2)
    assert transactions[2].transaction_date == date(2026, 6, 6)
    assert transactions[-1].transaction_date == date(2026, 6, 14)
    descriptions = {candidate.raw_description for candidate in transactions}
    assert not any(
        marker in description
        for description in descriptions
        for marker in ("PAYMENT SLIP", "REWARD BALANCE", "LEGAL INFORMATION", "PAGE 2")
    )


def test_payment_refund_fee_interest_and_foreign_continuation_are_exact(
    full_document: ExtractedDocument,
) -> None:
    transactions = tuple(TdCreditCardParser().extract_transactions(full_document))
    by_description = {candidate.raw_description: candidate for candidate in transactions}
    payment = by_description["PAYMENT - THANK YOU"]
    assert (payment.txn_type, payment.amount_cents) == (
        "payment",
        -150000,
    )
    refund = by_description["SYNTHETIC RETURN"]
    assert (refund.txn_type, refund.amount_cents) == (
        "refund",
        -2500,
    )
    assert by_description["ANNUAL FEE"].txn_type == "fee"
    assert by_description["INTEREST CHARGE"].txn_type == "interest"
    foreign = by_description["SYNTHETIC CLOUD MONTHLY SERVICE"]
    assert (foreign.amount_cents, foreign.original_currency, foreign.original_amount_cents) == (
        1345,
        "USD",
        1000,
    )
    assert foreign.exchange_rate == Decimal("1.34500000")


def test_occurrence_indexes_preserve_repeated_rows_and_feed_keyed_hmac_boundary(
    full_document: ExtractedDocument,
) -> None:
    repeated = [
        candidate
        for candidate in TdCreditCardParser().extract_transactions(full_document)
        if candidate.raw_description == "SYNTHETIC CAFE"
    ]
    assert [candidate.occurrence_index for candidate in repeated] == [0, 1]
    key = b"synthetic-local-fingerprint-key-material-32"
    fingerprints = [
        transaction_fingerprint(
            key=key,
            account_id=1,
            transaction_date=candidate.transaction_date,
            posted_date=candidate.posted_date,
            raw_description=candidate.raw_description,
            amount_cents=candidate.amount_cents,
            occurrence_index=candidate.occurrence_index,
        )
        for candidate in repeated
    ]
    assert fingerprints[0] != fingerprints[1]


def test_reconciliation_checks_net_and_sections_with_one_cent_tolerance(
    full_document: ExtractedDocument,
) -> None:
    parser = TdCreditCardParser()
    metadata = parser.extract_metadata(full_document)
    transactions = parser.extract_transactions(full_document)
    assert parser.reconcile(metadata, transactions).status == "reconciled"
    assert parser.reconcile(
        replace(metadata, expected_activity_cents=metadata.expected_activity_cents + 1),
        transactions,
    ).status == "reconciled"
    assert parser.reconcile(
        replace(metadata, expected_activity_cents=metadata.expected_activity_cents + 2),
        transactions,
    ).status == "needs_review"
    cancelling_transactions = list(transactions)
    purchase_index = next(
        index
        for index, candidate in enumerate(cancelling_transactions)
        if candidate.txn_type == "purchase"
    )
    fee_index = next(
        index
        for index, candidate in enumerate(cancelling_transactions)
        if candidate.txn_type == "fee"
    )
    cancelling_transactions[purchase_index] = replace(
        cancelling_transactions[purchase_index],
        amount_cents=cancelling_transactions[purchase_index].amount_cents + 100,
    )
    cancelling_transactions[fee_index] = replace(
        cancelling_transactions[fee_index],
        amount_cents=cancelling_transactions[fee_index].amount_cents - 100,
    )
    assert (
        parser.reconcile(metadata, cancelling_transactions).status == "needs_review"
    )
    assert parser.reconcile(
        replace(
            metadata,
            expected_debits_cents=metadata.expected_debits_cents + 100,
            expected_credits_cents=metadata.expected_credits_cents - 100,
        ),
        transactions,
    ).status == "needs_review"


def test_unsupported_and_scanned_layouts_fail_closed(tmp_path: Path) -> None:
    parser = TdCreditCardParser()
    with (FIXTURE_ROOT / "td_unsupported_layout.pdf").open("rb") as stream:
        with stage_pdf(
            stream,
            filename="td_unsupported_layout.pdf",
            content_type="application/pdf",
            temp_root=tmp_path,
        ) as document:
            detection = parser.detect(document)
            assert detection.matched is False
            assert detection.reason_code == "td_unsupported_layout"
            with pytest.raises(UnsupportedDocumentError, match="layout is not supported"):
                parser.extract_transactions(document)

    with (FIXTURE_ROOT / "td_scanned_placeholder.pdf").open("rb") as stream:
        with pytest.raises(ScannedDocumentError, match="text-based PDF"):
            with stage_pdf(
                stream,
                filename="td_scanned_placeholder.pdf",
                content_type="application/pdf",
                temp_root=tmp_path,
            ):
                pass
    blank = ExtractedDocument("blank", "a" * 64, "blank.pdf", 1, 1, ("",))
    with pytest.raises(ScannedDocumentError, match="extractable text"):
        parser.extract_transactions(blank)


def test_incomplete_foreign_continuation_and_out_of_period_rows_fail_closed() -> None:
    parser = TdCreditCardParser()
    prefix = (
        "TD CANADA TRUST\nCREDIT CARD STATEMENT\n"
        "STATEMENT PERIOD JUNE 1, 2026 - JUNE 30, 2026\n"
        "TRANSACTION DATE POSTING DATE ACTIVITY DESCRIPTION AMOUNT\n"
    )
    incomplete = ExtractedDocument(
        "incomplete",
        "b" * 64,
        "statement.pdf",
        1,
        1,
        (prefix + "JUN 08 JUN 09 SYNTHETIC CLOUD $13.45\nFOREIGN CURRENCY USD $10.00",),
    )
    with pytest.raises(UnsupportedDocumentError, match="continuation is incomplete"):
        parser.extract_transactions(incomplete)

    outside = ExtractedDocument(
        "outside",
        "c" * 64,
        "statement.pdf",
        1,
        1,
        (prefix + "JUL 08 JUL 09 SYNTHETIC CLOUD $13.45",),
    )
    with pytest.raises(UnsupportedDocumentError, match="outside the statement period"):
        parser.extract_transactions(outside)


def test_continuations_reclassify_rows_and_reject_ambiguous_amounts() -> None:
    parser = TdCreditCardParser()
    prefix = (
        "TD CANADA TRUST\nCREDIT CARD STATEMENT\n"
        "STATEMENT PERIOD JUNE 1, 2026 - JUNE 30, 2026\n"
        "TRANSACTION DATE POSTING DATE ACTIVITY DESCRIPTION AMOUNT\n"
    )
    continued_fee = ExtractedDocument(
        "continued-fee",
        "f" * 64,
        "statement.pdf",
        1,
        1,
        (
            prefix
            + "JUN 08 JUN 09 SYNTHETIC SERVICE $13.45\n"
            "DESCRIPTION CONTINUED: SERVICE FEE",
        ),
    )
    candidate = tuple(parser.extract_transactions(continued_fee))[0]
    assert candidate.raw_description == "SYNTHETIC SERVICE SERVICE FEE"
    assert candidate.txn_type == "fee"

    malformed_amount = ExtractedDocument(
        "malformed-amount",
        "1" * 64,
        "statement.pdf",
        1,
        1,
        (
            prefix
            + "JUN 07 JUN 08 SYNTHETIC VALID $10.00\n"
            "JUN 08 JUN 09 SYNTHETIC SERVICE $1,2.34",
        ),
    )
    with pytest.raises(UnsupportedDocumentError, match="ambiguous transaction row"):
        parser.extract_transactions(malformed_amount)


@pytest.mark.parametrize(
    "continuations",
    [
        (
            "FOREIGN CURRENCY USD $10.00\n"
            "FOREIGN CURRENCY EUR $9.00\n"
            "EXCHANGE RATE 1.345"
        ),
        (
            "FOREIGN CURRENCY USD $10.00\n"
            "EXCHANGE RATE 1.345\n"
            "EXCHANGE RATE 1.346"
        ),
        (
            "FOREIGN AMOUNT USD $10.00 AT 1.345\n"
            "FOREIGN AMOUNT USD $10.00 AT 1.345"
        ),
    ],
)
def test_duplicate_or_conflicting_foreign_continuations_fail_closed(
    continuations: str,
) -> None:
    document = ExtractedDocument(
        "duplicate-foreign",
        "2" * 64,
        "statement.pdf",
        1,
        1,
        (
            "TD CANADA TRUST\nCREDIT CARD STATEMENT\n"
            "STATEMENT PERIOD JUNE 1, 2026 - JUNE 30, 2026\n"
            "TRANSACTION DATE POSTING DATE ACTIVITY DESCRIPTION AMOUNT\n"
            "JUN 08 JUN 09 SYNTHETIC CLOUD $13.45\n"
            f"{continuations}",
        ),
    )
    with pytest.raises(
        UnsupportedDocumentError,
        match="continuation is duplicated or conflicting",
    ):
        TdCreditCardParser().extract_transactions(document)


def test_cross_year_statement_dates_are_inferred_only_inside_period() -> None:
    document = ExtractedDocument(
        "cross-year",
        "d" * 64,
        "statement.pdf",
        1,
        1,
        (
            "TD CANADA TRUST\nCREDIT CARD STATEMENT\n"
            "STATEMENT PERIOD DECEMBER 15, 2025 - JANUARY 14, 2026\n"
            "TRANSACTION DATE POSTING DATE ACTIVITY DESCRIPTION AMOUNT\n"
            "DEC 30 JAN 02 SYNTHETIC YEAR END $10.00",
        ),
    )
    candidate = tuple(TdCreditCardParser().extract_transactions(document))[0]
    assert candidate.transaction_date == date(2025, 12, 30)
    assert candidate.posted_date == date(2026, 1, 2)


def test_leap_day_is_inferred_from_the_only_valid_period_year() -> None:
    document = ExtractedDocument(
        "leap-year",
        "e" * 64,
        "statement.pdf",
        1,
        1,
        (
            "TD CANADA TRUST\nCREDIT CARD STATEMENT\n"
            "STATEMENT PERIOD DECEMBER 15, 2023 - MARCH 14, 2024\n"
            "TRANSACTION DATE POSTING DATE ACTIVITY DESCRIPTION AMOUNT\n"
            "FEB 29 MAR 01 SYNTHETIC LEAP DAY $10.00",
        ),
    )
    candidate = tuple(TdCreditCardParser().extract_transactions(document))[0]
    assert candidate.transaction_date == date(2024, 2, 29)
    assert candidate.posted_date == date(2024, 3, 1)


def test_fixture_manifest_and_corpus_are_synthetic_and_privacy_safe() -> None:
    manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["policy"] == "synthetic-only"
    assert all(fixture["synthetic"] is True for fixture in manifest["fixtures"])
    assert {fixture["file"] for fixture in manifest["fixtures"]} == {
        "td_full_matrix.pdf",
        "td_unsupported_layout.pdf",
        "td_scanned_placeholder.pdf",
    }

    extracted_text: list[str] = []
    for pdf_path in FIXTURE_ROOT.glob("*.pdf"):
        with pdfplumber.open(pdf_path) as pdf:
            extracted_text.extend(page.extract_text() or "" for page in pdf.pages)
    corpus = "\n".join(extracted_text)
    assert re.search(r"(?<!\d)\d{12,19}(?!\d)", corpus) is None
    assert not any(
        forbidden in corpus.upper()
        for forbidden in (" BARCODE", " STREET", " AVENUE", " ROAD", " POSTAL CODE")
    )
    assert "**** **** **** 4821" in corpus
    assert "SYNTHETIC" in corpus
