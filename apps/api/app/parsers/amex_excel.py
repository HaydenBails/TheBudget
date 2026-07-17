"""Parser for American Express "Transaction Details" .xlsx exports.

Amex lets a cardmember download activity as an Excel workbook with a
``Transaction Details`` sheet (one row per transaction) and a
``Transaction Summary`` sheet (period totals). Charges are positive amounts and
payments/credits are negative — already the canonical signed convention — so
this parser maps rows straight onto ``TransactionCandidate`` objects and
reconciles them against the summary totals.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.importing.contracts import (
    ParserDetection,
    ReconciliationResult,
    StatementMetadata,
    TransactionCandidate,
    TransactionType,
)
from app.importing.errors import UnsupportedDocumentError
from app.importing.reconciliation import parse_exchange_rate, reconcile_totals
from app.importing.spreadsheet import ExtractedWorkbook
from app.parsers.base import StatementParser

_DETAILS_SHEET = "Transaction Details"
_SUMMARY_SHEET = "Transaction Summary"
_ISSUER_MARKER = "AMERICAN EXPRESS"
_MASKED_ACCOUNT = re.compile(r"[X*][\dX*\-\s]*?(?P<last4>\d{4})(?!\d)")
_FOREIGN = re.compile(r"^(?P<amount>[\d.,]+)\s+(?P<currency>[A-Z]{3})$")
# Column order in the Amex details sheet.
_COL_DATE = 0
_COL_POSTED = 1
_COL_DESC = 2
_COL_AMOUNT = 3
_COL_FOREIGN = 4
_COL_RATE = 6


@dataclass(frozen=True, slots=True, repr=False)
class _AmexExcelMetadata(StatementMetadata):
    section_totals_cents: tuple[tuple[str, int], ...] = ()


def _parse_amount_to_cents(text: str) -> int:
    cleaned = text.replace(",", "").strip()
    try:
        return int((Decimal(cleaned) * 100).to_integral_value())
    except (InvalidOperation, ValueError):
        raise UnsupportedDocumentError(
            "Amex workbook contains an unreadable monetary amount"
        ) from None


def _parse_foreign_amount(text: str) -> int:
    # European style: comma is the decimal separator, dots group thousands.
    normalized = text.replace(".", "").replace(",", ".")
    try:
        return int((Decimal(normalized) * 100).to_integral_value())
    except (InvalidOperation, ValueError):
        raise UnsupportedDocumentError(
            "Amex workbook contains an unreadable foreign amount"
        ) from None


def _parse_date(text: str) -> date:
    for pattern in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text.strip(), pattern).date()
        except ValueError:
            continue
    raise UnsupportedDocumentError("Amex workbook contains an unreadable date")


def _classify(description: str, amount_cents: int) -> TransactionType:
    normalized = " ".join(description.upper().split())
    if "PAYMENT" in normalized and ("THANK YOU" in normalized or "RECEIVED" in normalized):
        return "payment"
    if "INTEREST" in normalized:
        return "interest"
    if "FEE" in normalized or "ANNUAL MEMBERSHIP" in normalized:
        return "fee"
    if "CASH ADVANCE" in normalized:
        return "cash_advance"
    if amount_cents < 0:
        return "refund"
    return "purchase"


class AmexExcelParser(StatementParser):
    """Parse the Amex ``Transaction Details`` .xlsx workbook layout."""

    parser_name = "amex_excel"
    parser_version = "1.0.0"

    def detect(self, workbook: ExtractedWorkbook) -> ParserDetection:
        details = workbook.sheet(_DETAILS_SHEET)
        if details is None:
            return ParserDetection(False, Decimal("0"), "no_transaction_details_sheet")
        joined = "\n".join(cell for row in details[:8] for cell in row).upper()
        if _ISSUER_MARKER not in joined:
            return ParserDetection(False, Decimal("0.2"), "issuer_not_amex")
        if self._header_row_index(details) is None:
            return ParserDetection(False, Decimal("0.3"), "amex_excel_missing_header")
        return ParserDetection(True, Decimal("1"), "amex_excel_supported_layout")

    def extract_metadata(self, workbook: ExtractedWorkbook) -> StatementMetadata:
        self._require_supported(workbook)
        details = workbook.sheet(_DETAILS_SHEET)
        assert details is not None
        transactions = self.extract_transactions(workbook)
        dates = [candidate.transaction_date for candidate in transactions]
        summaries = self._extract_summary_amounts(workbook)
        expected_debits = summaries.get("charges")
        expected_credits = summaries.get("credits")
        expected_activity = (
            expected_debits + expected_credits
            if expected_debits is not None and expected_credits is not None
            else None
        )
        return _AmexExcelMetadata(
            issuer="AMEX",
            account_last4=self._masked_last4(details),
            period_start=min(dates) if dates else None,
            period_end=max(dates) if dates else None,
            expected_activity_cents=expected_activity,
            expected_debits_cents=expected_debits,
            expected_credits_cents=expected_credits,
            section_totals_cents=tuple(sorted(summaries.items())),
        )

    def extract_transactions(
        self, workbook: ExtractedWorkbook
    ) -> Sequence[TransactionCandidate]:
        self._require_supported(workbook)
        details = workbook.sheet(_DETAILS_SHEET)
        assert details is not None
        header_index = self._header_row_index(details)
        assert header_index is not None

        transactions: list[TransactionCandidate] = []
        occurrences: Counter[tuple[object, ...]] = Counter()
        for row in details[header_index + 1 :]:
            if len(row) <= _COL_AMOUNT:
                continue
            raw_date = row[_COL_DATE].strip()
            raw_amount = row[_COL_AMOUNT].strip()
            description = " ".join(row[_COL_DESC].split())
            if not raw_date or not raw_amount or not description:
                continue
            amount_cents = _parse_amount_to_cents(raw_amount)
            if amount_cents == 0:
                continue
            txn_date = _parse_date(raw_date)
            posted_raw = row[_COL_POSTED].strip() if len(row) > _COL_POSTED else ""
            posted_date = _parse_date(posted_raw) if posted_raw else None
            txn_type = _classify(description, amount_cents)
            direction = "debit" if amount_cents > 0 else "credit"
            currency, foreign_cents, rate = self._parse_foreign(row, direction)
            key = (
                txn_date,
                " ".join(description.casefold().split()),
                amount_cents,
                txn_type,
            )
            occurrence_index = occurrences[key]
            occurrences[key] += 1
            transactions.append(
                TransactionCandidate(
                    source_index=len(transactions),
                    occurrence_index=occurrence_index,
                    transaction_date=txn_date,
                    posted_date=posted_date,
                    raw_description=description,
                    amount_cents=amount_cents,
                    txn_type=txn_type,
                    direction=direction,
                    original_currency=currency,
                    original_amount_cents=foreign_cents,
                    exchange_rate=rate,
                )
            )
        if not transactions:
            raise UnsupportedDocumentError("Amex workbook has no recognized transaction rows")
        return tuple(transactions)

    def reconcile(
        self,
        metadata: StatementMetadata,
        transactions: Sequence[TransactionCandidate],
    ) -> ReconciliationResult:
        parsed_debits = sum(c.amount_cents for c in transactions if c.amount_cents > 0)
        parsed_credits = sum(c.amount_cents for c in transactions if c.amount_cents < 0)
        parsed_activity = parsed_debits + parsed_credits
        if metadata.expected_activity_cents is None:
            return ReconciliationResult(
                status="needs_review",
                expected_cents=0,
                parsed_cents=parsed_activity,
                delta_cents=parsed_activity,
                tolerance_cents=1,
                transaction_count=len(transactions),
            )
        result = reconcile_totals(metadata.expected_activity_cents, transactions)
        section_deltas = [result.delta_cents]
        if metadata.expected_debits_cents is not None:
            section_deltas.append(parsed_debits - metadata.expected_debits_cents)
        if metadata.expected_credits_cents is not None:
            section_deltas.append(parsed_credits - metadata.expected_credits_cents)
        if any(abs(delta) > result.tolerance_cents for delta in section_deltas):
            return ReconciliationResult(
                status="needs_review",
                expected_cents=result.expected_cents,
                parsed_cents=result.parsed_cents,
                delta_cents=result.delta_cents,
                tolerance_cents=result.tolerance_cents,
                transaction_count=result.transaction_count,
            )
        return result

    # -- helpers ------------------------------------------------------------
    def _require_supported(self, workbook: ExtractedWorkbook) -> None:
        if not self.detect(workbook).matched:
            raise UnsupportedDocumentError("Amex workbook layout is not supported")

    @staticmethod
    def _header_row_index(details: tuple[tuple[str, ...], ...]) -> int | None:
        for index, row in enumerate(details[:20]):
            cells = {cell.strip().casefold() for cell in row}
            if "date" in cells and "amount" in cells and "description" in cells:
                return index
        return None

    @staticmethod
    def _masked_last4(details: tuple[tuple[str, ...], ...]) -> str | None:
        for row in details[:10]:
            for cell in row:
                match = _MASKED_ACCOUNT.search(cell)
                if match is not None:
                    return match.group("last4")
        return None

    @staticmethod
    def _parse_foreign(
        row: tuple[str, ...], direction: str
    ) -> tuple[str | None, int | None, Decimal | None]:
        if len(row) <= _COL_RATE:
            return None, None, None
        foreign_text = row[_COL_FOREIGN].strip()
        rate_text = row[_COL_RATE].strip()
        match = _FOREIGN.match(foreign_text)
        if match is None or not rate_text:
            return None, None, None
        magnitude = _parse_foreign_amount(match.group("amount"))
        signed = magnitude if direction == "debit" else -magnitude
        return match.group("currency"), signed, parse_exchange_rate(rate_text)

    def _extract_summary_amounts(self, workbook: ExtractedWorkbook) -> dict[str, int]:
        summary = workbook.sheet(_SUMMARY_SHEET)
        if summary is None:
            return {}
        amounts: dict[str, int] = {}
        for row in summary:
            label = row[0].strip().casefold() if row else ""
            value = next((cell for cell in row[1:] if cell.strip()), "")
            if not value:
                continue
            if label.startswith("charges"):
                amounts["charges"] = _parse_amount_to_cents(value)
            elif label.startswith("payments"):
                amounts["credits"] = _parse_amount_to_cents(value)
        return amounts
