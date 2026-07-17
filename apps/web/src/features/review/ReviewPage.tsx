import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useCurrentProfile } from '../profiles/ProfileContext';
import { useAccounts } from '../accounts/api';
import { useCategories } from '../categories/api';
import { CategoryIcon } from '../categories/CategoryIcon';
import { useTransactions, useUpdateTransaction } from '../transactions/api';
import { formatCad } from '../transactions/money';
import type { Transaction, TransactionFilters } from '../transactions/types';
import type { Category } from '../categories/types';
import type { Account } from '../accounts/types';
import './review.css';

const ALL: TransactionFilters = {
  accountId: null,
  categoryId: null,
  type: null,
  dateFrom: '',
  dateTo: '',
  includedInSpending: null,
  search: '',
  includeDeleted: false,
};

function formatDay(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-CA', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
}
/** Money out shows negative, money in positive. */
const displayAmount = (t: Transaction) => -t.amount_cents;

interface HistoryEntry {
  transaction: Transaction;
  previousCategoryId: number | null;
}

export function ReviewPage() {
  const { currentProfile, currentProfileId } = useCurrentProfile();
  const txns = useTransactions(currentProfileId, ALL);
  const categories = useCategories(currentProfileId, false);
  const accounts = useAccounts(currentProfileId, false);
  const update = useUpdateTransaction(currentProfileId ?? 0);

  const [queue, setQueue] = useState<Transaction[] | null>(null);
  const [index, setIndex] = useState(0);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  // Snapshot the uncategorized queue once per load so the current card doesn't
  // reshuffle under the user as mutations invalidate the list.
  useEffect(() => {
    if (queue === null && txns.data) {
      const pending = txns.data
        .filter((t) => t.category_id == null && t.deleted_at == null)
        .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : b.id - a.id));
      setQueue(pending);
      setIndex(0);
      setHistory([]);
    }
  }, [txns.data, queue]);

  const catList = useMemo(
    () => (categories.data ?? []).filter((c) => !c.is_archived),
    [categories.data],
  );
  const acctById = useMemo(
    () => new Map<number, Account>((accounts.data ?? []).map((a) => [a.id, a])),
    [accounts.data],
  );

  const current = queue && index < queue.length ? queue[index] : null;
  const total = queue?.length ?? 0;

  const assign = useCallback((categoryId: number) => {
    if (!current) return;
    setHistory((h) => [...h, { transaction: current, previousCategoryId: current.category_id }]);
    update.mutate({ id: current.id, body: { category_id: categoryId, categorization_status: 'manual' } });
    setIndex((i) => i + 1);
  }, [current, update]);

  const skip = useCallback(() => {
    if (current) setIndex((i) => i + 1);
  }, [current]);

  const undo = useCallback(() => {
    if (history.length === 0) return;
    const last = history[history.length - 1];
    setHistory((h) => h.slice(0, -1));
    update.mutate({
      id: last.transaction.id,
      body: { category_id: last.previousCategoryId, categorization_status: last.previousCategoryId == null ? 'uncategorized' : 'manual' },
    });
    setIndex((i) => Math.max(0, i - 1));
  }, [history, update]);

  // Keyboard: 1–9 pick a category, S skip, U/Backspace undo.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      const digit = Number(event.key);
      if (Number.isInteger(digit) && digit >= 1 && digit <= 9 && catList[digit - 1]) {
        event.preventDefault();
        assign(catList[digit - 1].id);
      } else if (event.key.toLowerCase() === 's') {
        event.preventDefault();
        skip();
      } else if (event.key.toLowerCase() === 'u' || event.key === 'Backspace') {
        event.preventDefault();
        undo();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [catList, assign, skip, undo]);

  if (currentProfileId == null) {
    return (
      <>
        <div className="app-head"><div><h1>Review</h1><p>Quickly categorize new transactions.</p></div></div>
        <div className="app-card app-placeholder">
          <h2>No profile selected</h2>
          <p>Transactions belong to a profile. Create or select one first.</p>
          <Link className="app-btn primary" to="/app/profiles" style={{ marginTop: 14 }}>Go to profiles</Link>
        </div>
      </>
    );
  }

  if (txns.isLoading || categories.isLoading || queue === null) {
    return (
      <>
        <div className="app-head"><div><h1>Review</h1><p>Quickly categorize new transactions.</p></div></div>
        <div className="app-card pf-state">Loading transactions…</div>
      </>
    );
  }

  const done = index >= total;

  return (
    <>
      <div className="app-head">
        <div><h1>Review &amp; categorize</h1><p>Assign a category to each new charge for <b>{currentProfile?.name}</b>.</p></div>
        {total > 0 && !done && <span className="rv-count">{Math.min(index + 1, total)} of {total}</span>}
      </div>

      {total > 0 && (
        <div className="rv-progress" aria-hidden><span style={{ width: `${Math.round((index / total) * 100)}%` }} /></div>
      )}

      {done ? (
        <div className="app-card app-placeholder rv-done">
          <div className="rv-check" aria-hidden>✓</div>
          <h2>{total === 0 ? 'Nothing to review' : "You're all caught up"}</h2>
          <p>{total === 0
            ? 'Every transaction already has a category. Import a statement or add transactions, then come back.'
            : `You categorized ${history.length} transaction${history.length === 1 ? '' : 's'} this session.`}</p>
          <div className="app-placeholder-actions">
            <button type="button" className="app-btn" onClick={() => { setQueue(null); txns.refetch(); }}>Check for more</button>
            <Link className="app-btn primary" to="/app/transactions">View all transactions</Link>
          </div>
        </div>
      ) : current ? (
        <div className="rv-card app-card">
          <div className="rv-charge">
            <div className="rv-charge-meta">
              <span className="rv-acct"><span className="rv-acct-dot" style={{ background: acctById.get(current.account_id)?.color ?? '#8a90a6' }} />{acctById.get(current.account_id)?.display_name ?? 'Account'}</span>
              <span className="rv-date">{formatDay(current.date)}</span>
            </div>
            <div className="rv-merchant">{current.merchant || current.raw_description}</div>
            {current.merchant && current.raw_description !== current.merchant && <div className="rv-raw">{current.raw_description}</div>}
            <div className={`rv-amount ${displayAmount(current) > 0 ? 'pos' : ''}`}>{displayAmount(current) > 0 ? '+' : ''}{formatCad(displayAmount(current))}</div>
          </div>

          <div className="rv-prompt">Pick a category</div>
          <div className="rv-cats" role="group" aria-label="Categories">
            {catList.map((cat: Category, i) => (
              <button
                key={cat.id}
                type="button"
                className="rv-cat"
                style={{ ['--rc' as string]: cat.color }}
                onClick={() => assign(cat.id)}
              >
                <span className="rv-cat-ico" style={{ color: cat.color, background: `color-mix(in srgb, ${cat.color} 16%, transparent)` }}><CategoryIcon name={cat.icon} /></span>
                <span className="rv-cat-name">{cat.name}</span>
                {i < 9 && <span className="rv-cat-key" aria-hidden>{i + 1}</span>}
              </button>
            ))}
          </div>

          <div className="rv-actions">
            <button type="button" className="app-btn" onClick={undo} disabled={history.length === 0}>↩ Undo</button>
            <button type="button" className="app-btn" onClick={skip}>Skip →</button>
            <span className="rv-hint">Tip: press <kbd>1</kbd>–<kbd>9</kbd> to pick, <kbd>S</kbd> to skip, <kbd>U</kbd> to undo</span>
          </div>
        </div>
      ) : null}
    </>
  );
}
