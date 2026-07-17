import type { Transaction } from '../transactions/types';

/**
 * Included spending for one month, following the canonical signed-cents
 * convention: debit amounts are positive (money out), credits negative (money
 * in), and only transactions counted `included_in_spending` contribute.
 */
export interface MonthSpending {
  /** Total included spend for the month, in cents. */
  overall: number;
  /** Included spend per category id, in cents. */
  byCategory: Map<number, number>;
}

const ymOf = (iso: string) => iso.slice(0, 7);

export function monthSpending(transactions: Transaction[], periodMonth: string): MonthSpending {
  const byCategory = new Map<number, number>();
  let overall = 0;
  for (const t of transactions) {
    if (!t.included_in_spending || ymOf(t.date) !== periodMonth) continue;
    overall += t.amount_cents;
    if (t.category_id != null) {
      byCategory.set(t.category_id, (byCategory.get(t.category_id) ?? 0) + t.amount_cents);
    }
  }
  return { overall, byCategory };
}

export type BudgetLevel = 'ok' | 'warn' | 'high' | 'over';

/** Product-plan warning thresholds at 75%, 90%, and 100% of the limit. */
export function budgetLevel(spentCents: number, limitCents: number): BudgetLevel {
  if (limitCents <= 0) return 'ok';
  const ratio = spentCents / limitCents;
  if (ratio >= 1) return 'over';
  if (ratio >= 0.9) return 'high';
  if (ratio >= 0.75) return 'warn';
  return 'ok';
}

export const budgetLevelLabel: Record<BudgetLevel, string> = {
  ok: 'On track',
  warn: 'Approaching limit',
  high: 'Nearly at limit',
  over: 'Over budget',
};
