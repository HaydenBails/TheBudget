import { useMemo, useState } from 'react';
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
import type { Direction, ScreenKey } from '../types';
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
import type { Category, Transaction } from '../../lib/types';
import {
  formatCents,
  formatCentsAbs,
  formatDollarsAbs,
  formatMonthLabel,
  formatShortDate,
  formatSignedPct,
} from '../../lib/format';
import './meridian.css';

const MONTH_LABEL = formatMonthLabel(CURRENT_YM + '-01');

const NAV: { icon: string; label: string; screen: ScreenKey | null }[] = [
  { icon: '◧', label: 'Dashboard', screen: 'dashboard' },
  { icon: '≣', label: 'Transactions', screen: 'transactions' },
  { icon: '↥', label: 'Import', screen: null },
  { icon: '✓', label: 'Review', screen: 'review' },
  { icon: '↻', label: 'Recurring', screen: null },
  { icon: '◑', label: 'Budgets', screen: null },
  { icon: '⌁', label: 'Income', screen: null },
  { icon: '◔', label: 'Reports', screen: null },
];

/** Categories a user can assign in review (exclude system/excluded ones). */
const REVIEW_CATEGORIES: Category[] = categories.filter(
  (c) => !c.excludedFromSpending && c.id !== 'uncategorized',
);

const tooltipStyle = {
  borderRadius: 12,
  border: '1px solid var(--mrd-border)',
  background: 'var(--mrd-panel)',
  color: 'var(--mrd-text)',
  fontSize: 12.5,
  fontWeight: 600,
  boxShadow: 'var(--mrd-shadow)',
};

/* ------------------------------------------------------------------ chrome */

function TopNav({ active }: { active: string }) {
  return (
    <nav className="mrd-nav" aria-label="Primary">
      <div className="mrd-brand">
        <span className="mrd-logo" aria-hidden>
          ◈
        </span>
        Meridian
      </div>
      <div className="mrd-tabs">
        {NAV.map((n) => (
          <button
            key={n.label}
            type="button"
            className={`mrd-tab ${n.label === active ? 'active' : ''}`}
            aria-current={n.label === active ? 'page' : undefined}
          >
            <span className="mrd-tab-ico" aria-hidden>
              {n.icon}
            </span>
            {n.label}
          </button>
        ))}
      </div>
      <div className="mrd-nav-right">
        <button type="button" className="mrd-iconbtn" aria-label="Notifications">
          ◔
        </button>
        <span className="mrd-user">
          <span className="mrd-avatar" aria-hidden>
            {profile.initials}
          </span>
          <span className="mrd-user-meta">
            <b>{profile.name}</b>
            <span>Personal</span>
          </span>
        </span>
      </div>
    </nav>
  );
}

function SubHeader({ title, subtitle }: { title: string; subtitle: React.ReactNode }) {
  return (
    <div className="mrd-sub">
      <div className="mrd-sub-titles">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="mrd-sub-ctrls">
        <button type="button" className="mrd-chip">
          <span className="mrd-chip-k">Account</span> All accounts <span aria-hidden>▾</span>
        </button>
        <button type="button" className="mrd-chip">
          <span className="mrd-chip-k">Period</span> {MONTH_LABEL} <span aria-hidden>▾</span>
        </button>
      </div>
    </div>
  );
}

function Frame({
  active,
  title,
  subtitle,
  children,
}: {
  active: string;
  title: string;
  subtitle: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="mrd">
      <TopNav active={active} />
      <div className="mrd-body">
        <SubHeader title={title} subtitle={subtitle} />
        {children}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- dashboard */

function Dashboard() {
  const spend = totalSpendingCents(CURRENT_YM);
  const prevSpend = totalSpendingCents(PREV_YM);
  const mom = monthOverMonthChange();
  const income = incomeThisMonthCents();
  const save = availableToSaveCents();
  const budget = overallBudgetCents();
  const budgetRatio = budget ? spend / budget : 0;
  const budgetOver = budgetRatio > 1;
  const upcomingCents = upcomingRecurringCents();
  const excluded = excludedActivityCents(CURRENT_YM);

  const catData = spendingByCategory(CURRENT_YM);
  const trend = monthlyTrend();
  const budgetRows = categoryBudgetProgress(CURRENT_YM);
  const recent = recentTransactions(6);
  const largest = largestPurchases(CURRENT_YM, 4);

  const upcoming = [...recurringSeries]
    .filter((r) => r.status !== 'ended' && r.status !== 'ignored')
    .sort((a, b) => a.nextExpectedDate.localeCompare(b.nextExpectedDate))
    .slice(0, 4);

  return (
    <Frame
      active="Dashboard"
      title="Dashboard"
      subtitle={
        <>
          Your money in <b>{MONTH_LABEL}</b> · {allTxns.length} transactions · 2 accounts
        </>
      }
    >
      {/* hero + secondary metrics */}
      <section className="mrd-hero-row">
        <div className="mrd-hero">
          <span className="mrd-hero-k">Spent this month</span>
          <div className="mrd-hero-main">
            <span className="mrd-hero-v">{formatDollarsAbs(spend)}</span>
            <span className={`mrd-delta ${mom > 0 ? 'up' : 'down'}`}>
              <span aria-hidden>{mom > 0 ? '↑' : '↓'}</span> {formatSignedPct(mom)}
            </span>
          </div>
          <span className="mrd-hero-foot">
            vs {formatDollarsAbs(prevSpend)} in June · {formatDollarsAbs(income)} income est.
          </span>
          <div className="mrd-hero-budget">
            <div className="mrd-hero-budget-row">
              <span>Overall budget</span>
              <span className={budgetOver ? 'over' : ''}>
                {formatDollarsAbs(spend)} / {formatDollarsAbs(budget)} · {Math.round(budgetRatio * 100)}%
              </span>
            </div>
            <div className="mrd-meter" role="progressbar" aria-valuenow={Math.round(budgetRatio * 100)} aria-valuemin={0} aria-valuemax={100}>
              <span style={{ width: `${Math.min(budgetRatio, 1) * 100}%` }} className={budgetOver ? 'over' : ''} />
            </div>
          </div>
        </div>

        <div className="mrd-statcards">
          <StatCard icon="↑" label="Available to save" value={formatDollarsAbs(save)} foot="After spend + recurring" tone={save < 0 ? 'neg' : 'accent'} />
          <StatCard icon="◈" label="Income (est.)" value={formatDollarsAbs(income)} foot="Recorded + expected" />
          <StatCard icon="↻" label="Upcoming recurring" value={formatDollarsAbs(upcomingCents)} foot="Due before month end" />
          <StatCard icon="⊘" label="Excluded activity" value={formatDollarsAbs(excluded)} foot="Payments · fees · transfers" />
        </div>
      </section>

      {/* trend + category */}
      <section className="mrd-grid-2">
        <Card title="Spending over time" meta="Apr – Jul">
          <ResponsiveContainer width="100%" height={236}>
            <AreaChart data={trend} margin={{ top: 8, right: 6, left: 6, bottom: 0 }}>
              <defs>
                <linearGradient id="mrd-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--mrd-accent)" stopOpacity={0.32} />
                  <stop offset="100%" stopColor="var(--mrd-accent)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: 'var(--mrd-faint)' }} />
              <YAxis hide />
              <Tooltip formatter={(v: number) => [formatDollarsAbs(v), 'Spent']} contentStyle={tooltipStyle} cursor={{ stroke: 'var(--mrd-accent)', strokeDasharray: '4 4' }} />
              <Area type="monotone" dataKey="cents" stroke="var(--mrd-accent)" strokeWidth={3} fill="url(#mrd-grad)" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card title="By category" meta={`${catData.length} categories`}>
          <div className="mrd-donut-wrap">
            <div className="mrd-donut">
              <ResponsiveContainer width="100%" height={168}>
                <PieChart>
                  <Pie data={catData} dataKey="cents" nameKey="name" innerRadius={56} outerRadius={80} paddingAngle={2} strokeWidth={0}>
                    {catData.map((c) => (
                      <Cell key={c.categoryId} fill={c.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number, n) => [formatDollarsAbs(v), n as string]} contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mrd-donut-center">
                <span>{formatDollarsAbs(spend)}</span>
                <small>total</small>
              </div>
            </div>
            <ul className="mrd-catlegend">
              {catData.slice(0, 5).map((c) => (
                <li key={c.categoryId}>
                  <span className="mrd-swatch" style={{ background: c.color }} aria-hidden />
                  <span className="mrd-legend-ico" aria-hidden>{c.icon}</span>
                  <span className="mrd-legend-name">{c.name}</span>
                  <b>{formatDollarsAbs(c.cents)}</b>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </section>

      {/* budgets + recurring + largest */}
      <section className="mrd-grid-3">
        <Card title="Category budgets" meta={`${budgetRows.length} tracked`}>
          <ul className="mrd-budgetlist">
            {budgetRows.map((b) => (
              <li key={b.categoryId}>
                <div className="mrd-budget-top">
                  <span className="mrd-legend-ico" aria-hidden>{b.icon}</span>
                  <span className="mrd-budget-name">{b.name}</span>
                  <span className={`mrd-budget-pct ${b.pct > 1 ? 'over' : ''}`}>{Math.round(b.pct * 100)}%</span>
                </div>
                <div className="mrd-meter sm">
                  <span style={{ width: `${Math.min(b.pct, 1) * 100}%`, background: b.pct > 1 ? 'var(--mrd-neg)' : b.color }} />
                </div>
                <span className="mrd-budget-foot">
                  {formatDollarsAbs(b.spentCents)} / {formatDollarsAbs(b.limitCents)}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Upcoming recurring" meta={`${formatDollarsAbs(upcomingCents)} due`}>
          <ul className="mrd-rows">
            {upcoming.map((r) => (
              <li key={r.id} className="mrd-row">
                <span className="mrd-ico" style={{ background: (categoryById[r.categoryId ?? 'misc']?.color ?? '#888') + '1f' }} aria-hidden>
                  {categoryById[r.categoryId ?? 'misc']?.icon ?? '↻'}
                </span>
                <span className="mrd-row-meta">
                  <b>{r.name}</b>
                  <small>{r.cadence} · next {formatShortDate(r.nextExpectedDate)}</small>
                </span>
                <span className="mrd-row-amt">{formatCentsAbs(r.expectedAmountCents)}</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Largest purchases" meta={MONTH_LABEL}>
          <ul className="mrd-rows">
            {largest.map((t) => (
              <TxRow key={t.id} t={t} />
            ))}
          </ul>
        </Card>
      </section>

      {/* recent table */}
      <Card title="Recent transactions" meta="Newest first" flush>
        <table className="mrd-table">
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
              <TableRow key={t.id} t={t} />
            ))}
          </tbody>
        </table>
      </Card>
    </Frame>
  );
}

function StatCard({ icon, label, value, foot, tone }: { icon: string; label: string; value: string; foot: string; tone?: 'accent' | 'neg' }) {
  return (
    <div className="mrd-stat">
      <span className={`mrd-stat-ico ${tone ?? ''}`} aria-hidden>{icon}</span>
      <span className="mrd-stat-k">{label}</span>
      <span className={`mrd-stat-v ${tone === 'neg' ? 'neg' : ''}`}>{value}</span>
      <span className="mrd-stat-foot">{foot}</span>
    </div>
  );
}

function Card({ title, meta, children, flush }: { title: string; meta?: string; children: React.ReactNode; flush?: boolean }) {
  return (
    <div className={`mrd-card ${flush ? 'flush' : ''}`}>
      <div className="mrd-card-head">
        <h3>{title}</h3>
        {meta && <span className="mrd-card-meta">{meta}</span>}
      </div>
      {children}
    </div>
  );
}

function TxRow({ t }: { t: Transaction }) {
  const cat = t.categoryId ? categoryById[t.categoryId] : null;
  const positive = t.amountCents > 0;
  return (
    <li className="mrd-row">
      <span className="mrd-ico" style={{ background: (cat?.color ?? '#94a3b8') + '1f' }} aria-hidden>
        {cat?.icon ?? '❓'}
      </span>
      <span className="mrd-row-meta">
        <b>{t.merchant}</b>
        <small>{formatShortDate(t.date)} · {accountById[t.accountId]?.name}</small>
      </span>
      <span className={`mrd-row-amt ${positive ? 'pos' : ''}`}>{positive ? '+' : ''}{formatCentsAbs(t.amountCents)}</span>
    </li>
  );
}

function TableRow({ t }: { t: Transaction }) {
  const cat = t.categoryId ? categoryById[t.categoryId] : null;
  const positive = t.amountCents > 0;
  return (
    <tr className={!t.includedInSpending ? 'excluded' : ''}>
      <td className="muted mono">{formatShortDate(t.date)}</td>
      <td>
        <div className="mrd-cell-merch">
          <b>{t.merchant}</b>
          <small className="mono">{t.rawDescription}</small>
        </div>
      </td>
      <td className="muted">
        <span className="mrd-acct">
          <span className="mrd-acct-dot" style={{ background: accountById[t.accountId]?.color }} aria-hidden />
          {accountById[t.accountId]?.name}
        </span>
      </td>
      <td>
        {cat ? (
          <span className="mrd-pill" style={{ background: cat.color + '1f', color: cat.color }}>
            <span aria-hidden>{cat.icon}</span> {cat.name}
          </span>
        ) : (
          <span className="mrd-pill none">❓ Uncategorized</span>
        )}
        {!t.includedInSpending && <span className="mrd-excl">excluded</span>}
      </td>
      <td className={`num mono ${positive ? 'pos' : ''}`}>{positive ? '+' : ''}{formatCents(t.amountCents)}</td>
    </tr>
  );
}

/* ------------------------------------------------------------ transactions */

function Transactions() {
  const [q, setQ] = useState('');
  const rows = useMemo(() => {
    const query = q.trim().toLowerCase();
    return allTxns.filter(
      (t) => !query || t.merchant.toLowerCase().includes(query) || t.rawDescription.toLowerCase().includes(query),
    );
  }, [q]);
  const included = rows.filter((t) => t.includedInSpending).length;

  return (
    <Frame
      active="Transactions"
      title="Transactions"
      subtitle={
        <>
          <b>{rows.length}</b> shown · {included} included · {rows.length - included} excluded
        </>
      }
    >
      <div className="mrd-toolbar">
        <div className="mrd-searchwrap">
          <span aria-hidden>⌕</span>
          <input className="mrd-search" placeholder="Search merchant or description…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <button type="button" className="mrd-chip">Category ▾</button>
        <button type="button" className="mrd-chip">Type ▾</button>
        <button type="button" className="mrd-chip">Included ▾</button>
      </div>
      <div className="mrd-card flush">
        <table className="mrd-table">
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
            {rows.slice(0, 40).map((t) => (
              <TableRow key={t.id} t={t} />
            ))}
          </tbody>
        </table>
      </div>
    </Frame>
  );
}

/* ------------------------------------------------------------------ review */

function Review() {
  const queue = reviewQueue();
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [done, setDone] = useState<Set<string>>(new Set());
  const [idx, setIdx] = useState(0);

  const current = queue[idx];
  const completed = done.size;
  const pct = queue.length ? (completed / queue.length) * 100 : 100;

  function advance() {
    setIdx((i) => {
      for (let step = 1; step <= queue.length; step++) {
        const j = (i + step) % queue.length;
        if (!done.has(queue[j].id)) return j;
      }
      return i;
    });
  }
  function confirm(id: string) {
    setDone((prev) => new Set(prev).add(id));
    advance();
  }

  if (!current || completed >= queue.length) {
    return (
      <Frame active="Review" title="Review" subtitle="Category clean-up">
        <div className="mrd-card mrd-empty">
          <span className="mrd-empty-badge" aria-hidden>✓</span>
          <h2>All caught up</h2>
          <p>Every transaction has a category. New imports will land here when they need a look.</p>
        </div>
      </Frame>
    );
  }

  const suggested = current.categoryId ? categoryById[current.categoryId] : null;
  const selectedId = choice[current.id] ?? current.categoryId ?? '';
  const conf = Math.round((current.confidence ?? 0) * 100);
  const positive = current.amountCents > 0;

  return (
    <Frame
      active="Review"
      title="Review"
      subtitle={
        <>
          <b>{queue.length - completed}</b> to categorise · {completed} done
        </>
      }
    >
      <div className="mrd-review">
        {/* active card */}
        <div className="mrd-card mrd-reviewcard">
          <div className="mrd-progress" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
            <span style={{ width: `${pct}%` }} />
          </div>

          <div className="mrd-reviewtop">
            <span className="mrd-ico mrd-ico-lg" style={{ background: (categoryById[selectedId]?.color ?? suggested?.color ?? '#94a3b8') + '1f' }} aria-hidden>
              {categoryById[selectedId]?.icon ?? suggested?.icon ?? '❓'}
            </span>
            <div className="mrd-reviewtop-meta">
              <h2>{current.merchant}</h2>
              <p className="mono">{current.rawDescription}</p>
            </div>
            <span className={`mrd-reviewamt ${positive ? 'pos' : ''}`}>{positive ? '+' : ''}{formatCentsAbs(current.amountCents)}</span>
          </div>

          <div className="mrd-facts">
            <span>📅 {formatShortDate(current.date)}</span>
            <span>💳 {accountById[current.accountId]?.name}</span>
            {suggested && (
              <span className="mrd-suggest">
                <span className="mrd-suggest-ring" style={{ ['--p' as string]: conf }} aria-hidden>{conf}%</span>
                Suggested <b>{suggested.name}</b> — {current.reason ?? 'based on merchant history'}
              </span>
            )}
          </div>

          <div className="mrd-secttitle">Choose a category</div>
          <div className="mrd-catgrid" role="group" aria-label="Choose a category">
            {REVIEW_CATEGORIES.map((c) => {
              const isSel = selectedId === c.id;
              const isSuggested = suggested?.id === c.id;
              return (
                <button
                  key={c.id}
                  type="button"
                  className={`mrd-catbtn ${isSel ? 'selected' : ''}`}
                  style={{ ['--c' as string]: c.color }}
                  aria-pressed={isSel}
                  onClick={() => setChoice((p) => ({ ...p, [current.id]: c.id }))}
                >
                  <span className="mrd-catbtn-ico" aria-hidden>{c.icon}</span>
                  {c.name}
                  {isSuggested && <em>suggested</em>}
                </button>
              );
            })}
          </div>

          <label className="mrd-remember">
            <input type="checkbox" defaultChecked /> Remember <b>&nbsp;{current.merchant}&nbsp;</b> for future transactions
          </label>

          <div className="mrd-reviewactions">
            <button type="button" className="mrd-btn ghost" onClick={advance}>Skip</button>
            <button type="button" className="mrd-btn primary" disabled={!selectedId} onClick={() => confirm(current.id)}>
              Confirm {selectedId ? categoryById[selectedId]?.name : 'category'} →
            </button>
          </div>
        </div>

        {/* queue rail (Ledger-style detail) */}
        <div className="mrd-card mrd-queue">
          <div className="mrd-card-head">
            <h3>Queue</h3>
            <span className="mrd-card-meta">{completed}/{queue.length}</span>
          </div>
          <ul className="mrd-queuelist">
            {queue.map((t, i) => {
              const isDone = done.has(t.id);
              const isCur = i === idx && !isDone;
              const cat = t.categoryId ? categoryById[t.categoryId] : null;
              return (
                <li key={t.id}>
                  <button type="button" className={`mrd-queueitem ${isCur ? 'current' : ''} ${isDone ? 'done' : ''}`} onClick={() => setIdx(i)}>
                    <span className="mrd-queue-ico" aria-hidden>{isDone ? '✓' : cat?.icon ?? '❓'}</span>
                    <span className="mrd-queue-meta">
                      <b>{t.merchant}</b>
                      <small>{formatShortDate(t.date)}</small>
                    </span>
                    <span className="mrd-queue-amt mono">{formatCentsAbs(t.amountCents)}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </Frame>
  );
}

const meridian: Direction = {
  meta: {
    id: 'meridian',
    name: 'Meridian',
    tagline: 'Ledger detail, Horizon warmth',
    description:
      'The blend: Ledger’s information density and precise tabular numbers, softened with Horizon’s rounded cards, gentle gradients and warmth. Professional, but friendly.',
    accent: '#4f6bff',
  },
  Dashboard,
  Transactions,
  Review,
};

export default meridian;
