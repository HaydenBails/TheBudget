# Parser notes

Per-issuer findings for text-based statement parsing live here. Each issuer gets
its own note (e.g. `td.md`, `amex.md`, `cibc.md`) as samples are reviewed and
parsers are built. This directory is documentation only — the actual parsers
arrive in a later stage (see [`docs/decisions/0001-tech-stack.md`](../decisions/0001-tech-stack.md)).

Scope reminder: only **text-based** (selectable-text) statement PDFs are
supported; scanned/image statements are out of scope. **No real statements are
committed** — work from synthetic or redacted fixtures only (see
[`fixtures/statements/README.md`](../../fixtures/statements/README.md)).

## Issuer status

| Issuer   | Status                          | Notes                                   |
| -------- | ------------------------------- | --------------------------------------- |
| **TD**   | Reviewed — suitable             | See §6.4 summary below.                 |
| **Amex** | Reviewed — suitable             | See §6.5 summary below.                 |
| **CIBC** | **Parser pending** — need samples | Awaiting representative synthetic samples.|

## TD (product plan §6.4) — reviewed & suitable

- Text-based PDFs with **selectable text**; pdfplumber extracts cleanly.
- Transaction rows follow a consistent layout with **transaction date**,
  **posting date**, **description**, and **amount** columns.
- Statement period and account/last-4 are recoverable from the header.
- Credits (payments/refunds) are distinguishable from purchases (sign / column
  placement), enabling `txn_type` classification.
- Conclusion: **suitable** for a rule-based line parser; no OCR needed.

## Amex (product plan §6.5) — reviewed & suitable

- Text-based PDFs; pdfplumber extraction is reliable.
- Row layout differs from TD (issuer-specific date/description/amount
  arrangement) but is regular and parseable with an Amex-specific line pattern.
- Purchases vs payments/credits are distinguishable for spending inclusion.
- Conclusion: **suitable**; implement as a separate issuer profile from TD.

## CIBC — parser pending

- No representative (synthetic/redacted) samples reviewed yet.
- Layout, date columns, and credit handling are **unconfirmed**.
- **Action:** obtain synthetic samples, then document the layout here and build
  the parser. Marked **parser pending** until then.
