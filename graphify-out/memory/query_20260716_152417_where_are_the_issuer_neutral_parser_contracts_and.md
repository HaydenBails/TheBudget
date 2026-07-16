---
type: "architecture"
date: "2026-07-16T15:24:17.088312+00:00"
question: "Where are the issuer-neutral parser contracts and exact reconciliation boundaries needed by the TD parser? Expanded terms: statement parser detection metadata candidate transaction reconciliation occurrences foreign payment refund interest"
contributor: "graphify"
outcome: "useful"
source_nodes: ["StatementParser", "TransactionCandidate", "reconcile_totals"]
---

# Q: Where are the issuer-neutral parser contracts and exact reconciliation boundaries needed by the TD parser? Expanded terms: statement parser detection metadata candidate transaction reconciliation occurrences foreign payment refund interest

## Answer

StatementParser defines detect/extract_metadata/extract_transactions/reconcile; TransactionCandidate enforces exact structured rows and occurrence indexes; reconcile_totals enforces signed-cent one-cent-tolerance reconciliation. BE-14 should implement only a versioned TD adapter and synthetic fixture matrix over those boundaries.

## Outcome

- Signal: useful

## Source Nodes

- StatementParser
- TransactionCandidate
- reconcile_totals