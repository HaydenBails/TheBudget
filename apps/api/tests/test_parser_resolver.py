from __future__ import annotations

import pytest

from app.importing.contracts import ExtractedDocument
from app.importing.errors import ScannedDocumentError, UnsupportedDocumentError
from app.parsers import (
    AmexCreditCardParser,
    TdCreditCardParser,
    available_parsers,
    resolve_parser,
)

_TD_DOCUMENT = ExtractedDocument(
    "td",
    "a" * 64,
    "td.pdf",
    1,
    1,
    (
        "TD CANADA TRUST\nCREDIT CARD STATEMENT\n"
        "STATEMENT PERIOD JUNE 1, 2026 - JUNE 30, 2026\n"
        "TRANSACTION DATE POSTING DATE ACTIVITY DESCRIPTION AMOUNT\n"
        "JUN 02 JUN 03 SYNTHETIC MARKET $10.00",
    ),
)
_AMEX_DOCUMENT = ExtractedDocument(
    "amex",
    "b" * 64,
    "amex.pdf",
    1,
    1,
    (
        "AMERICAN EXPRESS\nCOBALT CARD\n"
        "STATEMENT PERIOD JUNE 1, 2026 TO JUNE 30, 2026\n"
        "NEW CHARGES\n"
        "JUN 02 SYNTHETIC MARKET $10.00",
    ),
)


def test_available_parsers_include_td_and_amex() -> None:
    names = {parser.parser_name for parser in available_parsers()}
    assert {"td_credit_card", "amex_credit_card"} <= names


def test_resolver_selects_td_for_a_td_document() -> None:
    assert isinstance(resolve_parser(_TD_DOCUMENT), TdCreditCardParser)


def test_resolver_selects_amex_for_an_amex_document() -> None:
    assert isinstance(resolve_parser(_AMEX_DOCUMENT), AmexCreditCardParser)


def test_resolver_rejects_an_unknown_issuer() -> None:
    unknown = ExtractedDocument(
        "unknown",
        "c" * 64,
        "unknown.pdf",
        1,
        1,
        ("SOME OTHER BANK\nMONTHLY STATEMENT\nACTIVITY LIST\nJUN 02 SOMETHING $10.00",),
    )
    with pytest.raises(UnsupportedDocumentError, match="issuer or layout is not supported"):
        resolve_parser(unknown)


def test_resolver_reports_a_scanned_document_when_no_text_is_present() -> None:
    blank = ExtractedDocument("blank", "d" * 64, "blank.pdf", 1, 1, ("",))
    with pytest.raises(ScannedDocumentError, match="text-based PDF"):
        resolve_parser(blank)
