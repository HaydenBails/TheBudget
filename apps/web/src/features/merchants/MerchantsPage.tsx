import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  PERIOD_PRESETS,
  computeRange,
  formatDay,
  formatDollars,
  monthLabel,
  outflow,
  ymOf,
} from '../../app/period';
import { formatCad } from '../transactions/money';
import { useCurrentProfile } from '../profiles/ProfileContext';
import { useCategories } from '../categories/api';
import { CategoryIcon } from '../categories/CategoryIcon';
import { useTransactions } from '../transactions/api';
import type { Category } from '../categories/types';
import type { Transaction, TransactionFilters } from '../transactions/types';
import './merchants.css';

interface MerchantRow {
  name: string;
  cents: number;
  count: number;
  categoryId: number | null;
  firstDate: string;
  lastDate: string;
}

export function MerchantsPage() {
  const { currentProfileId } = useCurrentProfile();
  const categories = useCategories(currentProfileId, false);

  const now = new Date();
  const [period, setPeriod] = useState('this');
  const [search, setSearch] = useState('');

  const filters = useMemo<TransactionFilters>(() => ({
    accountId: null,
    categoryId: null,
    type: null,
    dateFrom: '',
    dateTo: '',
    includedInSpending: null,
    search: '',
    includeDeleted: false,
  }), []);
  const txnsQuery = useTransactions(currentProfileId, filters);
  const allTx = txnsQuery.data ?? [];

  const availableMonths = useMemo(() => {
    const set = new Set(allTx.map((t) => ymOf(t.date)));
    return [...set].sort().reverse();
  }, [allTx]);
  const dateBounds = useMemo(() => {
    if (allTx.length === 0) return { min: '', max: '' };
    const dates = allTx.map((t) => t.date);
    return { min: dates.reduce((a, b) => (a < b ? a : b)), max: dates.reduce((a, b) => (a > b ? a : b)) };
  }, [allTx]);
  const range = useMemo(
    () => computeRange(period, now, dateBounds.min, dateBounds.max),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [period, dateBounds.min, dateBounds.max],
  );

  const catById = useMemo(
    () => new Map<number, Category>((categories.data ?? []).map((c) => [c.id, c])),
    [categories.data],
  );

  const rows = useMemo(() => {
    const inRange = (t: Transaction) => t.date >= range.fromISO && t.date <= range.toISO;
    const agg = new Map<string, { cents: number; count: number; catCounts: Map<number, number>; first: string; last: string }>();
    for (const t of allTx) {
      if (!t.included_in_spending || !inRange(t) || outflow(t) <= 0) continue;
      const name = (t.merchant || t.raw_description || 'Unknown').trim() || 'Unknown';
      const cur = agg.get(name) ?? { cents: 0, count: 0, catCounts: new Map<number, number>(), first: t.date, last: t.date };
      cur.cents += outflow(t);
      cur.count += 1;
      if (t.date < cur.first) cur.first = t.date;
      if (t.date > cur.last) cur.last = t.date;
      if (t.category_id != null) cur.catCounts.set(t.category_id, (cur.catCounts.get(t.category_id) ?? 0) + 1);
      agg.set(name, cur);
    }
    const list: MerchantRow[] = [...agg.entries()].map(([name, v]) => {
      let categoryId: number | null = null;
      let best = 0;
      for (const [id, c] of v.catCounts) {
        if (c > best) { best = c; categoryId = id; }
      }
      return { name, cents: v.cents, count: v.count, categoryId, firstDate: v.first, lastDate: v.last };
    });
    return list.sort((a, b) => b.cents - a.cents);
  }, [allTx, range]);

  const totalSpend = rows.reduce((s, r) => s + r.cents, 0);
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? rows.filter((r) => r.name.toLowerCase().includes(q)) : rows;
  }, [rows, search]);
  const maxCents = rows.length > 0 ? rows[0].cents : 0;

  const hasProfile = currentProfileId != null;
  const isEmpty = !txnsQuery.isLoading && !txnsQuery.isError && rows.length === 0;

  if (!hasProfile) {
    return (
      <>
        <div className="app-head"><div><h1>Merchants</h1><p>See who you spend the most with.</p></div></div>
        <section className="app-card app-placeholder">
          <h2>No profile selected</h2>
          <p>Merchant spending is tracked per profile. Create or select one to get started.</p>
          <Link className="app-btn primary" to="/app/profiles" style={{ marginTop: 14 }}>Go to profiles</Link>
        </section>
      </>
    );
  }

  return (
    <>
      <div className="dash-sub">
        <div>
          <h1>Merchants</h1>
          <p>Who you spend the most with over <b>{range.label}</b> · {rows.length} merchant{rows.length === 1 ? '' : 's'}</p>
        </div>
        <div className="dash-period" role="group" aria-label="Period">
          {PERIOD_PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              className={`dash-period-btn ${period === p.id ? 'active' : ''}`}
              aria-pressed={period === p.id}
              onClick={() => setPeriod(p.id)}
            >
              {p.label}
            </button>
          ))}
          <select
            className="dash-period-select"
            aria-label="Pick a specific month"
            value={availableMonths.includes(period) ? period : ''}
            onChange={(e) => e.target.value && setPeriod(e.target.value)}
          >
            <option value="">Month…</option>
            {availableMonths.map((ym) => (
              <option key={ym} value={ym}>{monthLabel(ym)}</option>
            ))}
          </select>
        </div>
      </div>

      {txnsQuery.isLoading && <div className="app-card pf-state">Loading merchants…</div>}

      {isEmpty && (
        <section className="app-card app-placeholder">
          <h2>No spending in this period</h2>
          <p>Pick a different period, or add transactions to see where your money goes.</p>
          <div className="app-placeholder-actions">
            <Link className="app-btn primary" to="/app/transactions">Add a transaction</Link>
            <Link className="app-btn" to="/app/imports">Import a statement</Link>
          </div>
        </section>
      )}

      {!isEmpty && !txnsQuery.isLoading && (
        <>
          <section className="mch-summary" aria-label="Merchant summary">
            <div className="mch-stat">
              <span className="mch-stat-k">Total spent</span>
              <span className="mch-stat-v">{formatDollars(totalSpend)}</span>
            </div>
            <div className="mch-stat">
              <span className="mch-stat-k">Merchants</span>
              <span className="mch-stat-v">{rows.length}</span>
            </div>
            <div className="mch-stat">
              <span className="mch-stat-k">Top merchant</span>
              <span className="mch-stat-v">{rows[0].name}</span>
              <span className="mch-stat-foot">{formatDollars(rows[0].cents)} · {Math.round((rows[0].cents / totalSpend) * 100)}% of spend</span>
            </div>
          </section>

          <section className="app-card mch-tablecard">
            <div className="mch-toolbar">
              <h2>Top merchants by spend</h2>
              <input
                type="search"
                className="pf-input mch-search"
                placeholder="Filter merchants…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Filter merchants by name"
              />
            </div>
            <div className="mch-tablewrap">
              <table className="mch-table">
                <thead>
                  <tr>
                    <th className="mch-rank">#</th>
                    <th>Merchant</th>
                    <th>Category</th>
                    <th className="num">Txns</th>
                    <th className="num">Avg</th>
                    <th className="num">Share</th>
                    <th className="num">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r, i) => {
                    const cat = r.categoryId != null ? catById.get(r.categoryId) : undefined;
                    const share = totalSpend > 0 ? (r.cents / totalSpend) * 100 : 0;
                    return (
                      <tr key={r.name}>
                        <td className="mch-rank muted">{search ? '' : i + 1}</td>
                        <td>
                          <div className="mch-merch">
                            <Link
                              className="mch-merch-link"
                              to={`/app/transactions?q=${encodeURIComponent(r.name)}`}
                              title={`View ${r.name} transactions`}
                            >
                              {r.name}
                            </Link>
                            <div className="mch-bar" aria-hidden>
                              <span style={{ width: `${maxCents > 0 ? (r.cents / maxCents) * 100 : 0}%` }} />
                            </div>
                            <small>{formatDay(r.firstDate)}{r.firstDate !== r.lastDate ? ` – ${formatDay(r.lastDate)}` : ''}</small>
                          </div>
                        </td>
                        <td>
                          {cat ? (
                            <span className="mch-pill" style={{ color: cat.color, background: `color-mix(in srgb, ${cat.color} 15%, transparent)` }}>
                              <CategoryIcon name={cat.icon} /> {cat.name}
                            </span>
                          ) : (
                            <span className="mch-pill none">Uncategorised</span>
                          )}
                        </td>
                        <td className="num muted">{r.count}</td>
                        <td className="num muted">{formatCad(Math.round(r.cents / r.count))}</td>
                        <td className="num muted">{share.toFixed(1)}%</td>
                        <td className="num mch-total">{formatCad(r.cents)}</td>
                      </tr>
                    );
                  })}
                  {filtered.length === 0 && (
                    <tr><td colSpan={7} className="mch-noresult">No merchants match “{search}”.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}
