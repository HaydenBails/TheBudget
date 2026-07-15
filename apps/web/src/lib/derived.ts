// Centralized derived metrics. Every UI direction MUST use these helpers rather
// than recomputing financial formulas, so all three show identical numbers.
import {
  budgets,
  categoryById,
  categories,
  CURRENT_MONTH,
  incomeSchedules,
  recurringSeries,
  TODAY,
  transactions,
} from './mockData';
import type { Transaction } from './types';

export function monthOf(iso: string): string {
  return iso.slice(0, 7); // YYYY-MM
}
const CUR = monthOf(CURRENT_MONTH); // '2026-07'
const PREV = '2026-06';

/** Transactions in a given YYYY-MM that count toward spending. */
export function spendingTxnsInMonth(ym: string): Transaction[] {
  return transactions.filter(
    (t) => monthOf(t.date) === ym && t.includedInSpending && (t.type === 'purchase' || t.type === 'refund'),
  );
}

/** Net included spending (purchases minus refunds), returned as a positive number of cents. */
export function totalSpendingCents(ym: string): number {
  const net = spendingTxnsInMonth(ym).reduce((sum, t) => sum + t.amountCents, 0);
  return Math.abs(net); // purchases are negative; magnitude is the spend
}

export interface CategorySpend {
  categoryId: string;
  name: string;
  color: string;
  icon: string;
  cents: number;
}

/** Spending grouped by category for a month, largest first. */
export function spendingByCategory(ym: string): CategorySpend[] {
  const totals = new Map<string, number>();
  for (const t of spendingTxnsInMonth(ym)) {
    if (!t.categoryId) continue;
    totals.set(t.categoryId, (totals.get(t.categoryId) ?? 0) + t.amountCents);
  }
  return [...totals.entries()]
    .map(([categoryId, signed]) => {
      const c = categoryById[categoryId];
      return { categoryId, name: c.name, color: c.color, icon: c.icon, cents: Math.abs(signed) };
    })
    .filter((c) => c.cents > 0)
    .sort((a, b) => b.cents - a.cents);
}

export interface MonthlyPoint {
  month: string; // 'YYYY-MM'
  label: string; // 'Apr'
  cents: number;
}

/** Total spending per month across the dataset (oldest -> newest). */
export function monthlyTrend(): MonthlyPoint[] {
  const months = ['2026-04', '2026-05', '2026-06', '2026-07'];
  const labels: Record<string, string> = { '2026-04': 'Apr', '2026-05': 'May', '2026-06': 'Jun', '2026-07': 'Jul' };
  return months.map((m) => ({ month: m, label: labels[m], cents: totalSpendingCents(m) }));
}

/** Percentage change of current month vs previous. Positive = spending up. */
export function monthOverMonthChange(): number {
  const cur = totalSpendingCents(CUR);
  const prev = totalSpendingCents(PREV);
  if (prev === 0) return 0;
  return (cur - prev) / prev;
}

/** Recorded + expected income for the current month, in cents. */
export function incomeThisMonthCents(): number {
  // Simplified forecast: count each active schedule's typical monthly contribution.
  return incomeSchedules
    .filter((s) => s.active)
    .reduce((sum, s) => {
      const perMonth =
        s.frequency === 'weekly' ? s.amountCents * 4.33 : s.frequency === 'biweekly' ? s.amountCents * 2.17 : s.amountCents;
      return sum + Math.round(perMonth);
    }, 0);
}

/** Confirmed recurring charges still expected before month end (not yet posted). */
export function upcomingRecurringCents(): number {
  return recurringSeries
    .filter((r) => r.status === 'keep' && r.nextExpectedDate.slice(0, 7) === CUR && r.nextExpectedDate >= TODAY)
    .reduce((sum, r) => sum + r.expectedAmountCents, 0);
}

/**
 * Available to save (estimate) for the current month:
 *   income - included net spending to date - upcoming confirmed recurring charges.
 */
export function availableToSaveCents(): number {
  return incomeThisMonthCents() - totalSpendingCents(CUR) - upcomingRecurringCents();
}

export function overallBudgetCents(): number {
  return budgets.find((b) => b.categoryId === null)?.monthlyLimitCents ?? 0;
}

export interface CategoryBudgetProgress {
  categoryId: string;
  name: string;
  color: string;
  icon: string;
  spentCents: number;
  limitCents: number;
  pct: number;
}

export function categoryBudgetProgress(ym: string): CategoryBudgetProgress[] {
  const spend = new Map(spendingByCategory(ym).map((c) => [c.categoryId, c.cents]));
  return budgets
    .filter((b) => b.categoryId !== null)
    .map((b) => {
      const c = categoryById[b.categoryId as string];
      const spentCents = spend.get(b.categoryId as string) ?? 0;
      return {
        categoryId: b.categoryId as string,
        name: c.name,
        color: c.color,
        icon: c.icon,
        spentCents,
        limitCents: b.monthlyLimitCents,
        pct: b.monthlyLimitCents ? spentCents / b.monthlyLimitCents : 0,
      };
    })
    .sort((a, b) => b.pct - a.pct);
}

/** Largest included purchases this month. */
export function largestPurchases(ym: string, limit = 5): Transaction[] {
  return spendingTxnsInMonth(ym)
    .filter((t) => t.type === 'purchase')
    .sort((a, b) => a.amountCents - b.amountCents) // most negative first
    .slice(0, limit);
}

/** Recent transactions across all accounts. */
export function recentTransactions(limit = 8): Transaction[] {
  return transactions.slice(0, limit);
}

/** Transactions awaiting category review (uncategorized / suggested). */
export function reviewQueue(): Transaction[] {
  return transactions.filter(
    (t) => t.categoryId === null || t.categorizationStatus === 'suggested',
  );
}

/** Excluded activity totals (payments, interest, fees) for disclosure. */
export function excludedActivityCents(ym: string): number {
  return transactions
    .filter((t) => monthOf(t.date) === ym && !t.includedInSpending)
    .reduce((sum, t) => sum + Math.abs(t.amountCents), 0);
}

export const allCategories = categories;
export const CURRENT_YM = CUR;
export const PREV_YM = PREV;
