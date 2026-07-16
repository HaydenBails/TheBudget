"""Versioned parser for supported TD Canada Trust credit-card statements."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.importing.contracts import (
    ExtractedDocument,
    ParserDetection,
    ReconciliationResult,
    StatementMetadata,
    TransactionCandidate,
    TransactionType,
)
from app.importing.errors import ScannedDocumentError, UnsupportedDocumentError
from app.importing.reconciliation import parse_exchange_rate, reconcile_totals
from app.parsers.base import StatementParser

_ISSUER_MARKERS = ("TD CANADA TRUST", "TD CREDIT CARD")
_TABLE_HEADER = re.compile(
    r"TRANSACTION\s+DATE\s+POSTING\s+DATE\s+ACTIVITY\s+DESCRIPTION\s+AMOUNT",
    re.IGNORECASE,
)
_PERIOD = re.compile(
    r"STATEMENT\s+PERIOD\s+(?P<start>[A-Z]{3,9}\s+\d{1,2},\s+\d{4})"
    r"\s+(?:TO|-)\s+(?P<end>[A-Z]{3,9}\s+\d{1,2},\s+\d{4})",
    re.IGNORECASE,
)
_MASKED_ACCOUNT = re.compile(
    r"ACCOUNT(?:\s+NUMBER)?\s+(?:[*X][\s-]*){4,}(?P<last4>\d{4})\b",
    re.IGNORECASE,
)
_GROUPED_DIGITS = r"(?:\d+|\d{1,3}(?:,\d{3})+)"
_AMOUNT_TEXT = (
    rf"(?:-?\$?{_GROUPED_DIGITS}\.\d{{2}}|"
    rf"\(\$?{_GROUPED_DIGITS}\.\d{{2}}\)|"
    rf"\$?{_GROUPED_DIGITS}\.\d{{2}}\s+CR)"
)
_TRANSACTION_ROW = re.compile(
    rf"^(?P<transaction_date>[A-Z]{{3}}\s+\d{{1,2}})\s+"
    rf"(?P<posted_date>[A-Z]{{3}}\s+\d{{1,2}})\s+"
    rf"(?P<description>.+?)\s+(?P<amount>{_AMOUNT_TEXT})$",
    re.IGNORECASE,
)
_TRANSACTION_ROW_PREFIX = re.compile(
    r"^[A-Z]{3}\s+\d{1,2}\s+[A-Z]{3}\s+\d{1,2}\s+",
    re.IGNORECASE,
)
_FOREIGN_AMOUNT = re.compile(
    rf"^FOREIGN\s+(?:CURRENCY|AMOUNT)\s+(?P<currency>[A-Z]{{3}})\s+"
    rf"(?P<amount>{_AMOUNT_TEXT})$",
    re.IGNORECASE,
)
_EXCHANGE_RATE = re.compile(
    r"^EXCHANGE\s+RATE\s+(?P<rate>(?:0|[1-9]\d*)(?:\.\d{1,8})?)$",
    re.IGNORECASE,
)
_FOREIGN_COMBINED = re.compile(
    rf"^FOREIGN\s+(?:CURRENCY|AMOUNT)\s+(?P<currency>[A-Z]{{3}})\s+"
    rf"(?P<amount>{_AMOUNT_TEXT})\s+(?:AT|@)\s+"
    r"(?P<rate>(?:0|[1-9]\d*)(?:\.\d{1,8})?)$",
    re.IGNORECASE,
)
_SUMMARY_MARKERS = {
    "ACCOUNT ACTIVITY SUMMARY",
    "PAYMENT SLIP",
    "REWARDS SUMMARY",
    "LEGAL INFORMATION",
}
_IGNORED_PREFIXES = (
    "PAGE ",
    "TD CANADA TRUST",
    "TD CREDIT CARD",
    "CREDIT CARD STATEMENT",
    "ACCOUNT NUMBER",
    "STATEMENT PERIOD",
    "STATEMENT DATE",
    "CONTINUED ON NEXT PAGE",
    "PAYMENT SLIP",
    "MINIMUM PAYMENT",
    "PAYMENT DUE DATE",
    "REWARDS SUMMARY",
    "REWARD BALANCE",
    "LEGAL INFORMATION",
    "IMPORTANT INFORMATION",
)
_SUMMARY_PATTERNS = {
    "credits": re.compile(rf"^PAYMENTS\s+AND\s+CREDITS\s+(?P<amount>{_AMOUNT_TEXT})$", re.I),
    "purchases": re.compile(
        rf"^PURCHASES\s+AND\s+OTHER\s+CHARGES\s+(?P<amount>{_AMOUNT_TEXT})$", re.I
    ),
    "interest": re.compile(rf"^INTEREST\s+CHARGES\s+(?P<amount>{_AMOUNT_TEXT})$", re.I),
    "fees": re.compile(rf"^FEES\s+(?P<amount>{_AMOUNT_TEXT})$", re.I),
}


@dataclass(slots=True)
class _PendingTransaction:
    transaction_date: date
    posted_date: date
    description: str
    amount_cents: int
    txn_type: TransactionType
    original_currency: str | None = None
    original_amount_cents: int | None = None
    exchange_rate: Decimal | None = None


@dataclass(frozen=True, slots=True, repr=False)
class _TdStatementMetadata(StatementMetadata):
    section_totals_cents: tuple[tuple[str, int], ...] = ()


def _parse_amount_cents(value: str) -> int:
    normalized = value.strip().upper()
    negative = normalized.endswith(" CR") or normalized.startswith("-") or (
        normalized.startswith("(") and normalized.endswith(")")
    )
    digits = normalized.replace("$", "").replace(",", "").replace(" CR", "")
    digits = digits.removeprefix("-").removeprefix("(").removesuffix(")")
    match = re.fullmatch(r"(?P<whole>\d+)\.(?P<fraction>\d{2})", digits)
    if match is None:
        raise UnsupportedDocumentError("TD statement contains an ambiguous monetary amount")
    cents = int(match.group("whole")) * 100 + int(match.group("fraction"))
    return -cents if negative else cents


def _parse_period_date(value: str) -> date:
    for pattern in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value.title(), pattern).date()
        except ValueError:
            continue
    raise UnsupportedDocumentError("TD statement period could not be parsed")


def _infer_row_date(value: str, period_start: date, period_end: date) -> date:
    parsed = datetime.strptime(f"{value.title()} 2000", "%b %d %Y")
    candidates: set[date] = set()
    for year in (period_start.year, period_end.year):
        try:
            candidates.add(date(year, parsed.month, parsed.day))
        except ValueError:
            # A leap-day row can be valid for only one year of a cross-year period.
            continue
    in_period = sorted(
        candidate for candidate in candidates if period_start <= candidate <= period_end
    )
    if len(in_period) != 1:
        raise UnsupportedDocumentError("TD transaction date falls outside the statement period")
    return in_period[0]


def _classify(description: str, amount_cents: int) -> TransactionType:
    normalized = " ".join(description.upper().split())
    if "PAYMENT - THANK YOU" in normalized:
        return "payment"
    if "INTEREST" in normalized:
        return "interest"
    if "FEE" in normalized:
        return "fee"
    if "CASH ADVANCE" in normalized:
        return "cash_advance"
    negative_markers = ("REFUND", "RETURN", "CREDIT")
    if amount_cents < 0 or any(marker in normalized for marker in negative_markers):
        return "refund"
    return "purchase"


def _normalized_lines(document: ExtractedDocument) -> tuple[tuple[int, str], ...]:
    return tuple(
        (page_index, " ".join(line.split()))
        for page_index, page in enumerate(document.pages)
        for line in page.splitlines()
        if line.strip()
    )


class TdCreditCardParser(StatementParser):
    """Parse the supported, section-aware TD credit-card text layout."""

    parser_name = "td_credit_card"
    parser_version = "1.0.0"

    def detect(self, document: ExtractedDocument) -> ParserDetection:
        text = "\n".join(document.pages).upper()
        if not text.strip():
            return ParserDetection(False, Decimal("0"), "no_extractable_text")
        issuer = any(marker in text for marker in _ISSUER_MARKERS)
        has_table = _TABLE_HEADER.search(text) is not None
        has_period = _PERIOD.search(text) is not None
        if issuer and has_table and has_period:
            return ParserDetection(True, Decimal("1"), "td_supported_layout")
        if issuer and has_table:
            return ParserDetection(True, Decimal("0.80"), "td_layout_missing_period")
        if issuer:
            return ParserDetection(False, Decimal("0.25"), "td_unsupported_layout")
        return ParserDetection(False, Decimal("0"), "issuer_not_td")

    def extract_metadata(self, document: ExtractedDocument) -> StatementMetadata:
        self._require_supported(document)
        text = "\n".join(document.pages)
        period_match = _PERIOD.search(text)
        if period_match is None:
            raise UnsupportedDocumentError("TD statement period is missing")
        period_start = _parse_period_date(period_match.group("start"))
        period_end = _parse_period_date(period_match.group("end"))
        account_match = _MASKED_ACCOUNT.search(text)
        summaries = self._extract_summary_amounts(document)
        expected_credits = summaries.get("credits")
        if expected_credits is not None:
            expected_credits = -abs(expected_credits)
        debit_sections = [summaries.get(name) for name in ("purchases", "interest", "fees")]
        expected_debits = (
            sum(abs(value) for value in debit_sections if value is not None)
            if any(value is not None for value in debit_sections)
            else None
        )
        expected_activity = (
            expected_debits + expected_credits
            if expected_debits is not None and expected_credits is not None
            else None
        )
        return _TdStatementMetadata(
            issuer="TD",
            account_last4=account_match.group("last4") if account_match else None,
            period_start=period_start,
            period_end=period_end,
            expected_activity_cents=expected_activity,
            expected_debits_cents=expected_debits,
            expected_credits_cents=expected_credits,
            section_totals_cents=tuple(sorted(summaries.items())),
        )

    def extract_transactions(
        self, document: ExtractedDocument
    ) -> Sequence[TransactionCandidate]:
        detection = self.detect(document)
        if detection.reason_code == "no_extractable_text":
            raise ScannedDocumentError(
                "TD statement contains no extractable text; use a text-based PDF"
            )
        if not detection.matched:
            raise UnsupportedDocumentError("TD statement layout is not supported")
        metadata = self.extract_metadata(document)
        assert metadata.period_start is not None and metadata.period_end is not None

        pending: _PendingTransaction | None = None
        transactions: list[TransactionCandidate] = []
        occurrences: Counter[tuple[object, ...]] = Counter()
        in_transactions = False

        def flush() -> None:
            nonlocal pending
            if pending is None:
                return
            foreign_values = (
                pending.original_currency,
                pending.original_amount_cents,
                pending.exchange_rate,
            )
            if any(value is not None for value in foreign_values) and not all(
                value is not None for value in foreign_values
            ):
                raise UnsupportedDocumentError(
                    "TD foreign-currency continuation is incomplete"
                )
            pending.txn_type = _classify(
                pending.description,
                pending.amount_cents,
            )
            key = (
                pending.transaction_date,
                pending.posted_date,
                " ".join(pending.description.casefold().split()),
                pending.amount_cents,
                pending.txn_type,
            )
            occurrence_index = occurrences[key]
            occurrences[key] += 1
            transactions.append(
                TransactionCandidate(
                    source_index=len(transactions),
                    occurrence_index=occurrence_index,
                    transaction_date=pending.transaction_date,
                    posted_date=pending.posted_date,
                    raw_description=pending.description,
                    amount_cents=pending.amount_cents,
                    txn_type=pending.txn_type,
                    direction="debit" if pending.amount_cents > 0 else "credit",
                    original_currency=pending.original_currency,
                    original_amount_cents=pending.original_amount_cents,
                    exchange_rate=pending.exchange_rate,
                )
            )
            pending = None

        for _page_index, line in _normalized_lines(document):
            upper = line.upper()
            if _TABLE_HEADER.fullmatch(line):
                in_transactions = True
                continue
            if upper in _SUMMARY_MARKERS:
                flush()
                in_transactions = False
                continue
            if not in_transactions or upper.startswith(_IGNORED_PREFIXES):
                continue
            row_match = _TRANSACTION_ROW.fullmatch(line)
            if row_match is not None:
                flush()
                amount_cents = _parse_amount_cents(row_match.group("amount"))
                description = " ".join(row_match.group("description").split())
                pending = _PendingTransaction(
                    transaction_date=_infer_row_date(
                        row_match.group("transaction_date"),
                        metadata.period_start,
                        metadata.period_end,
                    ),
                    posted_date=_infer_row_date(
                        row_match.group("posted_date"),
                        metadata.period_start,
                        metadata.period_end,
                    ),
                    description=description,
                    amount_cents=amount_cents,
                    txn_type=_classify(description, amount_cents),
                )
                continue
            if _TRANSACTION_ROW_PREFIX.match(line):
                raise UnsupportedDocumentError(
                    "TD statement contains an ambiguous transaction row"
                )
            if pending is None:
                continue
            combined_match = _FOREIGN_COMBINED.fullmatch(line)
            foreign_match = _FOREIGN_AMOUNT.fullmatch(line)
            rate_match = _EXCHANGE_RATE.fullmatch(line)
            if combined_match is not None:
                if any(
                    value is not None
                    for value in (
                        pending.original_currency,
                        pending.original_amount_cents,
                        pending.exchange_rate,
                    )
                ):
                    raise UnsupportedDocumentError(
                        "TD foreign-currency continuation is duplicated or conflicting"
                    )
                pending.original_currency = combined_match.group("currency").upper()
                pending.original_amount_cents = _parse_amount_cents(
                    combined_match.group("amount")
                )
                pending.exchange_rate = parse_exchange_rate(combined_match.group("rate"))
            elif foreign_match is not None:
                if (
                    pending.original_currency is not None
                    or pending.original_amount_cents is not None
                ):
                    raise UnsupportedDocumentError(
                        "TD foreign-currency continuation is duplicated or conflicting"
                    )
                pending.original_currency = foreign_match.group("currency").upper()
                pending.original_amount_cents = _parse_amount_cents(
                    foreign_match.group("amount")
                )
            elif rate_match is not None:
                if pending.exchange_rate is not None:
                    raise UnsupportedDocumentError(
                        "TD foreign-currency continuation is duplicated or conflicting"
                    )
                pending.exchange_rate = parse_exchange_rate(rate_match.group("rate"))
            elif upper.startswith("DESCRIPTION CONTINUED:"):
                continuation = line.partition(":")[2].strip()
                if continuation:
                    pending.description = f"{pending.description} {continuation}"
            elif not any(pattern.fullmatch(line) for pattern in _SUMMARY_PATTERNS.values()):
                pending.description = f"{pending.description} {line}"
        flush()
        if not transactions:
            raise UnsupportedDocumentError("TD statement has no recognized transaction rows")
        return tuple(transactions)

    def reconcile(
        self,
        metadata: StatementMetadata,
        transactions: Sequence[TransactionCandidate],
    ) -> ReconciliationResult:
        parsed_debits = sum(
            candidate.amount_cents
            for candidate in transactions
            if candidate.amount_cents > 0
        )
        parsed_credits = sum(
            candidate.amount_cents
            for candidate in transactions
            if candidate.amount_cents < 0
        )
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
        if isinstance(metadata, _TdStatementMetadata):
            parsed_sections = {
                "credits": parsed_credits,
                "purchases": sum(
                    candidate.amount_cents
                    for candidate in transactions
                    if candidate.amount_cents > 0
                    and candidate.txn_type in {"purchase", "cash_advance"}
                ),
                "interest": sum(
                    candidate.amount_cents
                    for candidate in transactions
                    if candidate.txn_type == "interest"
                ),
                "fees": sum(
                    candidate.amount_cents
                    for candidate in transactions
                    if candidate.txn_type == "fee"
                ),
            }
            section_deltas.extend(
                parsed_sections[name]
                - (-abs(expected) if name == "credits" else abs(expected))
                for name, expected in metadata.section_totals_cents
            )
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

    def _require_supported(self, document: ExtractedDocument) -> None:
        detection = self.detect(document)
        if detection.reason_code == "no_extractable_text":
            raise ScannedDocumentError(
                "TD statement contains no extractable text; use a text-based PDF"
            )
        if not detection.matched:
            raise UnsupportedDocumentError("TD statement layout is not supported")

    def _extract_summary_amounts(self, document: ExtractedDocument) -> dict[str, int]:
        amounts: dict[str, int] = {}
        for _page_index, line in _normalized_lines(document):
            for name, pattern in _SUMMARY_PATTERNS.items():
                match = pattern.fullmatch(line)
                if match is None:
                    continue
                value = _parse_amount_cents(match.group("amount"))
                previous = amounts.get(name)
                if previous is not None and previous != value:
                    raise UnsupportedDocumentError(
                        f"TD statement has conflicting {name} summary totals"
                    )
                amounts[name] = value
        return amounts
