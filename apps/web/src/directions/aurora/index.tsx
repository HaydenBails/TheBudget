import { useMemo, useState } from 'react';
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Area,
  AreaChart,
} from 'recharts';
import type { Direction } from '../types';
import {
  CURRENT_YM,
  availableToSaveCents,
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
  categoryById,
  profile,
  recurringSeries,
  transactions as allTxns,
} from '../../lib/mockData';
import type { Transaction } from '../../lib/types';
import { formatCents, formatCentsAbs, formatDollarsAbs, formatMonthLabel, formatShortDate, formatSignedPct } from '../../lib/format';
import './aurora.css';

const NAV = [
  { icon: '◔', label: 'Dashboard', screen: 'dashboard' },
  { icon: '≣', label: 'Transactions', screen: 'transactions' },
  { icon: '⬆', label: 'Import', screen: 'dashboard' },
  { icon: '✓', label: 'Review', screen: 'review' },
  { icon: '↻', label: 'Recurring', screen: 'dashboard' },
  { icon: '◫', label: 'Budgets', screen: 'dashboard' },
  { icon: '$', label: 'Income', screen: 'dashboard' },
  { icon: '◐', label: 'Reports', screen: 'dashboard' },
];

function Frame({ active, children }: { active: string; children: React.ReactNode }) {
  return (
    <div className="au">
      <aside className="au-side">
        <div className="au-brand">
          <span className="au-logo">◔</span>
          <span>Aurora</span>
        </div>
        <nav className="au-nav">
          {NAV.map((n) => (
            <div key={n.label} className={`au-navitem ${n.label === active ? 'active' : ''}`}>
              <span className="au-navicon" aria-hidden>{n.icon}</span>
              {n.label}
            </div>
          ))}
        </nav>
        <div className="au-profile">
          <span className="au-avatar">{profile.initials}</span>
          <div>
            <div className="au-profile-name">{profile.name}</div>
            <div className="au-profile-sub">Personal profile</div>
          </div>
        </div>
      </aside>
      <main className="au-main">{children}</main>
    </div>
  );
}

function Topbar({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="au-top">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="au-top-controls">
        <button className="au-chip">All accounts ▾</button>
        <button className="au-chip">{formatMonthLabel(CURRENT_YM + '-01')} ▾</button>
      </div>
    </header>
  );
}

function AuroraDashboard() {
  const spend = totalSpendingCents(CURRENT_YM);
  const mom = monthOverMonthChange();
  const income = incomeThisMonthCents();
  const save = availableToSaveCents();
  const budget = overallBudgetCents();
  const catData = spendingByCategory(CURRENT_YM);
  const trend = monthlyTrend();
  const budgetRatio = budget ? spend / budget : 0;
  const budgetPct = Math.min(budgetRatio, 1);
  const upcoming = recurringSeries.filter((r) => r.nextExpectedDate >= '2026-07-15').slice(0, 4);

  return (
    <>
      <Topbar title="Dashboard" subtitle={`Here's your money in ${formatMonthLabel(CURRENT_YM + '-01')}.`} />

      <section className="au-metrics">
        <div className="au-metric au-metric-hero">
          <span className="au-metric-label">Spent this month</span>
          <span className="au-metric-value">{formatDollarsAbs(spend)}</span>
          <span className={`au-delta ${mom > 0 ? 'up' : 'down'}`}>
            {formatSignedPct(mom)} vs June {mom > 0 ? '▲' : '▼'}
          </span>
        </div>
        <div className="au-metric">
          <span className="au-metric-label">Income (est.)</span>
          <span className="au-metric-value">{formatDollarsAbs(income)}</span>
          <span className="au-metric-foot">Recorded + expected</span>
        </div>
        <div className="au-metric">
          <span className="au-metric-label">Available to save</span>
          <span className="au-metric-value">{formatDollarsAbs(save)}</span>
          <span className="au-metric-foot">estimate · after recurring</span>
        </div>
        <div className="au-metric">
          <span className="au-metric-label">Overall budget</span>
          <span className="au-metric-value">{Math.round(budgetRatio * 100)}%</span>
          <div className="au-progress">
            <span style={{ width: `${budgetPct * 100}%`, background: budgetPct > 0.9 ? '#ef4444' : '#6366f1' }} />
          </div>
          <span className="au-metric-foot">{formatDollarsAbs(spend)} of {formatDollarsAbs(budget)}</span>
        </div>
      </section>

      <section className="au-cols">
        <div className="au-card au-card-chart">
          <div className="au-card-head">
            <h3>Spending over time</h3>
            <span className="au-card-sub">Last 4 months</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={trend} margin={{ top: 10, right: 8, left: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="au-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: 'var(--au-muted)' }} />
              <YAxis hide />
              <Tooltip
                formatter={(v: number) => formatDollarsAbs(v)}
                contentStyle={{ borderRadius: 12, border: '1px solid var(--au-border)', background: 'var(--au-panel)', color: 'var(--au-text)' }}
              />
              <Area type="monotone" dataKey="cents" stroke="#6366f1" strokeWidth={3} fill="url(#au-grad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="au-card">
          <div className="au-card-head">
            <h3>By category</h3>
            <span className="au-card-sub">{formatDollarsAbs(spend)}</span>
          </div>
          <div className="au-donut">
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={catData} dataKey="cents" nameKey="name" innerRadius={54} outerRadius={80} paddingAngle={2} strokeWidth={0}>
                  {catData.map((c) => (
                    <Cell key={c.categoryId} fill={c.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v: number, n) => [formatDollarsAbs(v), n as string]}
                  contentStyle={{ borderRadius: 12, border: '1px solid var(--au-border)', background: 'var(--au-panel)', color: 'var(--au-text)' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="au-legend">
            {catData.slice(0, 5).map((c) => (
              <li key={c.categoryId}>
                <span className="au-dot" style={{ background: c.color }} />
                <span className="au-legend-icon">{c.icon}</span>
                {c.name}
                <b>{formatDollarsAbs(c.cents)}</b>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="au-cols">
        <div className="au-card">
          <div className="au-card-head">
            <h3>Recent transactions</h3>
          </div>
          <ul className="au-txlist">
            {recentTransactions(6).map((t) => (
              <TxRow key={t.id} t={t} />
            ))}
          </ul>
        </div>
        <div className="au-card">
          <div className="au-card-head">
            <h3>Upcoming recurring</h3>
            <span className="au-card-sub">{formatDollarsAbs(upcomingRecurringCents())} due</span>
          </div>
          <ul className="au-txlist">
            {upcoming.map((r) => (
              <li key={r.id} className="au-txrow">
                <span className="au-txicon" style={{ background: (categoryById[r.categoryId ?? 'misc']?.color ?? '#888') + '22' }}>
                  {categoryById[r.categoryId ?? 'misc']?.icon ?? '↻'}
                </span>
                <div className="au-txmeta">
                  <span className="au-txname">{r.name}</span>
                  <span className="au-txsub">{r.cadence} · next {formatShortDate(r.nextExpectedDate)}</span>
                </div>
                <span className="au-txamt">{formatCentsAbs(r.expectedAmountCents)}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="au-card">
        <div className="au-card-head">
          <h3>Largest purchases</h3>
        </div>
        <ul className="au-txlist">
          {largestPurchases(CURRENT_YM, 4).map((t) => (
            <TxRow key={t.id} t={t} />
          ))}
        </ul>
      </section>
    </>
  );
}

function TxRow({ t }: { t: Transaction }) {
  const cat = t.categoryId ? categoryById[t.categoryId] : null;
  const positive = t.amountCents > 0;
  return (
    <li className="au-txrow">
      <span className="au-txicon" style={{ background: (cat?.color ?? '#94a3b8') + '22' }}>
        {cat?.icon ?? '❓'}
      </span>
      <div className="au-txmeta">
        <span className="au-txname">{t.merchant}</span>
        <span className="au-txsub">
          {formatShortDate(t.date)} · {accountById[t.accountId]?.name}
        </span>
      </div>
      <span className={`au-txamt ${positive ? 'pos' : ''}`}>{positive ? '+' : ''}{formatCentsAbs(t.amountCents)}</span>
    </li>
  );
}

function AuroraTransactions() {
  const [q, setQ] = useState('');
  const rows = useMemo(() => {
    const query = q.trim().toLowerCase();
    return allTxns.filter(
      (t) => !query || t.merchant.toLowerCase().includes(query) || t.rawDescription.toLowerCase().includes(query),
    );
  }, [q]);

  return (
    <>
      <Topbar title="Transactions" subtitle={`${rows.length} transactions · all accounts`} />
      <div className="au-toolbar">
        <input className="au-search" placeholder="Search merchant or description…" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="au-chip">Category ▾</button>
        <button className="au-chip">Type ▾</button>
        <button className="au-chip">Included ▾</button>
      </div>
      <div className="au-card au-card-flush">
        <table className="au-table">
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
            {rows.slice(0, 40).map((t) => {
              const cat = t.categoryId ? categoryById[t.categoryId] : null;
              const positive = t.amountCents > 0;
              return (
                <tr key={t.id} className={!t.includedInSpending ? 'excluded' : ''}>
                  <td className="muted">{formatShortDate(t.date)}</td>
                  <td>
                    <div className="au-cellmerch">
                      <span className="au-txname">{t.merchant}</span>
                      <span className="au-txsub">{t.rawDescription}</span>
                    </div>
                  </td>
                  <td className="muted">{accountById[t.accountId]?.name}</td>
                  <td>
                    {cat ? (
                      <span className="au-pill" style={{ background: cat.color + '22', color: cat.color }}>
                        {cat.icon} {cat.name}
                      </span>
                    ) : (
                      <span className="au-pill au-pill-none">❓ Uncategorized</span>
                    )}
                    {!t.includedInSpending && <span className="au-tag-excl">excluded</span>}
                  </td>
                  <td className={`num ${positive ? 'pos' : ''}`}>{positive ? '+' : ''}{formatCents(t.amountCents)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

function AuroraReview() {
  const queue = reviewQueue();
  const [idx, setIdx] = useState(0);
  const t = queue[idx];

  if (!t) {
    return (
      <>
        <Topbar title="Review Categories" subtitle="You're all caught up 🎉" />
        <div className="au-card au-empty">Nothing left to review.</div>
      </>
    );
  }

  const suggested = t.categoryId ? categoryById[t.categoryId] : null;
  const suggestions = ['dining', 'groceries', 'shopping', 'transport', 'entertainment', 'health'].map((id) => categoryById[id]);

  return (
    <>
      <Topbar title="Review Categories" subtitle={`${queue.length} to review · ${idx + 1} of ${queue.length}`} />
      <div className="au-review">
        <div className="au-progress au-progress-lg">
          <span style={{ width: `${((idx + 1) / queue.length) * 100}%` }} />
        </div>
        <div className="au-card au-reviewcard">
          <div className="au-reviewhead">
            <span className="au-txicon lg" style={{ background: (suggested?.color ?? '#94a3b8') + '22' }}>
              {suggested?.icon ?? '❓'}
            </span>
            <div>
              <h2>{t.merchant}</h2>
              <p className="au-txsub">{t.rawDescription}</p>
            </div>
            <span className="au-reviewamt">{formatCents(t.amountCents)}</span>
          </div>
          <div className="au-reviewmeta">
            <span>{formatShortDate(t.date)}</span>
            <span>·</span>
            <span>{accountById[t.accountId]?.name}</span>
            {t.confidence && (
              <span className="au-conf">
                {Math.round(t.confidence * 100)}% confident · {t.reason}
              </span>
            )}
          </div>

          <div className="au-catgrid">
            {suggestions.map((c) => (
              <button
                key={c.id}
                className={`au-catbtn ${suggested?.id === c.id ? 'suggested' : ''}`}
                style={{ ['--c' as string]: c.color }}
              >
                <span>{c.icon}</span>
                {c.name}
                {suggested?.id === c.id && <em>suggested</em>}
              </button>
            ))}
          </div>

          <label className="au-remember">
            <input type="checkbox" defaultChecked /> Remember this merchant for future transactions
          </label>

          <div className="au-reviewactions">
            <button className="au-btn ghost" onClick={() => setIdx((i) => Math.max(0, i - 1))}>
              Skip
            </button>
            <button className="au-btn primary" onClick={() => setIdx((i) => Math.min(queue.length, i + 1))}>
              Confirm {suggested?.name ?? 'category'} →
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

const aurora: Direction = {
  meta: {
    id: 'aurora',
    name: 'Aurora',
    tagline: 'Calm, modern banking',
    description:
      'Airy indigo palette, soft cards, and generous whitespace. A gentle sidebar, big friendly numbers, and one hero metric that anchors the page.',
    accent: '#6366f1',
  },
  Dashboard: () => (
    <Frame active="Dashboard">
      <AuroraDashboard />
    </Frame>
  ),
  Transactions: () => (
    <Frame active="Transactions">
      <AuroraTransactions />
    </Frame>
  ),
  Review: () => (
    <Frame active="Review">
      <AuroraReview />
    </Frame>
  ),
};

export default aurora;
