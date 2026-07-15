import { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Direction } from '../types';
import {
  CURRENT_YM,
  PREV_YM,
  availableToSaveCents,
  categoryBudgetProgress,
  excludedActivityCents,
  incomeThisMonthCents,
  largestPurchases,
  monthOverMonthChange,
  monthlyTrend,
  overallBudgetCents,
  recentTransactions,
  reviewQueue,
  spendingByCategory,
  totalSpendingCents,
  upcomingRecurringCents,
} from '../../lib/derived';
import {
  accountById,
  categories,
  categoryById,
  profile,
  recurringSeries,
  transactions as allTxns,
} from '../../lib/mockData';
import type { Transaction } from '../../lib/types';
import {
  formatCents,
  formatCentsAbs,
  formatDollarsAbs,
  formatMonthLabel,
  formatShortDate,
  formatSignedPct,
} from '../../lib/format';
import './ledger.css';

const MONTH_LABEL = formatMonthLabel(CURRENT_YM + '-01');

const NAV: { icon: string; label: string; active?: boolean }[] = [
  { icon: '▚', label: 'Dashboard' },
  { icon: '≣', label: 'Transactions' },
  { icon: '⤒', label: 'Import' },
  { icon: '✓', label: 'Review' },
  { icon: '↻', label: 'Recurring' },
  { icon: '▤', label: 'Budgets' },
  { icon: '$', label: 'Income' },
  { icon: '◨', label: 'Reports' },
];

function NavBar({ active }: { active: string }) {
  return (
    <nav className="lg-nav" aria-label="Primary">
      <div className="lg-brand">
        <span className="lg-brand-dot" aria-hidden />
        LEDGER
      </div>
      <div className="lg-tabs">
        {NAV.map((n) => (
          <button
            key={n.label}
            type="button"
            className={`lg-tab ${n.label === active ? 'active' : ''}`}
            aria-current={n.label === active ? 'page' : undefined}
          >
            <span className="lg-tab-ico" aria-hidden>
              {n.icon}
            </span>
            {n.label}
          </button>
        ))}
      </div>
      <div className="lg-nav-right">
        <span className="lg-nav-clock" aria-hidden>
          {MONTH_LABEL.toUpperCase()} · CAD
        </span>
        <span className="lg-nav-user">
          <span className="lg-nav-avatar" aria-hidden>
            {profile.initials}
          </span>
          {profile.name}
        </span>
      </div>
    </nav>
  );
}

function SubHeader({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="lg-sub">
      <span className="lg-sub-title">{title}</span>
      <span className="lg-sub-meta">{children}</span>
      <div className="lg-sub-right">
        <button type="button" className="lg-chip">
          <span className="lg-chip-k">ACCT</span> All accounts ▾
        </button>
        <button type="button" className="lg-chip">
          <span className="lg-chip-k">PER</span> {MONTH_LABEL} ▾
        </button>
      </div>
    </div>
  );
}

function Chrome({
  active,
  title,
  meta,
  children,
}: {
  active: string;
  title: string;
  meta?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="lg">
      <NavBar active={active} />
      <SubHeader title={title}>{meta}</SubHeader>
      {children}
    </div>
  );
}

const chartTooltip = {
  borderRadius: 8,
  border: '1px solid var(--lg-border-strong)',
  background: 'var(--lg-panel)',
  color: 'var(--lg-text)',
  fontSize: 12,
  fontFamily: 'var(--lg-mono)',
  boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
};

/* ======================================================= DASHBOARD ==== */

function Dashboard() {
  const spend = totalSpendingCents(CURRENT_YM);
  const prevSpend = totalSpendingCents(PREV_YM);
  const mom = monthOverMonthChange();
  const income = incomeThisMonthCents();
  const save = availableToSaveCents();
  const budget = overallBudgetCents();
  const upcomingCents = upcomingRecurringCents();
  const excluded = excludedActivityCents(CURRENT_YM);

  const catData = spendingByCategory(CURRENT_YM);
  const trend = monthlyTrend();
  const budgetPct = budget ? spend / budget : 0;
  const budgetOver = budgetPct > 1;

  const budgetRows = categoryBudgetProgress(CURRENT_YM);
  const recent = recentTransactions(7);
  const largest = largestPurchases(CURRENT_YM, 5);

  // Upcoming recurring charges (kept series), soonest first.
  const upcoming = [...recurringSeries]
    .filter((r) => r.status !== 'ended' && r.status !== 'ignored')
    .sort((a, b) => a.nextExpectedDate.localeCompare(b.nextExpectedDate))
    .slice(0, 5);

  return (
    <Chrome
      active="Dashboard"
      title="Dashboard"
      meta={
        <>
          Overview for <b>{MONTH_LABEL}</b> · {allTxns.length} transactions · 2 accounts
        </>
      }
    >
      <div className="lg-page">
        {/* metric strip */}
        <section className="lg-strip" aria-label="Key metrics">
          <div className="lg-stat lg-stat-hero">
            <span className="lg-stat-k">◇ Spent this month</span>
            <span className="lg-stat-v">{formatDollarsAbs(spend)}</span>
            <span className="lg-stat-foot">
              <span className={`lg-delta ${mom > 0 ? 'up' : 'down'}`}>
                {mom > 0 ? '▲' : '▼'} {formatSignedPct(mom)}
              </span>
              vs {formatDollarsAbs(prevSpend)} in Jun
            </span>
          </div>
          <div className="lg-stat">
            <span className="lg-stat-k">$ Income (est.)</span>
            <span className="lg-stat-v">{formatDollarsAbs(income)}</span>
            <span className="lg-stat-foot">Recorded + expected</span>
          </div>
          <div className="lg-stat">
            <span className="lg-stat-k">↑ Available to save</span>
            <span className="lg-stat-v" style={{ color: save < 0 ? 'var(--lg-neg)' : undefined }}>
              {formatDollarsAbs(save)}
            </span>
            <span className="lg-stat-foot">After spend + recurring</span>
          </div>
          <div className="lg-stat">
            <span className="lg-stat-k">▤ Overall budget</span>
            <span className="lg-stat-v" style={{ color: budgetOver ? 'var(--lg-neg)' : undefined }}>
              {Math.round(budgetPct * 100)}%
            </span>
            <div className="lg-meter">
              <span
                style={{
                  width: `${Math.min(budgetPct, 1) * 100}%`,
                  background: budgetPct > 0.9 ? 'var(--lg-neg)' : 'var(--lg-accent)',
                }}
              />
            </div>
            <span className="lg-stat-foot">
              {formatDollarsAbs(spend)} / {formatDollarsAbs(budget)}
            </span>
          </div>
          <div className="lg-stat">
            <span className="lg-stat-k">↻ Upcoming recurring</span>
            <span className="lg-stat-v">{formatDollarsAbs(upcomingCents)}</span>
            <span className="lg-stat-foot">Due before month end</span>
          </div>
          <div className="lg-stat">
            <span className="lg-stat-k">⊘ Excluded activity</span>
            <span className="lg-stat-v">{formatDollarsAbs(excluded)}</span>
            <span className="lg-stat-foot">Payments, fees, transfers</span>
          </div>
        </section>

        {/* trend + category mix */}
        <section className="lg-grid c-2-1">
          <div className="lg-panel">
            <div className="lg-phead">
              <h3>Spending over time</h3>
              <span className="lg-phead-sub">Apr — Jul</span>
            </div>
            <div className="lg-chart">
              <ResponsiveContainer width="100%" height={216}>
                <AreaChart data={trend} margin={{ top: 8, right: 12, left: 6, bottom: 0 }}>
                  <defs>
                    <linearGradient id="lg-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--lg-grid)" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tickLine={false}
                    axisLine={{ stroke: 'var(--lg-border)' }}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    width={54}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fontFamily: 'var(--lg-mono)' }}
                    tickFormatter={(v: number) => formatDollarsAbs(v)}
                  />
                  <Tooltip
                    cursor={{ stroke: 'var(--lg-accent)', strokeWidth: 1, strokeDasharray: '3 3' }}
                    formatter={(v: number) => [formatDollarsAbs(v), 'Spent']}
                    contentStyle={chartTooltip}
                  />
                  <Area
                    type="monotone"
                    dataKey="cents"
                    stroke="#0ea5e9"
                    strokeWidth={2.5}
                    fill="url(#lg-grad)"
                    dot={{ r: 3, fill: '#0ea5e9', strokeWidth: 0 }}
                    activeDot={{ r: 5 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="lg-panel">
            <div className="lg-phead">
              <h3>Category mix</h3>
              <span className="lg-phead-sub">{formatDollarsAbs(spend)}</span>
            </div>
            <div className="lg-pbody">
              <div className="lg-donut-wrap">
                <div className="lg-donut-center">
                  <ResponsiveContainer width="100%" height={150}>
                    <PieChart>
                      <Pie
                        data={catData}
                        dataKey="cents"
                        nameKey="name"
                        innerRadius={46}
                        outerRadius={68}
                        paddingAngle={2}
                        strokeWidth={0}
                      >
                        {catData.map((c) => (
                          <Cell key={c.categoryId} fill={c.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(v: number, n) => [formatDollarsAbs(v), n as string]}
                        contentStyle={chartTooltip}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="lg-donut-label">
                    <small>Categories</small>
                    <b>{catData.length}</b>
                  </div>
                </div>
                <ul className="lg-mixlist">
                  {catData.slice(0, 6).map((c) => (
                    <li key={c.categoryId} className="lg-mixrow">
                      <span className="lg-dot" style={{ background: c.color }} aria-hidden />
                      <span className="lg-mixname">
                        <span aria-hidden>{c.icon}</span> {c.name}{' '}
                        <em>{Math.round((c.cents / spend) * 100)}%</em>
                      </span>
                      <span className="lg-mixamt">{formatDollarsAbs(c.cents)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* budgets + recurring + largest */}
        <section className="lg-grid c-3">
          <div className="lg-panel">
            <div className="lg-phead">
              <h3>Category budgets</h3>
              <span className="lg-phead-sub">{budgetRows.length} tracked</span>
            </div>
            <ul className="lg-catlist">
              {budgetRows.map((b) => {
                const over = b.pct > 1;
                return (
                  <li key={b.categoryId} className="lg-catrow">
                    <span className="lg-catico" aria-hidden>
                      {b.icon}
                    </span>
                    <div className="lg-catmid">
                      <div className="lg-catname">{b.name}</div>
                      <div className="lg-catbar">
                        <span
                          style={{
                            width: `${Math.min(b.pct, 1) * 100}%`,
                            background: over ? 'var(--lg-neg)' : b.color,
                          }}
                        />
                      </div>
                    </div>
                    <div className={`lg-catamt ${over ? 'lg-over' : ''}`}>
                      {Math.round(b.pct * 100)}%
                      <small>
                        {formatDollarsAbs(b.spentCents)}/{formatDollarsAbs(b.limitCents)}
                      </small>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="lg-panel">
            <div className="lg-phead">
              <h3>Upcoming recurring</h3>
              <span className="lg-phead-sub">{formatDollarsAbs(upcomingCents)} due</span>
            </div>
            <ul className="lg-minilist">
              {upcoming.map((r) => {
                const cat = r.categoryId ? categoryById[r.categoryId] : null;
                return (
                  <li key={r.id} className="lg-minirow">
                    <span
                      className="lg-miniico"
                      style={{ background: (cat?.color ?? '#64748b') + '22' }}
                      aria-hidden
                    >
                      {cat?.icon ?? '↻'}
                    </span>
                    <div className="lg-minimeta">
                      <div className="lg-mininame">{r.name}</div>
                      <div className="lg-minisub">
                        {r.cadence} · next {formatShortDate(r.nextExpectedDate)}
                      </div>
                    </div>
                    <span className="lg-miniamt">{formatCentsAbs(r.expectedAmountCents)}</span>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="lg-panel">
            <div className="lg-phead">
              <h3>Largest purchases</h3>
              <span className="lg-phead-sub">{MONTH_LABEL.split(' ')[0]}</span>
            </div>
            <ul className="lg-minilist">
              {largest.map((t) => (
                <MiniTxn key={t.id} t={t} />
              ))}
            </ul>
          </div>
        </section>

        {/* recent transactions */}
        <section className="lg-panel">
          <div className="lg-phead">
            <h3>Recent transactions</h3>
            <span className="lg-phead-sub">Newest first</span>
          </div>
          <div className="lg-pbody flush">
            <div className="lg-tablewrap">
              <table className="lg-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Merchant</th>
                    <th>Account</th>
                    <th>Category</th>
                    <th className="num">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((t) => (
                    <TxnTableRow key={t.id} t={t} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </Chrome>
  );
}

function MiniTxn({ t }: { t: Transaction }) {
  const cat = t.categoryId ? categoryById[t.categoryId] : null;
  const positive = t.amountCents > 0;
  return (
    <li className="lg-minirow">
      <span
        className="lg-miniico"
        style={{ background: (cat?.color ?? '#94a3b8') + '22' }}
        aria-hidden
      >
        {cat?.icon ?? '❓'}
      </span>
      <div className="lg-minimeta">
        <div className="lg-mininame">{t.merchant}</div>
        <div className="lg-minisub">
          {formatShortDate(t.date)} · {accountById[t.accountId]?.name}
        </div>
      </div>
      <span className={`lg-miniamt ${positive ? 'lg-pos' : ''}`}>
        {positive ? '+' : ''}
        {formatCentsAbs(t.amountCents)}
      </span>
    </li>
  );
}

/* =================================================== TRANSACTIONS ==== */

function CategoryPill({ categoryId }: { categoryId: string | null }) {
  const cat = categoryId ? categoryById[categoryId] : null;
  if (!cat) {
    return <span className="lg-pill lg-pill-none">❓ Uncategorized</span>;
  }
  return (
    <span
      className="lg-pill"
      style={{ background: cat.color + '22', color: cat.color, borderColor: cat.color + '55' }}
    >
      <span aria-hidden>{cat.icon}</span> {cat.name}
    </span>
  );
}

function AmountCell({ amountCents }: { amountCents: number }) {
  const positive = amountCents > 0;
  return (
    <td className={`num lg-num-cell ${positive ? 'lg-pos' : ''}`}>
      {positive ? '+' : ''}
      {formatCents(amountCents)}
    </td>
  );
}

function TxnTableRow({ t }: { t: Transaction }) {
  const acct = accountById[t.accountId];
  return (
    <tr className={!t.includedInSpending ? 'excluded' : ''}>
      <td className="lg-td-date">{formatShortDate(t.date)}</td>
      <td className="lg-td-merch">
        <div className="lg-merch-name">{t.merchant}</div>
        <div className="lg-merch-raw">{t.rawDescription}</div>
      </td>
      <td className="lg-td-acct">
        <span className="lg-acct-tag">
          <span className="lg-acct-swatch" style={{ background: acct?.color }} aria-hidden />
          {acct?.name}
        </span>
      </td>
      <td>
        <CategoryPill categoryId={t.categoryId} />
        {!t.includedInSpending && <span className="lg-tag-excl">excluded</span>}
      </td>
      <AmountCell amountCents={t.amountCents} />
    </tr>
  );
}

function Transactions() {
  const [q, setQ] = useState('');
  const rows = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (!query) return allTxns;
    return allTxns.filter(
      (t) =>
        t.merchant.toLowerCase().includes(query) ||
        t.rawDescription.toLowerCase().includes(query),
    );
  }, [q]);

  const included = rows.filter((t) => t.includedInSpending).length;
  const excludedCount = rows.length - included;

  return (
    <Chrome
      active="Transactions"
      title="Transactions"
      meta={
        <>
          Ledger of all account activity · <b>{allTxns.length}</b> rows
        </>
      }
    >
      <div className="lg-toolbar">
        <div className="lg-search">
          <span className="lg-search-ico" aria-hidden>
            ⌕
          </span>
          <input
            type="search"
            placeholder="Search merchant or raw description…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search transactions"
          />
        </div>
        <button type="button" className="lg-chip">
          <span className="lg-chip-k">CAT</span> All ▾
        </button>
        <button type="button" className="lg-chip">
          <span className="lg-chip-k">TYPE</span> All ▾
        </button>
        <div className="lg-legend-row">
          <span>
            Showing <b>{rows.length}</b>
          </span>
          <span>
            Included <b>{included}</b>
          </span>
          <span>
            Excluded <b>{excludedCount}</b>
          </span>
        </div>
      </div>

      <div className="lg-page">
        <div className="lg-panel">
          <div className="lg-pbody flush">
            <div className="lg-tablewrap">
              <table className="lg-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Merchant / Description</th>
                    <th>Account</th>
                    <th>Category</th>
                    <th className="num">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((t) => (
                    <TxnTableRow key={t.id} t={t} />
                  ))}
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={5} className="lg-empty">
                        No transactions match “{q}”.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </Chrome>
  );
}

/* ========================================================= REVIEW ==== */

// Candidate categories offered as quick-pick buttons (spending categories only).
const REVIEW_CHOICES = categories.filter((c) => !c.excludedFromSpending && c.id !== 'uncategorized');

function Review() {
  const queue = useMemo(() => reviewQueue(), []);
  const [idx, setIdx] = useState(0);
  const [done, setDone] = useState<Record<string, boolean>>({});
  const [picked, setPicked] = useState<Record<string, string>>({});

  const total = queue.length;
  const completed = Object.keys(done).length;
  const t = queue[idx];

  function advance() {
    const next = queue.findIndex((q, i) => i > idx && !done[q.id]);
    if (next !== -1) setIdx(next);
    else {
      const firstOpen = queue.findIndex((q) => !done[q.id]);
      if (firstOpen !== -1) setIdx(firstOpen);
    }
  }

  function confirm(catId: string) {
    if (!t) return;
    setPicked((p) => ({ ...p, [t.id]: catId }));
    setDone((d) => ({ ...d, [t.id]: true }));
    advance();
  }

  if (total === 0) {
    return (
      <Chrome active="Review" title="Review Categories" meta="Nothing awaiting review">
        <div className="lg-page">
          <div className="lg-panel">
            <div className="lg-empty">
              <div className="lg-empty-big" aria-hidden>
                ✓
              </div>
              You are all caught up. Every transaction has a confirmed category.
            </div>
          </div>
        </div>
      </Chrome>
    );
  }

  const suggested = t && t.categoryId ? categoryById[t.categoryId] : null;
  const chosenId = t ? picked[t.id] ?? t.categoryId ?? undefined : undefined;
  const acct = t ? accountById[t.accountId] : undefined;
  const progressPct = total ? (completed / total) * 100 : 0;

  return (
    <Chrome
      active="Review"
      title="Review Categories"
      meta={
        <>
          <b>{completed}</b> of <b>{total}</b> reviewed · confirm or reassign each suggestion
        </>
      }
    >
      <div className="lg-page">
        <div className="lg-progress-bar" role="progressbar" aria-valuenow={completed} aria-valuemin={0} aria-valuemax={total}>
          <span style={{ width: `${progressPct}%` }} />
        </div>

        <div className="lg-review">
          {/* active card */}
          <div className="lg-panel">
            {t ? (
              <>
                <div className="lg-rev-head">
                  <span
                    className="lg-rev-ico"
                    style={{ background: (suggested?.color ?? '#94a3b8') + '22' }}
                    aria-hidden
                  >
                    {suggested?.icon ?? '❓'}
                  </span>
                  <div>
                    <h2 className="lg-rev-merch">{t.merchant}</h2>
                    <p className="lg-rev-raw">{t.rawDescription}</p>
                  </div>
                  <span className="lg-rev-amt">{formatCents(t.amountCents)}</span>
                </div>

                <div className="lg-rev-facts">
                  <div className="lg-fact">
                    <span className="lg-fact-k">Date</span>
                    <span className="lg-fact-v">{formatShortDate(t.date)}</span>
                  </div>
                  <div className="lg-fact">
                    <span className="lg-fact-k">Account</span>
                    <span className="lg-fact-v">{acct?.name}</span>
                  </div>
                  <div className="lg-fact">
                    <span className="lg-fact-k">Amount</span>
                    <span className="lg-fact-v">{formatCentsAbs(t.amountCents)}</span>
                  </div>
                  <div className="lg-fact">
                    <span className="lg-fact-k">Status</span>
                    <span className="lg-fact-v">{t.categorizationStatus}</span>
                  </div>
                </div>

                {suggested && (
                  <div className="lg-conf">
                    <span className="lg-conf-badge">
                      {typeof t.confidence === 'number' ? Math.round(t.confidence * 100) : '—'}% ·{' '}
                      {suggested.icon} {suggested.name}
                    </span>
                    <span className="lg-conf-reason">
                      {t.reason ?? 'Suggested from similar past transactions.'}
                    </span>
                  </div>
                )}

                <div className="lg-rev-body">
                  <div className="lg-rev-label">Assign category</div>
                  <div className="lg-catgrid">
                    {REVIEW_CHOICES.map((c) => {
                      const isChosen = chosenId === c.id;
                      const isSuggested = suggested?.id === c.id;
                      return (
                        <button
                          key={c.id}
                          type="button"
                          className={`lg-catbtn ${isChosen ? 'selected' : ''}`}
                          style={{ ['--c' as string]: c.color }}
                          onClick={() => confirm(c.id)}
                        >
                          <span className="lg-catbtn-ico" aria-hidden>
                            {c.icon}
                          </span>
                          {c.name}
                          {isSuggested && <em>suggested</em>}
                        </button>
                      );
                    })}
                  </div>

                  <label className="lg-remember">
                    <input type="checkbox" defaultChecked />
                    Remember “{t.merchant}” and auto-apply to future transactions
                  </label>

                  <div className="lg-rev-actions">
                    <button type="button" className="lg-btn" onClick={advance}>
                      Skip
                    </button>
                    <button
                      type="button"
                      className="lg-btn primary"
                      onClick={() => confirm(chosenId ?? suggested?.id ?? REVIEW_CHOICES[0].id)}
                    >
                      Confirm {suggested ? suggested.name : 'category'} →
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="lg-empty">
                <div className="lg-empty-big" aria-hidden>
                  ✓
                </div>
                Queue cleared — {completed} of {total} reviewed.
              </div>
            )}
          </div>

          {/* queue rail */}
          <div className="lg-panel">
            <div className="lg-phead">
              <h3>Queue</h3>
              <span className="lg-phead-sub">
                {completed}/{total}
              </span>
            </div>
            <ul className="lg-queue">
              {queue.map((qt, i) => {
                const c = qt.categoryId ? categoryById[qt.categoryId] : null;
                const isDone = !!done[qt.id];
                return (
                  <li key={qt.id}>
                    <button
                      type="button"
                      className={`lg-qitem ${i === idx ? 'active' : ''} ${isDone ? 'done' : ''}`}
                      onClick={() => setIdx(i)}
                      aria-current={i === idx ? 'true' : undefined}
                    >
                      <span className="lg-qico" aria-hidden>
                        {isDone ? <span className="lg-qcheck">✓</span> : c?.icon ?? '❓'}
                      </span>
                      <span className="lg-qname">{qt.merchant}</span>
                      <span className="lg-qamt">{formatCentsAbs(qt.amountCents)}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </div>
    </Chrome>
  );
}

/* ========================================================= EXPORT ==== */

const ledger: Direction = {
  meta: {
    id: 'ledger',
    name: 'Ledger',
    tagline: 'Dense, data-forward analyst cockpit',
    description:
      'A Bloomberg-terminal-meets-fintech workspace: a dark command rail, compact tabular-numeric rows, and charts front-and-centre. Maximum information density for people who want every metric on one screen.',
    accent: '#0ea5e9',
  },
  Dashboard,
  Transactions,
  Review,
};

export default ledger;
