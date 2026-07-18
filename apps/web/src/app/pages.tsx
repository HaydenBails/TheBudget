import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useCurrentProfile } from '../features/profiles/ProfileContext';
import { useAccounts } from '../features/accounts/api';
import { netWorthNow, netWorthTrend, trackedAccounts } from '../features/accounts/netWorth';
import type { NetWorthPoint, NetWorthSummary } from '../features/accounts/netWorth';
import { useCategories } from '../features/categories/api';
import { CategoryIcon } from '../features/categories/CategoryIcon';
import { useTransactions } from '../features/transactions/api';
import { formatCad } from '../features/transactions/money';
import { useBudgets } from '../features/budgets/api';
import { budgetLevel, type BudgetLevel } from '../features/budgets/budgetMath';
import { useRecurringSeries } from '../features/recurring/api';
import { monthlyCostCents, CADENCE_LABEL, type RecurringSeries } from '../features/recurring/types';
import { useIncomeOccurrences } from '../features/income/api';
import type { Transaction, TransactionFilters } from '../features/transactions/types';
import type { Category } from '../features/categories/types';
import type { Account } from '../features/accounts/types';
import type { Budget } from '../features/budgets/types';
import {
  PERIOD_PRESETS,
  computeRange,
  displayAmount,
  formatDay,
  formatDollars,
  isoEnd,
  monthKey,
  monthLabel,
  outflow,
  pad,
  shortMonth,
  ymOf,
} from './period';
import './dashboard.css';

function PageHead({ title, subtitle }: { title: string; subtitle: string }) {
  return <div className="app-head"><div><h1>{title}</h1><p>{subtitle}</p></div></div>;
}

const tooltipStyle = {
  borderRadius: 12,
  border: '1px solid var(--lg-border)',
  background: 'var(--lg-panel)',
  color: 'var(--lg-text)',
  fontSize: 12.5,
  fontWeight: 600,
  boxShadow: 'var(--lg-shadow-card)',
};

export function DashboardPage() {
  const { currentProfileId } = useCurrentProfile();
  const accounts = useAccounts(currentProfileId, false);
  const categories = useCategories(currentProfileId, false);

  const now = new Date();
  const curYM = monthKey(now);
  const [period, setPeriod] = useState('this');

  // Pull all transactions so any period (YTD, all time, a specific month) works.
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
  const isCurrentMonth = period === 'this';

  const budgetsQuery = useBudgets(currentProfileId, curYM);
  const recurringQuery = useRecurringSeries(currentProfileId);
  const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const monthStartISO = `${curYM}-01`;
  const monthEndISO = `${curYM}-${pad(monthEnd.getDate())}`;
  const todayISO = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const incomeOccQuery = useIncomeOccurrences(currentProfileId, monthStartISO, monthEndISO);

  const catById = useMemo(
    () => new Map<number, Category>((categories.data ?? []).map((c) => [c.id, c])),
    [categories.data],
  );
  const acctById = useMemo(
    () => new Map<number, Account>((accounts.data ?? []).map((a) => [a.id, a])),
    [accounts.data],
  );

  const model = useMemo(() => {
    const inRange = (t: Transaction, from: string, to: string) => t.date >= from && t.date <= to;
    const spentIn = (from: string, to: string) =>
      allTx.filter((t) => t.included_in_spending && inRange(t, from, to)).reduce((s, t) => s + outflow(t), 0);

    const spent = spentIn(range.fromISO, range.toISO);
    const prevSpent = range.cmpFromISO ? spentIn(range.cmpFromISO, range.cmpToISO as string) : 0;
    const mom = range.cmpFromISO && prevSpent !== 0 ? (spent - prevSpent) / Math.abs(prevSpent) : 0;

    const inSel = (t: Transaction) => inRange(t, range.fromISO, range.toISO);
    const income = allTx
      .filter((t) => inSel(t) && t.type === 'income')
      .reduce((s, t) => s + Math.abs(t.amount_cents), 0);
    const excluded = allTx
      .filter((t) => inSel(t) && !t.included_in_spending && t.type !== 'income')
      .reduce((s, t) => s + Math.abs(t.amount_cents), 0);

    const catMap = new Map<number, number>();
    for (const t of allTx) {
      if (!t.included_in_spending || !inSel(t) || t.category_id == null) continue;
      catMap.set(t.category_id, (catMap.get(t.category_id) ?? 0) + outflow(t));
    }
    // Category spend in the comparison period, to show what moved up or down.
    const prevCatMap = new Map<number, number>();
    if (range.cmpFromISO) {
      for (const t of allTx) {
        if (!t.included_in_spending || t.category_id == null) continue;
        if (!inRange(t, range.cmpFromISO, range.cmpToISO as string)) continue;
        prevCatMap.set(t.category_id, (prevCatMap.get(t.category_id) ?? 0) + outflow(t));
      }
    }
    const byCategory = [...catMap.entries()]
      .map(([id, cents]) => ({ id, cents, prev: prevCatMap.get(id) ?? 0 }))
      .filter((x) => x.cents > 0)
      .sort((a, b) => b.cents - a.cents);

    // Where the money actually goes: merchant- and account-level spend.
    const merchMap = new Map<string, { cents: number; count: number }>();
    for (const t of allTx) {
      if (!t.included_in_spending || !inSel(t) || outflow(t) <= 0) continue;
      const name = (t.merchant || t.raw_description || 'Unknown').trim() || 'Unknown';
      const cur = merchMap.get(name) ?? { cents: 0, count: 0 };
      cur.cents += outflow(t);
      cur.count += 1;
      merchMap.set(name, cur);
    }
    const byMerchant = [...merchMap.entries()]
      .map(([name, v]) => ({ name, cents: v.cents, count: v.count }))
      .sort((a, b) => b.cents - a.cents)
      .slice(0, 6);

    const acctMap = new Map<number, number>();
    for (const t of allTx) {
      if (!t.included_in_spending || !inSel(t)) continue;
      acctMap.set(t.account_id, (acctMap.get(t.account_id) ?? 0) + outflow(t));
    }
    const byAccount = [...acctMap.entries()]
      .map(([id, cents]) => ({ id, cents }))
      .filter((x) => x.cents > 0)
      .sort((a, b) => b.cents - a.cents);

    // trend: six months ending at the selected period's end month.
    const endD = new Date(`${range.toISO}T00:00:00`);
    const months: string[] = [];
    for (let i = 5; i >= 0; i--) months.push(monthKey(new Date(endD.getFullYear(), endD.getMonth() - i, 1)));
    const trend = months.map((ym) => ({
      ym,
      label: shortMonth(ym),
      cents: Math.max(0, spentIn(`${ym}-01`, isoEnd(new Date(`${ym}-01T00:00:00`)))),
    }));

    const largest = allTx
      .filter((t) => t.included_in_spending && inSel(t) && t.direction === 'debit')
      .sort((a, b) => b.amount_cents - a.amount_cents)
      .slice(0, 4);

    const recent = allTx
      .filter(inSel)
      .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : b.id - a.id))
      .slice(0, 6);

    return { spent, mom, income, excluded, byCategory, byMerchant, byAccount, trend, largest, recent, prevSpent };
  }, [allTx, range]);

  const allAccounts = useMemo(() => accounts.data ?? [], [accounts.data]);
  const netWorth = useMemo(() => netWorthNow(allAccounts), [allAccounts]);
  const nwTrend = useMemo(
    () => netWorthTrend(allAccounts, allTx, 6, now),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [allAccounts, allTx],
  );
  const hasNetWorth = trackedAccounts(allAccounts).length > 0;

  const hasProfile = currentProfileId != null;
  const isEmpty = !txnsQuery.isLoading && !txnsQuery.isError && allTx.length === 0;
  const catTotal = model.byCategory.reduce((s, c) => s + c.cents, 0);

  const tracked = (recurringQuery.data ?? []).filter(
    (s) => s.status === 'keep' || s.status === 'review',
  );
  const recurringMonthly = tracked.reduce((s, r) => s + monthlyCostCents(r), 0);
  const upcoming = [...tracked]
    .sort((a, b) => (a.next_expected_date < b.next_expected_date ? -1 : 1))
    .slice(0, 4);

  // Available to save (§11.2): recorded + still-due income, minus spending and
  // confirmed recurring charges still expected (and not yet posted) this month.
  const expectedRemainingIncome = (incomeOccQuery.data ?? [])
    .filter((o) => o.occurrence_date > todayISO)
    .reduce((s, o) => s + o.amount_cents, 0);
  const recurringDue = tracked
    .filter((s) => s.next_expected_date > todayISO && s.next_expected_date <= monthEndISO)
    .reduce((s, r) => s + r.amount_cents, 0);
  const availableToSave = isCurrentMonth
    ? model.income + expectedRemainingIncome - model.spent - recurringDue
    : model.income - model.spent;
  const availableIsEstimate = isCurrentMonth && (expectedRemainingIncome > 0 || recurringDue > 0);
  const uncategorizedCount = allTx.filter((t) => t.category_id == null && t.deleted_at == null).length;

  // Current-month pacing: extrapolate today's spend to a projected month-end total.
  const dayOfMonth = now.getDate();
  const daysInMonth = monthEnd.getDate();
  const projectedSpend =
    isCurrentMonth && dayOfMonth > 0 ? Math.round((model.spent / dayOfMonth) * daysInMonth) : 0;

  if (!hasProfile) {
    return (
      <>
        <PageHead title="Dashboard" subtitle="Create or select a profile to get started" />
        <section className="app-card app-placeholder">
          <h2>No profile selected</h2>
          <p>Your data is organised per profile. Create one to start tracking spending.</p>
          <div className="app-placeholder-actions">
            <Link className="app-btn primary" to="/app/profiles">Create a profile</Link>
          </div>
        </section>
      </>
    );
  }

  return (
    <>
      <div className="dash-sub">
        <div>
          <h1>Dashboard</h1>
          <p>
            Your money over <b>{range.label}</b> · {allTx.length} transactions ·{' '}
            {accounts.data?.length ?? 0} account{(accounts.data?.length ?? 0) === 1 ? '' : 's'}
          </p>
        </div>
        <div className="dash-period" role="group" aria-label="Dashboard period">
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

      {isEmpty && (
        <section className="app-card app-placeholder">
          <h2>No spending recorded yet</h2>
          <p>Add a transaction by hand or import a statement, and your dashboard fills in automatically.</p>
          <div className="app-placeholder-actions">
            <Link className="app-btn primary" to="/app/transactions">Add a transaction</Link>
            <Link className="app-btn" to="/app/imports">Import a statement</Link>
          </div>
        </section>
      )}

      {!isEmpty && uncategorizedCount > 0 && (
        <Link className="dash-nudge" to="/app/review">
          <span className="dash-nudge-ico" aria-hidden>✓</span>
          <span className="dash-nudge-text">
            <b>{uncategorizedCount} transaction{uncategorizedCount === 1 ? '' : 's'}</b> need a category
          </span>
          <span className="dash-nudge-cta">Review now →</span>
        </Link>
      )}

      {!isEmpty && (
        <>
          {/* metric row */}
          <section className="dash-metrics" aria-label={`Spending over ${range.label}`}>
            <div className="dash-hero">
              <span className="dash-hero-k">Spent {isCurrentMonth ? 'this month' : range.label}</span>
              <div className="dash-hero-main">
                <span className="dash-hero-v">{formatDollars(model.spent)}</span>
                {range.cmpFromISO && model.prevSpent > 0 && (
                  <span className={`dash-delta ${model.mom > 0 ? 'up' : 'down'}`}>
                    {model.mom > 0 ? '▲' : '▼'} {Math.abs(model.mom * 100).toFixed(1)}%
                  </span>
                )}
              </div>
              <span className="dash-hero-foot">
                {range.cmpFromISO && model.prevSpent > 0 ? `vs ${formatDollars(model.prevSpent)} (${range.cmpLabel}) · ` : ''}
                {formatDollars(model.income)} income
              </span>
              {isCurrentMonth && model.spent > 0 && dayOfMonth < daysInMonth && (
                <span className="dash-hero-pace">
                  On pace for ~{formatDollars(projectedSpend)} by month-end
                </span>
              )}
            </div>
            <StatCard
              icon="↑"
              label={availableIsEstimate ? 'Available to save (est.)' : 'Available to save'}
              value={formatDollars(availableToSave)}
              foot={availableIsEstimate ? 'Income + due − spend − recurring' : 'Income − spending'}
              tone={availableToSave < 0 ? 'neg' : 'accent'}
            />
            <StatCard icon="◈" label="Income" value={formatDollars(model.income)} foot={isCurrentMonth ? 'This month' : range.label} />
            <StatCard
              icon="↻"
              label="Recurring / mo"
              value={tracked.length > 0 ? formatDollars(recurringMonthly) : '—'}
              foot={tracked.length > 0 ? `${tracked.length} subscription${tracked.length === 1 ? '' : 's'}` : 'None detected yet'}
              muted={tracked.length === 0}
            />
            <StatCard icon="⊘" label="Excluded activity" value={formatDollars(model.excluded)} foot="Payments · fees · transfers" />
          </section>

          {hasNetWorth && <NetWorthCard summary={netWorth} trend={nwTrend} />}

          {/* trend + category */}
          <section className="dash-grid-2">
            <Card title="Spending over time" meta={`${model.trend[0].label} – ${model.trend[model.trend.length - 1].label}`}>
              <ResponsiveContainer width="100%" height={230}>
                <AreaChart data={model.trend} margin={{ top: 8, right: 6, left: 6, bottom: 0 }}>
                  <defs>
                    <linearGradient id="dash-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--mrd-accent)" stopOpacity={0.34} />
                      <stop offset="100%" stopColor="var(--mrd-accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: 'var(--lg-faint)' }} />
                  <YAxis hide />
                  <Tooltip formatter={(v: number) => [formatDollars(v), 'Spent']} contentStyle={tooltipStyle} cursor={{ stroke: 'var(--mrd-accent)', strokeDasharray: '4 4' }} />
                  <Area type="monotone" dataKey="cents" stroke="var(--mrd-accent)" strokeWidth={3} fill="url(#dash-grad)" />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            <Card title="By category" meta={`${model.byCategory.length} categories`}>
              <div className="dash-donut-wrap">
                <div className="dash-donut">
                  <ResponsiveContainer width="100%" height={168}>
                    <PieChart>
                      <Pie data={model.byCategory} dataKey="cents" nameKey="id" innerRadius={56} outerRadius={80} paddingAngle={2} strokeWidth={0}>
                        {model.byCategory.map((c) => (
                          <Cell key={c.id} fill={catById.get(c.id)?.color ?? '#8a90a6'} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number, _n, p) => [formatDollars(v), catById.get(Number(p?.payload?.id))?.name ?? 'Category']} contentStyle={tooltipStyle} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="dash-donut-center"><span>{formatDollars(catTotal)}</span><small>total</small></div>
                </div>
                <ul className="dash-legend">
                  {model.byCategory.slice(0, 5).map((c) => {
                    const cat = catById.get(c.id);
                    const delta = range.cmpFromISO && c.prev > 0 ? (c.cents - c.prev) / c.prev : null;
                    return (
                      <li key={c.id}>
                        <span className="dash-dot" style={{ background: cat?.color ?? '#8a90a6' }} />
                        <span className="dash-legend-name">{cat?.name ?? 'Uncategorised'}</span>
                        {delta != null && Math.abs(delta) >= 0.01 && (
                          <span className={`dash-legend-delta ${delta > 0 ? 'up' : 'down'}`}>
                            {delta > 0 ? '▲' : '▼'}{Math.abs(delta * 100).toFixed(0)}%
                          </span>
                        )}
                        <b>{formatDollars(c.cents)}</b>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </Card>
          </section>

          {/* where the money goes: merchants + accounts */}
          <section className="dash-grid-2">
            <TopMerchantsCard merchants={model.byMerchant} total={model.spent} />
            <ByAccountCard accounts={model.byAccount} total={model.spent} acctById={acctById} />
          </section>

          {/* budgets (real) + recurring (placeholder) + largest (real) */}
          <section className="dash-grid-3">
            <BudgetCard
              budgets={budgetsQuery.data ?? []}
              overallSpent={model.spent}
              spentByCategory={model.byCategory}
              catById={catById}
            />
            <UpcomingRecurringCard upcoming={upcoming} catById={catById} />

            <Card title="Largest purchases" meta={range.label}>
              {model.largest.length === 0 ? (
                <p className="dash-empty">No purchases in this period.</p>
              ) : (
                <ul className="dash-rows">
                  {model.largest.map((t) => <TxRow key={t.id} t={t} category={t.category_id != null ? catById.get(t.category_id) : undefined} />)}
                </ul>
              )}
            </Card>
          </section>

          {/* recent transactions table */}
          <section className="app-card dash-tablecard">
            <div className="dash-card-head"><h2>Recent transactions</h2><Link className="dash-card-link" to="/app/transactions">View all</Link></div>
            <div className="dash-tablewrap">
              <table className="dash-table">
                <thead><tr><th>Date</th><th>Merchant</th><th>Account</th><th>Category</th><th className="num">Amount</th></tr></thead>
                <tbody>
                  {model.recent.map((t) => {
                    const cat = t.category_id != null ? catById.get(t.category_id) : undefined;
                    const acct = acctById.get(t.account_id);
                    const disp = displayAmount(t);
                    return (
                      <tr key={t.id} className={t.included_in_spending ? '' : 'excl'}>
                        <td className="muted">{formatDay(t.date)}</td>
                        <td><div className="dash-merch"><b>{t.merchant || t.raw_description}</b><small>{t.raw_description}</small></div></td>
                        <td className="muted"><span className="dash-acct"><span className="dash-acct-dot" style={{ background: acct?.color ?? '#8a90a6' }} />{acct?.display_name ?? '—'}</span></td>
                        <td>{cat ? <span className="dash-pill" style={{ color: cat.color, background: `color-mix(in srgb, ${cat.color} 15%, transparent)` }}><CategoryIcon name={cat.icon} /> {cat.name}</span> : <span className="dash-pill none">Uncategorised</span>}</td>
                        <td className={`num ${disp > 0 ? 'pos' : ''}`}>{disp > 0 ? '+' : ''}{formatCad(disp)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}

function TopMerchantsCard({
  merchants,
  total,
}: {
  merchants: { name: string; cents: number; count: number }[];
  total: number;
}) {
  const max = merchants.length > 0 ? merchants[0].cents : 0;
  return (
    <Card title="Top merchants" meta={<Link className="dash-card-link" to="/app/merchants">View all</Link>}>
      {merchants.length === 0 ? (
        <p className="dash-empty">No spending in this period.</p>
      ) : (
        <ul className="dash-merchants">
          {merchants.map((m) => {
            const share = total > 0 ? Math.round((m.cents / total) * 100) : 0;
            return (
              <li key={m.name} className="dash-merchant">
                <div className="dash-merchant-top">
                  <span className="dash-merchant-name" title={m.name}>{m.name}</span>
                  <b className="dash-merchant-amt">{formatDollars(m.cents)}</b>
                </div>
                <div className="dash-merchant-bar">
                  <span style={{ width: `${max > 0 ? (m.cents / max) * 100 : 0}%` }} />
                </div>
                <span className="dash-merchant-sub">{m.count} transaction{m.count === 1 ? '' : 's'} · {share}% of spend</span>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

function ByAccountCard({
  accounts,
  total,
  acctById,
}: {
  accounts: { id: number; cents: number }[];
  total: number;
  acctById: Map<number, Account>;
}) {
  return (
    <Card title="Spending by account" meta={accounts.length > 0 ? `${accounts.length} account${accounts.length === 1 ? '' : 's'}` : undefined}>
      {accounts.length === 0 ? (
        <p className="dash-empty">No spending in this period.</p>
      ) : (
        <ul className="dash-accounts">
          {accounts.map((a) => {
            const acct = acctById.get(a.id);
            const color = acct?.color ?? '#8a90a6';
            const share = total > 0 ? Math.round((a.cents / total) * 100) : 0;
            return (
              <li key={a.id} className="dash-account">
                <div className="dash-account-top">
                  <span className="dash-account-name">
                    <span className="dash-acct-dot" style={{ background: color }} />
                    {acct?.display_name ?? 'Unknown account'}
                  </span>
                  <b className="dash-account-amt">{formatDollars(a.cents)}</b>
                </div>
                <div className="dash-account-bar">
                  <span style={{ width: `${total > 0 ? (a.cents / total) * 100 : 0}%`, background: color }} />
                </div>
                <span className="dash-account-sub">{share}% of spend</span>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

function NetWorthCard({ summary, trend }: { summary: NetWorthSummary; trend: NetWorthPoint[] }) {
  const first = trend.length > 0 ? trend[0].cents : summary.net;
  const change = summary.net - first;
  const changePct = first !== 0 ? (change / Math.abs(first)) * 100 : 0;
  const showChange = trend.length > 1 && first !== summary.net;
  return (
    <section className="app-card dash-networth" aria-label="Net worth">
      <div className="dash-nw-left">
        <span className="dash-card-meta">Net worth</span>
        <div className="dash-nw-main">
          <span className={`dash-nw-v ${summary.net < 0 ? 'neg' : ''}`}>{formatDollars(summary.net)}</span>
          {showChange && (
            <span className={`dash-nw-delta ${change >= 0 ? 'pos' : 'neg'}`}>
              {change >= 0 ? '▲' : '▼'} {formatDollars(Math.abs(change))}
              {first !== 0 ? ` (${Math.abs(changePct).toFixed(1)}%)` : ''}
            </span>
          )}
        </div>
        <div className="dash-nw-breakdown">
          <span className="dash-nw-chip asset">
            <small>Assets</small>
            <b>{formatDollars(summary.assets)}</b>
          </span>
          <span className="dash-nw-chip liab">
            <small>Liabilities</small>
            <b>{formatDollars(summary.liabilities)}</b>
          </span>
          <Link className="dash-card-link dash-nw-manage" to="/app/accounts">Update balances →</Link>
        </div>
      </div>
      {trend.length > 1 && (
        <div className="dash-nw-chart">
          <ResponsiveContainer width="100%" height={96}>
            <AreaChart data={trend} margin={{ top: 6, right: 4, left: 4, bottom: 0 }}>
              <defs>
                <linearGradient id="dash-nw-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--mrd-accent)" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="var(--mrd-accent)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: 'var(--lg-faint)' }} />
              <YAxis hide domain={['auto', 'auto']} />
              <Tooltip formatter={(v: number) => [formatDollars(v), 'Net worth']} contentStyle={tooltipStyle} cursor={{ stroke: 'var(--mrd-accent)', strokeDasharray: '4 4' }} />
              <Area type="monotone" dataKey="cents" stroke="var(--mrd-accent)" strokeWidth={2.5} fill="url(#dash-nw-grad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

const budgetBarClass: Record<BudgetLevel, string> = { ok: 'ok', warn: 'warn', high: 'high', over: 'over' };

function DashBudgetBar({ name, color, spent, limit }: { name: string; color?: string; spent: number; limit: number }) {
  const level = budgetLevel(spent, limit);
  const pct = limit > 0 ? Math.min(100, Math.max(0, (spent / limit) * 100)) : 0;
  const pctLabel = limit > 0 ? Math.round((spent / limit) * 100) : 0;
  return (
    <li className="dash-budget">
      <div className="dash-budget-top">
        <span className="dash-budget-name">{color && <span className="dash-dot" style={{ background: color }} />}{name}</span>
        <span className="dash-budget-num">{formatDollars(spent)} / {formatDollars(limit)}</span>
      </div>
      <div className={`dash-budget-bar ${budgetBarClass[level]}`} role="progressbar" aria-valuenow={pctLabel} aria-valuemin={0} aria-valuemax={100} aria-label={`${name}: ${pctLabel}% of budget used`}>
        <span style={{ width: `${pct}%` }} />
      </div>
    </li>
  );
}

function BudgetCard({
  budgets,
  overallSpent,
  spentByCategory,
  catById,
}: {
  budgets: Budget[];
  overallSpent: number;
  spentByCategory: { id: number; cents: number }[];
  catById: Map<number, Category>;
}) {
  const spentMap = new Map(spentByCategory.map((c) => [c.id, c.cents]));
  const overall = budgets.find((b) => b.category_id == null);
  const categoryBudgets = budgets
    .filter((b) => b.category_id != null)
    .map((b) => {
      const spent = spentMap.get(b.category_id as number) ?? 0;
      return { budget: b, spent, ratio: b.limit_cents > 0 ? spent / b.limit_cents : 0 };
    })
    .sort((a, b) => b.ratio - a.ratio)
    .slice(0, 4);

  if (!overall && categoryBudgets.length === 0) {
    return (
      <Card title="Category budgets" meta="Not set up">
        <div className="dash-mini-empty">
          <p>Set monthly limits and track your progress against them here.</p>
          <Link className="app-btn primary" to="/app/budgets">Set budgets</Link>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Budgets" meta={<Link className="dash-card-link" to="/app/budgets">Manage</Link>}>
      <ul className="dash-budget-list">
        {overall && <DashBudgetBar name="All spending" spent={overallSpent} limit={overall.limit_cents} />}
        {categoryBudgets.map(({ budget, spent }) => {
          const cat = catById.get(budget.category_id as number);
          return <DashBudgetBar key={budget.id} name={cat?.name ?? 'Category'} color={cat?.color} spent={spent} limit={budget.limit_cents} />;
        })}
      </ul>
    </Card>
  );
}

function UpcomingRecurringCard({
  upcoming,
  catById,
}: {
  upcoming: RecurringSeries[];
  catById: Map<number, Category>;
}) {
  if (upcoming.length === 0) {
    return (
      <Card title="Upcoming recurring" meta="Not set up">
        <div className="dash-mini-empty">
          <p>Detect subscriptions and repeating charges from your transactions to see what's due next.</p>
          <Link className="app-btn primary" to="/app/recurring">Detect recurring</Link>
        </div>
      </Card>
    );
  }
  return (
    <Card title="Upcoming recurring" meta={<Link className="dash-card-link" to="/app/recurring">Manage</Link>}>
      <ul className="dash-rows">
        {upcoming.map((s) => {
          const cat = s.category_id != null ? catById.get(s.category_id) : undefined;
          const color = cat?.color ?? '#8a90a6';
          return (
            <li key={s.id} className="dash-txrow">
              <span className="dash-caticon sm" style={{ color, background: `color-mix(in srgb, ${color} 16%, transparent)` }}>
                <CategoryIcon name={cat?.icon} />
              </span>
              <div className="dash-txmeta">
                <div className="dash-txname">{s.display_name}</div>
                <div className="dash-txsub">{CADENCE_LABEL[s.cadence]} · next {formatDay(s.next_expected_date)}</div>
              </div>
              <span className="dash-txamt">{formatCad(s.amount_cents)}</span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function StatCard({ icon, label, value, foot, tone, muted }: { icon: string; label: string; value: string; foot: string; tone?: 'accent' | 'neg'; muted?: boolean }) {
  return (
    <div className={`dash-stat ${muted ? 'muted' : ''}`}>
      <span className={`dash-stat-ico ${tone ?? ''}`} aria-hidden>{icon}</span>
      <span className="dash-stat-k">{label}</span>
      <span className={`dash-stat-v ${tone === 'neg' ? 'neg' : ''}`}>{value}</span>
      <span className="dash-stat-foot">{foot}</span>
    </div>
  );
}

function Card({ title, meta, children }: { title: string; meta?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="app-card dash-card">
      <div className="dash-card-head"><h2>{title}</h2>{meta && <span className="dash-card-meta">{meta}</span>}</div>
      {children}
    </div>
  );
}

function TxRow({ t, category }: { t: Transaction; category?: Category }) {
  const disp = displayAmount(t);
  const color = category?.color ?? '#8a90a6';
  return (
    <li className="dash-txrow">
      <span className="dash-caticon sm" style={{ color, background: `color-mix(in srgb, ${color} 16%, transparent)` }}>
        <CategoryIcon name={category?.icon} />
      </span>
      <div className="dash-txmeta">
        <div className="dash-txname">{t.merchant || t.raw_description}</div>
        <div className="dash-txsub">{formatDay(t.date)} · {category?.name ?? 'Uncategorised'}</div>
      </div>
      <span className={`dash-txamt ${disp > 0 ? 'pos' : ''}`}>{disp > 0 ? '+' : ''}{formatCad(disp)}</span>
    </li>
  );
}

export function SettingsPage() {
  return (
    <>
      <PageHead title="Settings" subtitle="Local, private, and stored on your machine." />
      <section className="app-card" aria-labelledby="privacy-title">
        <h2 id="privacy-title">Privacy and appearance</h2>
        <p className="app-settings-copy">Meridian runs on <b>127.0.0.1</b> and stores application data in a local SQLite database. There is no login or cloud sync. Use the theme control in the top bar to switch appearance; that choice is remembered in this browser.</p>
      </section>
    </>
  );
}
