// Shared dashboard/analytics period logic and money-format helpers. Used by the
// dashboard and the Merchants view so the period selector behaves identically.
import type { Transaction } from '../features/transactions/types';

export const pad = (n: number) => String(n).padStart(2, '0');
export const ymOf = (iso: string) => iso.slice(0, 7);

export function monthKey(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}
export function monthLabel(ym: string) {
  return new Date(`${ym}-01T00:00:00`).toLocaleDateString('en-CA', { month: 'long', year: 'numeric' });
}
export function shortMonth(ym: string) {
  return new Date(`${ym}-01T00:00:00`).toLocaleDateString('en-CA', { month: 'short' });
}
export function formatDay(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
}
/** Whole-dollar CAD for headline figures, e.g. "$4,049". */
export function formatDollars(cents: number) {
  const sign = cents < 0 ? '-' : '';
  return `${sign}$${Math.round(Math.abs(cents) / 100).toLocaleString('en-CA')}`;
}

// Canonical storage is signed: debit amounts are positive (money out), credit
// amounts are negative (money in). See validate_transaction_sign on the API.
/** Signed spend: positive amounts are outflow, negative (credits/refunds) reduce it. */
export const outflow = (t: Transaction) => t.amount_cents;
/** Display amount: money out shows negative, money in shows positive. */
export const displayAmount = (t: Transaction) => -t.amount_cents;

export interface DashRange {
  fromISO: string;
  toISO: string;
  label: string;
  cmpFromISO: string | null;
  cmpToISO: string | null;
  cmpLabel: string | null;
}
export const isoStart = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-01`;
export function isoEnd(d: Date) {
  const e = new Date(d.getFullYear(), d.getMonth() + 1, 0);
  return `${e.getFullYear()}-${pad(e.getMonth() + 1)}-${pad(e.getDate())}`;
}

/** Turn a period id (this/last/l3m/ytd/all or "YYYY-MM") into a date range + comparison. */
export function computeRange(period: string, now: Date, minDate: string, maxDate: string): DashRange {
  const y = now.getFullYear();
  const m = now.getMonth();
  const monthRange = (curM: Date, prevM: Date, label: string): DashRange => ({
    fromISO: isoStart(curM), toISO: isoEnd(curM), label,
    cmpFromISO: isoStart(prevM), cmpToISO: isoEnd(prevM), cmpLabel: shortMonth(monthKey(prevM)),
  });
  if (period === 'this') return monthRange(new Date(y, m, 1), new Date(y, m - 1, 1), 'this month');
  if (period === 'last') return monthRange(new Date(y, m - 1, 1), new Date(y, m - 2, 1), monthLabel(monthKey(new Date(y, m - 1, 1))));
  if (period === 'l3m') {
    return {
      fromISO: isoStart(new Date(y, m - 2, 1)), toISO: isoEnd(new Date(y, m, 1)), label: 'the last 3 months',
      cmpFromISO: isoStart(new Date(y, m - 5, 1)), cmpToISO: isoEnd(new Date(y, m - 3, 1)), cmpLabel: 'prev 3 mo',
    };
  }
  if (period === 'ytd') {
    return {
      fromISO: isoStart(new Date(y, 0, 1)), toISO: isoEnd(new Date(y, m, 1)), label: `${y} so far`,
      cmpFromISO: isoStart(new Date(y - 1, 0, 1)), cmpToISO: isoEnd(new Date(y - 1, m, 1)), cmpLabel: `${y - 1}`,
    };
  }
  if (period === 'all') {
    return {
      fromISO: minDate || isoStart(new Date(y, m, 1)), toISO: maxDate || isoEnd(new Date(y, m, 1)),
      label: 'all time', cmpFromISO: null, cmpToISO: null, cmpLabel: null,
    };
  }
  const [yy, mm] = period.split('-').map(Number);
  return monthRange(new Date(yy, mm - 1, 1), new Date(yy, mm - 2, 1), monthLabel(period));
}

export const PERIOD_PRESETS: { id: string; label: string }[] = [
  { id: 'this', label: 'This month' },
  { id: 'last', label: 'Last month' },
  { id: 'l3m', label: '3 months' },
  { id: 'ytd', label: 'Year to date' },
  { id: 'all', label: 'All time' },
];
