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
import type { Direction } from '../types';
import {
  CURRENT_YM,
  availableToSaveCents,
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
import './horizon.css';

type Screen = 'dashboard' | 'transactions' | 'review';

const NAV: { icon: string; label: string; screen: Screen }[] = [
  { icon: '🏔️', label: 'Dashboard', screen: 'dashboard' },
  { icon: '🧾', label: 'Transactions', screen: 'transactions' },
  { icon: '✨', label: 'Review', screen: 'review' },
];

const MONTH_LABEL = formatMonthLabel(CURRENT_YM + '-01');

/** Categories a user can actively assign in review (excludes excluded/uncategorized). */
const REVIEW_CATEGORIES: Category[] = categories.filter(
  (c) => !c.excludedFromSpending && c.id !== 'uncategorized',
);

function Frame({ active, children }: { active: Screen; children: React.ReactNode }) {
  return (
    <div className="hz">
      <nav className="hz-nav" aria-label="Primary">
        <div className="hz-brand">
          <span className="hz-logo" aria-hidden>
            ◭
          </span>
          <span>Horizon</span>
        </div>
        <div className="hz-navlinks">
          {NAV.map((n) => (
            <button
              key={n.label}
              type="button"
              className={`hz-navlink ${n.screen === active ? 'active' : ''}`}
              aria-current={n.screen === active ? 'page' : undefined}
            >
              <span className="hz-navicon" aria-hidden>
                {n.icon}
              </span>
              {n.label}
            </button>
          ))}
        </div>
        <div className="hz-navright">
          <span className="hz-avatar" aria-hidden>
            {profile.initials}
          </span>
          <span className="hz-who">
            <b>{profile.name}</b>
            <span>Personal</span>
          </span>
        </div>
      </nav>
      <main className="hz-main">{children}</main>
    </div>
  );
}

function PageHead({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="hz-pagehead">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="hz-headctrls">
        <button type="button" className="hz-chip">
          All accounts ▾
        </button>
        <button type="button" className="hz-chip">
          {MONTH_LABEL} ▾
        </button>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- Dashboard */

function Hero() {
  const spend = totalSpendingCents(CURRENT_YM);
  const mom = monthOverMonthChange();
  const income = incomeThisMonthCents();
  const save = availableToSaveCents();
  const budget = overallBudgetCents();
  const budgetRatio = budget ? spend / budget : 0;
  const budgetPct = Math.min(budgetRatio, 1);
  const up = mom > 0;

  return (
    <section className="hz-hero" aria-label="Spending summary">
      <div className="hz-hero-top">
        <span aria-hidden>🏔️</span> Spent in {MONTH_LABEL}
      </div>
      <div className="hz-hero-grid">
        <div>
          <div className="hz-hero-num">{formatDollarsAbs(spend)}</div>
          <div className="hz-hero-sub">
            <span className="hz-delta">
              <span aria-hidden>{up ? '▲' : '▼'}</span>
              {formatSignedPct(mom)} vs June
            </span>
            <span className="hz-hero-of">{up ? 'more than' : 'less than'} last month</span>
          </div>
        </div>
        <div className="hz-hero-stats">
          <div className="hz-hstat">
            <div className="hz-hstat-label">💵 Income (est.)</div>
            <div className="hz-hstat-val">{formatDollarsAbs(income)}</div>
            <div className="hz-hstat-foot">Recorded + expected this month</div>
          </div>
          <div className="hz-hstat">
            <div className="hz-hstat-label">🐖 Available to save</div>
            <div className="hz-hstat-val">{formatDollarsAbs(save)}</div>
            <div className="hz-hstat-foot">After spending &amp; recurring</div>
          </div>
        </div>
      </div>
      <div className="hz-hero-budget">
        <div className="hz-hero-budget-row">
          <span>Overall budget</span>
          <span>
            {formatDollarsAbs(spend)} of {formatDollarsAbs(budget)} · {Math.round(budgetRatio * 100)}%
          </span>
        </div>
        <div className="hz-bigbar" role="progressbar" aria-valuenow={Math.round(budgetRatio * 100)} aria-valuemin={0} aria-valuemax={100} aria-label="Overall budget used">
          <span style={{ width: `${budgetPct * 100}%` }} />
        </div>
      </div>
    </section>
  );
}

function TrendCard() {
  const trend = monthlyTrend();
  return (
    <div className="hz-card">
      <div className="hz-cardhead">
        <h3>Spending over time</h3>
        <span className="hz-cardsub">Apr – Jul</span>
      </div>
      <ResponsiveContainer width="100%" height={230}>
        <AreaChart data={trend} margin={{ top: 8, right: 6, left: 6, bottom: 0 }}>
          <defs>
            <linearGradient id="hz-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f97316" stopOpacity={0.55} />
              <stop offset="55%" stopColor="#ec4899" stopOpacity={0.22} />
              <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 12 }} />
          <YAxis hide />
          <Tooltip
            formatter={(v: number) => [formatDollarsAbs(v), 'Spent']}
            contentStyle={{
              borderRadius: 14,
              border: '1px solid var(--hz-border)',
              background: 'var(--hz-panel)',
              color: 'var(--hz-text)',
              boxShadow: 'var(--hz-shadow)',
              fontWeight: 600,
            }}
            cursor={{ stroke: '#f97316', strokeWidth: 1, strokeDasharray: '4 4' }}
          />
          <Area type="monotone" dataKey="cents" stroke="#f97316" strokeWidth={3.5} fill="url(#hz-grad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function CategoryCard() {
  const cats = spendingByCategory(CURRENT_YM);
  const total = totalSpendingCents(CURRENT_YM);
  return (
    <div className="hz-card">
      <div className="hz-cardhead">
        <h3>By category</h3>
        <span className="hz-cardsub">{cats.length} categories</span>
      </div>
      <div className="hz-donut-wrap">
        <ResponsiveContainer width="100%" height={190}>
          <PieChart>
            <Pie
              data={cats}
              dataKey="cents"
              nameKey="name"
              innerRadius={62}
              outerRadius={88}
              paddingAngle={3}
              cornerRadius={6}
              strokeWidth={0}
            >
              {cats.map((c) => (
                <Cell key={c.categoryId} fill={c.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(v: number, n) => [formatDollarsAbs(v), n as string]}
              contentStyle={{
                borderRadius: 14,
                border: '1px solid var(--hz-border)',
                background: 'var(--hz-panel)',
                color: 'var(--hz-text)',
                boxShadow: 'var(--hz-shadow)',
                fontWeight: 600,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="hz-donut-center">
          <b>{formatDollarsAbs(total)}</b>
          <span>total</span>
        </div>
      </div>
      <ul className="hz-legend">
        {cats.slice(0, 5).map((c) => (
          <li key={c.categoryId}>
            <span className="hz-legend-bar" style={{ background: c.color }} aria-hidden />
            <span className="hz-legend-icon" aria-hidden>
              {c.icon}
            </span>
            {c.name}
            <b>{formatDollarsAbs(c.cents)}</b>
          </li>
        ))}
      </ul>
    </div>
  );
}

function TxRow({ t }: { t: Transaction }) {
  const cat = t.categoryId ? categoryById[t.categoryId] : null;
  const positive = t.amountCents > 0;
  return (
    <li className="hz-row">
      <span className="hz-ico" style={{ background: (cat?.color ?? '#94a3b8') + '26' }} aria-hidden>
        {cat?.icon ?? '❓'}
      </span>
      <div className="hz-rowmeta">
        <span className="hz-rowname">{t.merchant}</span>
        <span className="hz-rowsub">
          {formatShortDate(t.date)} · {accountById[t.accountId]?.name}
        </span>
      </div>
      <span className={`hz-amt ${positive ? 'pos' : ''}`}>
        {positive ? '+' : ''}
        {formatCentsAbs(t.amountCents)}
      </span>
    </li>
  );
}

function UpcomingCard() {
  const upcoming = recurringSeries
    .filter((r) => r.status === 'keep' || r.status === 'review')
    .slice()
    .sort((a, b) => a.nextExpectedDate.localeCompare(b.nextExpectedDate))
    .slice(0, 4);
  return (
    <div className="hz-card">
      <div className="hz-cardhead">
        <h3>Upcoming recurring</h3>
        <span className="hz-cardsub">{formatDollarsAbs(upcomingRecurringCents())} left this month</span>
      </div>
      <ul className="hz-list">
        {upcoming.map((r) => {
          const cat = r.categoryId ? categoryById[r.categoryId] : null;
          return (
            <li key={r.id} className="hz-row">
              <span className="hz-ico" style={{ background: (cat?.color ?? '#94a3b8') + '26' }} aria-hidden>
                {cat?.icon ?? '↻'}
              </span>
              <div className="hz-rowmeta">
                <span className="hz-rowname">{r.name}</span>
                <span className="hz-rowsub">
                  {r.cadence} · next {formatShortDate(r.nextExpectedDate)}
                </span>
              </div>
              <span className="hz-amt">{formatCentsAbs(r.expectedAmountCents)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function HorizonDashboard() {
  const excluded = excludedActivityCents(CURRENT_YM);
  return (
    <>
      <PageHead title={`Hey ${profile.name} 👋`} subtitle={`Here's your money in ${MONTH_LABEL}.`} />
      <Hero />

      <div className="hz-grid two">
        <TrendCard />
        <CategoryCard />
      </div>

      <div className="hz-grid two">
        <div className="hz-card">
          <div className="hz-cardhead">
            <h3>Recent transactions</h3>
            <span className="hz-cardsub">Newest first</span>
          </div>
          <ul className="hz-list">
            {recentTransactions(6).map((t) => (
              <TxRow key={t.id} t={t} />
            ))}
          </ul>
        </div>
        <UpcomingCard />
      </div>

      <div className="hz-grid two">
        <div className="hz-card">
          <div className="hz-cardhead">
            <h3>Largest purchases</h3>
            <span className="hz-cardsub">{MONTH_LABEL}</span>
          </div>
          <ul className="hz-list">
            {largestPurchases(CURRENT_YM, 5).map((t) => (
              <TxRow key={t.id} t={t} />
            ))}
          </ul>
        </div>
        <div className="hz-card">
          <div className="hz-cardhead">
            <h3>Excluded activity</h3>
            <span className="hz-cardsub">Not counted as spending</span>
          </div>
          <p style={{ margin: '4px 0 0', color: 'var(--hz-muted)', lineHeight: 1.5 }}>
            <b style={{ fontSize: 30, color: 'var(--hz-text)', display: 'block', letterSpacing: '-0.02em' }}>
              {formatDollarsAbs(excluded)}
            </b>
            in card payments, transfers, fees and interest are kept out of your spending totals so the picture
            stays honest.
          </p>
        </div>
      </div>
    </>
  );
}

/* ------------------------------------------------------------- Transactions */

function HorizonTransactions() {
  const [q, setQ] = useState('');
  const rows = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (!query) return allTxns;
    return allTxns.filter(
      (t) =>
        t.merchant.toLowerCase().includes(query) || t.rawDescription.toLowerCase().includes(query),
    );
  }, [q]);

  return (
    <>
      <PageHead title="Transactions" subtitle={`${rows.length} transactions across all accounts`} />
      <div className="hz-toolbar">
        <input
          className="hz-search"
          type="search"
          placeholder="🔎  Search merchant or description…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search transactions"
        />
        <button type="button" className="hz-chip">
          Category ▾
        </button>
        <button type="button" className="hz-chip">
          Type ▾
        </button>
      </div>

      <div className="hz-card hz-card-flush">
        <div className="hz-tablewrap">
          <table className="hz-table">
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Merchant</th>
                <th scope="col">Account</th>
                <th scope="col">Category</th>
                <th scope="col" className="num">
                  Amount
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => {
                const cat = t.categoryId ? categoryById[t.categoryId] : null;
                const positive = t.amountCents > 0;
                return (
                  <tr key={t.id} className={!t.includedInSpending ? 'excluded' : ''}>
                    <td className="hz-muted">{formatShortDate(t.date)}</td>
                    <td>
                      <div className="hz-cellmerch">
                        <span
                          className="hz-ico"
                          style={{ background: (cat?.color ?? '#94a3b8') + '26' }}
                          aria-hidden
                        >
                          {cat?.icon ?? '❓'}
                        </span>
                        <span className="hz-cellname">
                          <b>{t.merchant}</b>
                          <span>{t.rawDescription}</span>
                        </span>
                      </div>
                    </td>
                    <td className="hz-muted">{accountById[t.accountId]?.name}</td>
                    <td>
                      {cat ? (
                        <span
                          className="hz-pill"
                          style={{
                            background: cat.color + '22',
                            color: cat.color,
                            borderColor: cat.color + '55',
                          }}
                        >
                          <span aria-hidden>{cat.icon}</span> {cat.name}
                        </span>
                      ) : (
                        <span className="hz-pill hz-pill-none">
                          <span aria-hidden>❓</span> Uncategorized
                        </span>
                      )}
                      {!t.includedInSpending && <span className="hz-tag-excl">excluded</span>}
                    </td>
                    <td className={`num ${positive ? 'hz-num-pos' : 'hz-num'}`}>
                      {positive ? '+' : ''}
                      {formatCents(t.amountCents)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

/* -------------------------------------------------------------------- Review */

function HorizonReview() {
  const queue = reviewQueue();
  const [idx, setIdx] = useState(0);
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [done, setDone] = useState<Set<string>>(new Set());

  const t = queue[idx];
  const completed = done.size;

  if (!t || completed >= queue.length) {
    return (
      <>
        <PageHead title="Review" subtitle="Category clean-up" />
        <div className="hz-review">
          <div className="hz-card hz-empty">🎉 All caught up — every transaction is categorised.</div>
        </div>
      </>
    );
  }

  const suggested = t.categoryId ? categoryById[t.categoryId] : null;
  const selectedId = choice[t.id] ?? t.categoryId ?? '';
  const positive = t.amountCents > 0;
  const conf = Math.round((t.confidence ?? 0) * 100);
  const progressPct = (completed / queue.length) * 100;

  function advance() {
    setDone((prev) => {
      const next = new Set(prev);
      next.add(t.id);
      return next;
    });
    setIdx((i) => Math.min(queue.length, i + 1));
  }

  return (
    <>
      <PageHead title="Review" subtitle={`${queue.length - completed} left to categorise`} />
      <div className="hz-review">
        <div className="hz-progresswrap">
          <div className="hz-progress-top">
            <span>
              {completed} of {queue.length} done
            </span>
            <span>{Math.round(progressPct)}%</span>
          </div>
          <div
            className="hz-progress"
            role="progressbar"
            aria-valuenow={completed}
            aria-valuemin={0}
            aria-valuemax={queue.length}
            aria-label="Review progress"
          >
            <span style={{ width: `${progressPct}%` }} />
          </div>
        </div>

        <div className="hz-card hz-reviewcard">
          <div className="hz-reviewtop">
            <span
              className="hz-ico hz-ico-lg"
              style={{ background: (categoryById[selectedId]?.color ?? suggested?.color ?? '#94a3b8') + '26' }}
              aria-hidden
            >
              {categoryById[selectedId]?.icon ?? suggested?.icon ?? '❓'}
            </span>
            <div>
              <h2>{t.merchant}</h2>
              <p>{t.rawDescription}</p>
            </div>
            <span className={`hz-reviewamt ${positive ? 'pos' : ''}`}>
              {positive ? '+' : ''}
              {formatCentsAbs(t.amountCents)}
            </span>
          </div>

          <div className="hz-reviewmeta">
            <span>📅 {formatShortDate(t.date)}</span>
            <span>💳 {accountById[t.accountId]?.name}</span>
          </div>

          {suggested && (
            <div className="hz-suggestbox">
              <span className="hz-conf-ring" style={{ ['--p' as string]: conf }} aria-hidden>
                <span>{conf}%</span>
              </span>
              <span className="hz-suggest-txt">
                <b>
                  Suggested: {suggested.icon} {suggested.name}
                </b>
                <span>{t.reason ?? 'Based on merchant history.'}</span>
              </span>
            </div>
          )}

          <div className="hz-secttitle">Choose a category</div>
          <div className="hz-catgrid" role="group" aria-label="Choose a category">
            {REVIEW_CATEGORIES.map((c) => {
              const isSel = selectedId === c.id;
              const isSuggested = suggested?.id === c.id;
              return (
                <button
                  key={c.id}
                  type="button"
                  className={`hz-catbtn ${isSel ? 'selected' : ''}`}
                  style={{ ['--c' as string]: c.color }}
                  aria-pressed={isSel}
                  onClick={() => setChoice((prev) => ({ ...prev, [t.id]: c.id }))}
                >
                  <span className="hz-catemoji" aria-hidden>
                    {c.icon}
                  </span>
                  {c.name}
                  {isSuggested && <em>suggested</em>}
                </button>
              );
            })}
          </div>

          <label className="hz-remember">
            <input type="checkbox" defaultChecked />
            Remember <b>&nbsp;{t.merchant}&nbsp;</b> for future transactions
          </label>

          <div className="hz-reviewactions">
            <button type="button" className="hz-btn ghost" onClick={advance}>
              Skip
            </button>
            <button type="button" className="hz-btn primary" onClick={advance} disabled={!selectedId}>
              Confirm {categoryById[selectedId]?.name ?? 'category'} →
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/* --------------------------------------------------------------------- meta */

const horizon: Direction = {
  meta: {
    id: 'horizon',
    name: 'Horizon',
    tagline: 'Bold & colourful',
    description:
      'Confident, high-contrast, and playful: a vivid gradient hero, warm-orange accents, big rounded cards with depth, and expressive charts — next-gen consumer-fintech energy.',
    accent: '#f97316',
  },
  Dashboard: () => (
    <Frame active="dashboard">
      <HorizonDashboard />
    </Frame>
  ),
  Transactions: () => (
    <Frame active="transactions">
      <HorizonTransactions />
    </Frame>
  ),
  Review: () => (
    <Frame active="review">
      <HorizonReview />
    </Frame>
  ),
};

export default horizon;
