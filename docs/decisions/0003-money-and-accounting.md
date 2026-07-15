# 3. Money representation and spending inclusion

- **Status:** Accepted
- **Date:** 2026-07-15

## Context

The domain is money, so representation and accounting semantics must be exact
and consistent across the database, API, and UI. Two recurring hazards:

1. **Floating-point currency** causes rounding drift in sums, budgets, and
   reconciliation.
2. **Not all transactions are "spending."** A statement mixes purchases,
   payments, transfers, refunds, cash advances, interest, fees, and income.
   Counting the wrong rows inflates or deflates spending totals and budgets.

## Decision

### Money as integer cents

All monetary amounts are stored and computed as **integer cents** (e.g. `$12.34`
→ `1234`; `amount_cents` columns). No floating-point currency is ever persisted
or used in arithmetic. Conversion to a formatted dollar string happens **only at
the presentation edge**. Base currency is **CAD**. Sign convention: purchases
(outflows) are positive spending; credits (payments/refunds/income) carry the
opposite sign per issuer normalization.

### Spending inclusion by transaction type

Each transaction carries a `txn_type` and a derived `included_in_spending` flag.
The canonical treatment (product plan §7.2):

| Transaction type  | Included in spending? | Notes                                                        |
| ----------------- | :-------------------: | ------------------------------------------------------------ |
| **Purchase**      | **Yes**               | Core spend; categorized and budgeted.                        |
| **Payment**       | No                    | Paying the card balance is not spending (avoids double-count).|
| **Transfer**      | No                    | Movement between own accounts; net-zero, not consumption.    |
| **Refund**        | No (offsets)          | Reduces the category it reverses; not counted as new spend.  |
| **Cash advance**  | No                    | Borrowing, not consumption; tracked separately from spend.   |
| **Interest**      | No                    | Cost of borrowing; reported as a fee/cost, not category spend.|
| **Fee**           | No                    | Bank/card fees; reported as a cost, not category spend.      |
| **Income**        | No                    | Tracked for income vs spending / savings, not as spending.   |

Only **purchases** (and net refunds against them) drive category spending totals
and budget consumption. Interest and fees are surfaced separately as costs;
income feeds income-vs-spending and savings views but is never counted as spend.

## Consequences

- **Positive:** exact arithmetic (no rounding drift); consistent spending totals
  across dashboard, budgets, and exports; a single source of truth for what
  "counts" as spending.
- **Negative / trade-offs:** every amount must be converted at UI/import
  boundaries (integer in, format out); `txn_type` classification must be correct
  during import — misclassification distorts totals, so parser/rule accuracy for
  type detection is important.
- Splits and tags operate on included (purchase) amounts; a split's child
  `amount_cents` values must sum to the parent transaction amount.
