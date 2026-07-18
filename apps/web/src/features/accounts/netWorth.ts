import type { Transaction } from '../transactions/types';
import type { Account } from './types';

export interface NetWorthSummary {
  assets: number;
  liabilities: number;
  net: number;
  tracked: number;
}

/** Accounts that have a balance set (untracked accounts are ignored). */
export function trackedAccounts(accounts: Account[]): Account[] {
  return accounts.filter((a) => !a.is_archived && a.current_balance_cents != null);
}

export function netWorthNow(accounts: Account[]): NetWorthSummary {
  const tracked = trackedAccounts(accounts);
  let assets = 0;
  let liabilities = 0;
  for (const a of tracked) {
    const balance = a.current_balance_cents ?? 0;
    if (a.kind === 'asset') assets += balance;
    else liabilities += balance;
  }
  return { assets, liabilities, net: assets - liabilities, tracked: tracked.length };
}

/**
 * Reconstruct net worth at a past date from current balances + the ledger.
 * Each transaction after `dateISO` is "undone": a liability's owed balance was
 * raised by amount_cents (so subtract it going back); an asset's balance was
 * lowered by amount_cents (so add it going back).
 */
function netWorthAt(accounts: Account[], txByAccount: Map<number, Transaction[]>, dateISO: string): number {
  let total = 0;
  for (const a of accounts) {
    const current = a.current_balance_cents ?? 0;
    const after = (txByAccount.get(a.id) ?? [])
      .filter((t) => t.date > dateISO && t.deleted_at == null)
      .reduce((s, t) => s + t.amount_cents, 0);
    total += a.kind === 'asset' ? current + after : -(current - after);
  }
  return total;
}

const pad = (n: number) => String(n).padStart(2, '0');

export interface NetWorthPoint {
  ym: string;
  label: string;
  cents: number;
}

/** Net worth at each of the last `months` month-ends (oldest first). */
export function netWorthTrend(
  accounts: Account[],
  transactions: Transaction[],
  months = 6,
  now = new Date(),
): NetWorthPoint[] {
  const tracked = trackedAccounts(accounts);
  if (tracked.length === 0) return [];
  const txByAccount = new Map<number, Transaction[]>();
  for (const t of transactions) {
    const list = txByAccount.get(t.account_id) ?? [];
    list.push(t);
    txByAccount.set(t.account_id, list);
  }
  const points: NetWorthPoint[] = [];
  for (let i = months - 1; i >= 0; i--) {
    const monthEnd = new Date(now.getFullYear(), now.getMonth() - i + 1, 0);
    const ym = `${monthEnd.getFullYear()}-${pad(monthEnd.getMonth() + 1)}`;
    const iso = `${ym}-${pad(monthEnd.getDate())}`;
    points.push({
      ym,
      label: monthEnd.toLocaleDateString('en-CA', { month: 'short' }),
      cents: netWorthAt(tracked, txByAccount, iso),
    });
  }
  return points;
}
