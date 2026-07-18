"""Generate the synthetic TD account-activity CSV fixture and its expected JSON.

The data is entirely fabricated — generic merchant names, no real account
number, integer cents only — so it is safe to commit under the no-real-statements
rule. Running this regenerates ``td_account_activity.csv`` and
``td_account_activity.expected.json`` deterministically.

    python fixtures/statements/td/generate_csv_fixtures.py
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "td_account_activity.csv"
JSON_PATH = HERE / "td_account_activity.expected.json"

OPENING_BALANCE = Decimal("1000.00")

# (date MM/DD/YYYY, description, charge, credit, expected txn_type)
ACTIVITY = [
    ("07/01/2026", "PAYROLL DEPOSIT PAY", None, "2000.00", "income"),
    ("07/02/2026", "MONTHLY PLAN FEE", "10.95", None, "fee"),
    ("07/03/2026", "TIM HORTONS", "4.65", None, "purchase"),
    ("07/03/2026", "TIM HORTONS", "4.65", None, "purchase"),
    ("07/05/2026", "HYDRO ONE BILL PAYMENT", "142.30", None, "payment"),
    ("07/08/2026", "LOBLAWS", "86.42", None, "purchase"),
    ("07/10/2026", "SEND E-TFR", "500.00", None, "transfer"),
    ("07/12/2026", "AMAZON", "39.99", None, "purchase"),
    ("07/15/2026", "INTEREST", None, "1.05", "interest"),
    ("07/20/2026", "SHELL", "55.20", None, "purchase"),
]


def _cents(text: str) -> int:
    return int((Decimal(text) * 100).to_integral_value())


def build() -> tuple[list[list[str]], dict[str, object]]:
    rows: list[list[str]] = []
    balance = OPENING_BALANCE
    candidates: list[dict[str, object]] = []
    occurrences: dict[tuple[object, ...], int] = {}
    parsed_total = 0
    for index, (date, desc, charge, credit, txn_type) in enumerate(ACTIVITY):
        charge_dec = Decimal(charge) if charge else Decimal("0")
        credit_dec = Decimal(credit) if credit else Decimal("0")
        balance = balance + credit_dec - charge_dec
        rows.append([date, desc, charge or "", credit or "", f"{balance:.2f}"])
        amount_cents = _cents(charge) if charge else -_cents(credit)  # type: ignore[arg-type]
        parsed_total += amount_cents
        key = (date, desc.casefold(), amount_cents, txn_type)
        occ = occurrences.get(key, 0)
        occurrences[key] = occ + 1
        candidates.append(
            {
                "source_index": index,
                "occurrence_index": occ,
                "transaction_date": f"2026-{date[0:2]}-{date[3:5]}",
                "posted_date": None,
                "raw_description": desc,
                "amount_cents": amount_cents,
                "txn_type": txn_type,
                "direction": "debit" if amount_cents > 0 else "credit",
                "original_currency": None,
                "original_amount_cents": None,
                "exchange_rate": None,
            }
        )
    expected_activity = -(_cents(f"{balance:.2f}") - _cents(f"{OPENING_BALANCE:.2f}"))
    expected = {
        "metadata": {
            "issuer": "TD",
            "account_last4": None,
            "period_start": "2026-07-01",
            "period_end": "2026-07-20",
            "currency": "CAD",
            "expected_activity_cents": expected_activity,
            "expected_debits_cents": None,
            "expected_credits_cents": None,
        },
        "transactions": candidates,
        "reconciliation": {
            "status": "reconciled",
            "expected_cents": expected_activity,
            "parsed_cents": parsed_total,
            "delta_cents": parsed_total - expected_activity,
            "tolerance_cents": 1,
            "transaction_count": len(candidates),
        },
    }
    return rows, expected


def main() -> None:
    rows, expected = build()
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    JSON_PATH.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {CSV_PATH.name} ({len(rows)} rows) and {JSON_PATH.name}")


if __name__ == "__main__":
    main()
