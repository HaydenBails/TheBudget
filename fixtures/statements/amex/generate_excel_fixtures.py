"""Generate a deterministic, entirely synthetic Amex .xlsx parser fixture.

Mirrors the real "Transaction Details" + "Transaction Summary" workbook layout
Amex exports, using only invented merchants and a masked account. No real
statement content is committed.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

FIXTURE_DIRECTORY = Path(__file__).resolve().parent

_HEADER = [
    ["Transaction Details", "American Express Cobalt®"],
    ["Prepared for"],
    ["SYNTHETIC CARDMEMBER"],
    ["Account Number"],
    ["XXXX-XXXXXX-19005"],
    [],
]
_COLUMNS = [
    "Date",
    "Date Processed",
    "Description",
    "Amount",
    "Foreign Spend Amount",
    "Commission",
    "Exchange Rate",
    "Additional Information",
]
# (date, processed, description, amount, foreign, commission, rate, info)
_ROWS = [
    ["02 Jun 2026", "03 Jun 2026", "SYNTHETIC MARKET", 1234.56, "", "", "", ""],
    ["04 Jun 2026", "04 Jun 2026", "SYNTHETIC CLOUD", 13.45, "10,00 EUR", "", 1.345, ""],
    ["06 Jun 2026", "06 Jun 2026", "ANNUAL MEMBERSHIP FEE", 25.65, "", "", "", ""],
    ["07 Jun 2026", "07 Jun 2026", "SYNTHETIC CAFE", 100.00, "", "", "", ""],
    ["07 Jun 2026", "07 Jun 2026", "SYNTHETIC CAFE", 100.00, "", "", "", ""],
    ["05 Jun 2026", "05 Jun 2026", "SYNTHETIC RETURN", -25.00, "", "", "", ""],
    ["10 Jun 2026", "10 Jun 2026", "PAYMENT RECEIVED - THANK YOU", -1500.00, "", "", "", ""],
]
_SUMMARY = [
    ["Transaction Summary", "American Express Cobalt®"],
    ["Prepared for"],
    ["SYNTHETIC CARDMEMBER"],
    ["Account Number"],
    ["XXXX-XXXXXX-19005"],
    [],
    ["SUMMARY"],
    ["", "Total"],
    ["Last billed statement", 0.0],
    ["Payments & Credits", -1525.00],
    ["Charges & Adjustments", 1473.66],
    ["Summary for this billed period", -51.34],
]


def build() -> Workbook:
    workbook = Workbook()
    details = workbook.active
    details.title = "Transaction Details"
    for row in _HEADER:
        details.append(row)
    details.append(_COLUMNS)
    for row in _ROWS:
        details.append(row)

    summary = workbook.create_sheet("Transaction Summary")
    for row in _SUMMARY:
        summary.append(row)
    return workbook


def main() -> None:
    build().save(FIXTURE_DIRECTORY / "amex_excel_matrix.xlsx")


if __name__ == "__main__":
    main()
