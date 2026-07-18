"""Parser for TD "account activity" .csv exports (chequing/savings).

TD lets you download account activity as a headerless five-column CSV:

    MM/DD/YYYY, description, charge amount, credit amount, running balance

A charge is money out (a debit) and a credit is money in. The canonical signed
convention is debit-positive / credit-negative, so a charge maps to a positive
amount and a credit to a negative one. The running-balance column is used to
reconcile: each row must move the balance by exactly ``credit - charge``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.importing.contracts import (
    ParserDetection,
    ReconciliationResult,
    StatementMetadata,
    TransactionCandidate,
    TransactionType,
)
from app.importing.csv_statement import ExtractedCsv
from app.importing.errors import UnsupportedDocumentError
from app.importing.reconciliation import reconcile_totals
from app.parsers.base import StatementParser

_COL_DATE = 0
_COL_DESC = 1
_COL_CHARGE = 2
_COL_CREDIT = 3
_COL_BALANCE = 4
_MIN_COLS = 5


def _parse_amount_to_cents(text: str) -> int | None:
    cleaned = text.replace(",", "").replace("$", "").strip()
    if not cleaned:
        return None
    try:
        return int((Decimal(cleaned) * 100).to_integral_value())
    except (InvalidOperation, ValueError):
        return None


def _parse_date(text: str) -> date | None:
    for pattern in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text.strip(), pattern).date()
        except ValueError:
            continue
    return None


def _looks_like_row(row: tuple[str, ...]) -> bool:
    if len(row) < _MIN_COLS:
        return False
    if _parse_date(row[_COL_DATE]) is None:
        return False
    charge = _parse_amount_to_cents(row[_COL_CHARGE])
    credit = _parse_amount_to_cents(row[_COL_CREDIT])
    # Exactly one of charge/credit must carry the amount; the balance must parse.
    if (charge is None) == (credit is None):
        return False
    if _parse_amount_to_cents(row[_COL_BALANCE]) is None:
        return False
    return bool(row[_COL_DESC].strip())


def _classify(description: str, direction: str) -> TransactionType:
    normalized = " ".join(description.upper().split())

    def has(*needles: str) -> bool:
        return any(needle in normalized for needle in needles)

    if has("INTEREST"):
        return "interest"
    if has("SERVICE CHARGE", "SERVICE FEE", "MONTHLY PLAN FEE", "OVERDRAFT", "NSF", "FEE"):
        return "fee"
    if direction == "credit":
        if has("PAYROLL", "DIRECT DEP", "DIR DEP", "PAY ", "PAYDEP", "DEPOSIT PAYROLL"):
            return "income"
        return "transfer"
    if has("TFR", "TRANSFER", "XFER", "E-TFR", "E TFR", "ETRANSFER", "E-TRANSFER",
           "WITHDRAW", "ATM", "SEND E"):
        return "transfer"
    if has("BILL PAYMENT", "BILL PMT", "PMT ", "PREAUTHORIZED"):
        return "payment"
    return "purchase"


class TdCsvParser(StatementParser):
    """Parse the headerless five-column TD account-activity CSV layout."""

    parser_name = "td_csv"
    parser_version = "1.0.0"

    def detect(self, document: ExtractedCsv) -> ParserDetection:
        rows = document.rows
        if not rows:
            return ParserDetection(False, Decimal("0"), "empty_csv")
        # Skip an optional header row (non-date first cell).
        data = [row for row in rows if _parse_date(row[_COL_DATE] if row else "") is not None]
        if not data:
            return ParserDetection(False, Decimal("0.1"), "td_csv_no_dated_rows")
        matches = sum(1 for row in data if _looks_like_row(row))
        ratio = Decimal(matches) / Decimal(len(data))
        if matches == 0:
            return ParserDetection(False, Decimal("0.2"), "td_csv_shape_unrecognized")
        if ratio < Decimal("0.6"):
            return ParserDetection(False, ratio, "td_csv_low_row_match")
        return ParserDetection(True, min(ratio, Decimal("1")), "td_csv_supported_layout")

    def extract_metadata(self, document: ExtractedCsv) -> StatementMetadata:
        self._require_supported(document)
        candidates, balances = self._extract(document)
        dates = [candidate.transaction_date for candidate in candidates]
        expected_activity = self._expected_activity(candidates, balances)
        return StatementMetadata(
            issuer="TD",
            account_last4=None,
            period_start=min(dates) if dates else None,
            period_end=max(dates) if dates else None,
            expected_activity_cents=expected_activity,
        )

    def extract_transactions(
        self, document: ExtractedCsv
    ) -> Sequence[TransactionCandidate]:
        self._require_supported(document)
        candidates, _ = self._extract(document)
        if not candidates:
            raise UnsupportedDocumentError("TD CSV has no recognized transaction rows")
        return candidates

    def reconcile(
        self,
        metadata: StatementMetadata,
        transactions: Sequence[TransactionCandidate],
    ) -> ReconciliationResult:
        parsed = sum(candidate.amount_cents for candidate in transactions)
        if metadata.expected_activity_cents is None:
            return ReconciliationResult(
                status="needs_review",
                expected_cents=0,
                parsed_cents=parsed,
                delta_cents=parsed,
                tolerance_cents=1,
                transaction_count=len(transactions),
            )
        return reconcile_totals(metadata.expected_activity_cents, transactions)

    # -- helpers ------------------------------------------------------------
    def _require_supported(self, document: ExtractedCsv) -> None:
        if not self.detect(document).matched:
            raise UnsupportedDocumentError("TD CSV layout is not supported")

    def _extract(
        self, document: ExtractedCsv
    ) -> tuple[tuple[TransactionCandidate, ...], tuple[int, ...]]:
        candidates: list[TransactionCandidate] = []
        balances: list[int] = []
        occurrences: Counter[tuple[object, ...]] = Counter()
        for row in document.rows:
            if not _looks_like_row(row):
                continue
            txn_date = _parse_date(row[_COL_DATE])
            assert txn_date is not None
            charge = _parse_amount_to_cents(row[_COL_CHARGE])
            credit = _parse_amount_to_cents(row[_COL_CREDIT])
            balance = _parse_amount_to_cents(row[_COL_BALANCE])
            assert balance is not None
            # Charge -> money out (debit, positive); credit -> money in (negative).
            amount_cents = charge if charge is not None else -(credit or 0)
            if amount_cents == 0:
                continue
            description = " ".join(row[_COL_DESC].split())
            direction = "debit" if amount_cents > 0 else "credit"
            txn_type = _classify(description, direction)
            key = (txn_date, description.casefold(), amount_cents, txn_type)
            occurrence_index = occurrences[key]
            occurrences[key] += 1
            candidates.append(
                TransactionCandidate(
                    source_index=len(candidates),
                    occurrence_index=occurrence_index,
                    transaction_date=txn_date,
                    posted_date=None,
                    raw_description=description,
                    amount_cents=amount_cents,
                    txn_type=txn_type,
                    direction=direction,
                )
            )
            balances.append(balance)
        return tuple(candidates), tuple(balances)

    @staticmethod
    def _expected_activity(
        candidates: Sequence[TransactionCandidate],
        balances: Sequence[int],
    ) -> int | None:
        """Net activity implied by the running-balance column, in canonical cents.

        Each row moves the account balance by ``credit - charge`` = ``-amount``.
        The opening balance is the first row's balance minus its own effect, so
        the statement's net activity in canonical signed cents is
        ``-(last_balance - opening_balance)``. If the per-row balance chain is not
        internally consistent, reconciliation is declined (returns ``None``).
        """

        if len(candidates) < 1 or len(balances) != len(candidates):
            return None
        opening = balances[0] - (-candidates[0].amount_cents)
        running = opening
        for candidate, balance in zip(candidates, balances, strict=True):
            running += -candidate.amount_cents
            if running != balance:
                return None
        return -(balances[-1] - opening)
