---
type: "review"
date: "2026-07-16T15:58:15.513931+00:00"
question: "Final independent BE-15 review of stale/concurrent duplicate safety, atomic rollback, one-cent reconciliation, durable failures, partial unique index parity, and occurrence repeats"
contributor: "graphify"
outcome: "useful"
source_nodes: ["preview_import", "commit_import", "_commit_rows_atomic", "ImportBatch", "Transaction", "ImportStagedTransaction"]
---

# Q: Final independent BE-15 review of stale/concurrent duplicate safety, atomic rollback, one-cent reconciliation, durable failures, partial unique index parity, and occurrence repeats

## Answer

Expanded from graph vocabulary: [commit, duplicate, atomic, failure, index, migration, occurrence, fingerprint, batch, staged, transaction, reconciliation]. Current graph correctly located preview_import, commit_import, _commit_rows_atomic, ImportBatch, Transaction, staged rows, and focused persistence/service tests. Verified clean through source review and tests: writer claims serialize SQLite preview/commit decisions; unique non-null profile/account/fingerprint index is the final guard; result construction is inside the savepoint; failures return durable structured status without rows; tolerance above one cent fails; occurrence indexes preserve repeated rows.

## Outcome

- Signal: useful

## Source Nodes

- preview_import
- commit_import
- _commit_rows_atomic
- ImportBatch
- Transaction
- ImportStagedTransaction