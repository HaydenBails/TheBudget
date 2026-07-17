import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { useCurrentProfile } from '../profiles/ProfileContext';
import { useCategories } from '../categories/api';
import { CategoryIcon } from '../categories/CategoryIcon';
import { useTransactions } from '../transactions/api';
import type { TransactionFilters } from '../transactions/types';
import { formatCad, parseCadToCents, centsToInput } from '../transactions/money';
import { useBudgets, useCreateBudget, useDeleteBudget, useUpdateBudget } from './api';
import { budgetLevel, budgetLevelLabel, monthSpending, type BudgetLevel } from './budgetMath';
import type { Budget } from './types';
import './budgets.css';

const pad = (n: number) => String(n).padStart(2, '0');
const monthKey = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
function monthLabel(ym: string) {
  return new Date(`${ym}-01T00:00:00`).toLocaleDateString('en-CA', { month: 'long', year: 'numeric' });
}
function shiftMonth(ym: string, delta: number) {
  const [y, m] = ym.split('-').map(Number);
  return monthKey(new Date(y, m - 1 + delta, 1));
}
function monthBounds(ym: string) {
  const [y, m] = ym.split('-').map(Number);
  const last = new Date(y, m, 0).getDate();
  return { from: `${ym}-01`, to: `${ym}-${pad(last)}` };
}

const levelClass: Record<BudgetLevel, string> = { ok: 'ok', warn: 'warn', high: 'high', over: 'over' };

function ProgressBar({ spent, limit }: { spent: number; limit: number }) {
  const level = budgetLevel(spent, limit);
  const pct = limit > 0 ? Math.min(100, Math.max(0, (spent / limit) * 100)) : 0;
  const pctLabel = limit > 0 ? Math.round((spent / limit) * 100) : 0;
  return (
    <div className="bg-progress">
      <div
        className={`bg-bar ${levelClass[level]}`}
        role="progressbar"
        aria-valuenow={pctLabel}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${pctLabel}% of budget used — ${budgetLevelLabel[level]}`}
      >
        <span style={{ width: `${pct}%` }} />
      </div>
      <div className="bg-progress-meta">
        <span className="bg-spent">{formatCad(spent)} <span className="bg-of">of</span> {formatCad(limit)}</span>
        <span className={`bg-tag ${levelClass[level]}`}>{pctLabel}% · {budgetLevelLabel[level]}</span>
      </div>
    </div>
  );
}

function BudgetRow({
  label,
  spent,
  budget,
  color,
  icon,
  pending,
  onSave,
  onRemove,
}: {
  label: React.ReactNode;
  spent: number;
  budget?: Budget;
  color?: string;
  icon?: React.ReactNode;
  pending: boolean;
  onSave: (cents: number) => void;
  onRemove: () => void;
}) {
  const [draft, setDraft] = useState(budget ? centsToInput(budget.limit_cents) : '');
  const parsed = parseCadToCents(draft);
  const changed = budget ? parsed !== budget.limit_cents : draft.trim() !== '';
  const invalid = draft.trim() !== '' && (parsed == null || parsed <= 0);

  return (
    <li className="app-card bg-row">
      <div className="bg-row-head">
        <div className="bg-row-label">
          {icon && <span className="bg-icon" style={color ? { color, background: `color-mix(in srgb, ${color} 16%, transparent)` } : undefined} aria-hidden>{icon}</span>}
          <span className="bg-name">{label}</span>
        </div>
        <div className="bg-row-edit">
          <div className="bg-input-wrap">
            <span aria-hidden>$</span>
            <input
              className="pf-input bg-input"
              inputMode="decimal"
              placeholder="0.00"
              aria-label={`Monthly limit for ${typeof label === 'string' ? label : 'budget'}`}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
          </div>
          <button
            type="button"
            className="app-btn primary bg-save"
            disabled={pending || !changed || invalid || parsed == null}
            onClick={() => parsed != null && onSave(parsed)}
          >
            {budget ? 'Update' : 'Set'}
          </button>
          {budget && (
            <button type="button" className="app-btn bg-remove" disabled={pending} onClick={onRemove} aria-label={`Remove budget for ${typeof label === 'string' ? label : 'this category'}`}>
              Remove
            </button>
          )}
        </div>
      </div>
      {invalid && <p className="pf-error" role="alert">Enter an amount greater than $0.</p>}
      {budget ? (
        <ProgressBar spent={spent} limit={budget.limit_cents} />
      ) : (
        <p className="bg-unset">{spent > 0 ? `${formatCad(spent)} spent so far — no limit set.` : 'No limit set for this month.'}</p>
      )}
    </li>
  );
}

export function BudgetsPage() {
  const { currentProfile, currentProfileId } = useCurrentProfile();
  const [month, setMonth] = useState(() => monthKey(new Date()));

  const categories = useCategories(currentProfileId, false);
  const budgets = useBudgets(currentProfileId, month);

  const filters = useMemo<TransactionFilters>(() => {
    const { from, to } = monthBounds(month);
    return {
      accountId: null,
      categoryId: null,
      type: null,
      dateFrom: from,
      dateTo: to,
      includedInSpending: null,
      search: '',
      includeDeleted: false,
    };
  }, [month]);
  const transactions = useTransactions(currentProfileId, filters);

  const create = useCreateBudget(currentProfileId ?? 0);
  const update = useUpdateBudget(currentProfileId ?? 0);
  const remove = useDeleteBudget(currentProfileId ?? 0);
  const pending = create.isPending || update.isPending || remove.isPending;

  const spending = useMemo(
    () => monthSpending(transactions.data ?? [], month),
    [transactions.data, month],
  );

  if (currentProfileId == null) {
    return (
      <>
        <div className="app-head"><div><h1>Budgets</h1><p>Monthly spending targets for the active profile.</p></div></div>
        <div className="app-card app-placeholder">
          <h2>No profile selected</h2>
          <p>Budgets belong to a profile. Create or select a profile first.</p>
          <Link className="app-btn primary" to="/app/profiles" style={{ marginTop: 14 }}>Go to profiles</Link>
        </div>
      </>
    );
  }

  const budgetList = budgets.data ?? [];
  const overall = budgetList.find((b) => b.category_id == null);
  const byCategoryBudget = new Map<number, Budget>(
    budgetList.filter((b) => b.category_id != null).map((b) => [b.category_id as number, b]),
  );
  const spendCategories = (categories.data ?? []).filter((c) => !c.is_archived && !c.excluded_from_spending);

  function saveBudget(categoryId: number | null, cents: number) {
    const existing = categoryId == null ? overall : byCategoryBudget.get(categoryId);
    if (existing) {
      update.mutate({ id: existing.id, body: { limit_cents: cents } });
    } else {
      create.mutate({ category_id: categoryId, period_month: month, limit_cents: cents });
    }
  }

  const err = (create.error ?? update.error ?? remove.error) instanceof ApiError
    ? (create.error ?? update.error ?? remove.error) as ApiError
    : null;

  return (
    <>
      <div className="app-head">
        <div>
          <h1>Budgets</h1>
          <p>Monthly spending targets for <b>{currentProfile?.name}</b>. Progress uses spending counted this month.</p>
        </div>
        <div className="bg-month" role="group" aria-label="Select month">
          <button type="button" className="app-btn bg-month-btn" onClick={() => setMonth((m) => shiftMonth(m, -1))} aria-label="Previous month">‹</button>
          <span className="bg-month-label">{monthLabel(month)}</span>
          <button type="button" className="app-btn bg-month-btn" onClick={() => setMonth((m) => shiftMonth(m, 1))} aria-label="Next month">›</button>
        </div>
      </div>

      {err && <div className="app-card pf-state pf-state-error" role="alert"><p>{err.message}</p></div>}

      <section aria-labelledby="bg-overall-h">
        <h2 className="pf-section" id="bg-overall-h">Overall monthly budget</h2>
        <ul className="bg-list">
          <BudgetRow
            key={`overall-${overall?.id ?? 'none'}`}
            label="All spending"
            spent={spending.overall}
            budget={overall}
            pending={pending}
            onSave={(cents) => saveBudget(null, cents)}
            onRemove={() => overall && remove.mutate(overall.id)}
          />
        </ul>
      </section>

      <section aria-labelledby="bg-cat-h">
        <h2 className="pf-section" id="bg-cat-h">Category budgets</h2>
        {categories.isLoading ? (
          <div className="app-card pf-state">Loading categories…</div>
        ) : spendCategories.length === 0 ? (
          <div className="app-card pf-state">No spending categories yet. <Link to="/app/categories">Add categories</Link> to budget them.</div>
        ) : (
          <ul className="bg-list">
            {spendCategories.map((c) => {
              const b = byCategoryBudget.get(c.id);
              return (
                <BudgetRow
                  key={`${c.id}-${b?.id ?? 'none'}`}
                  label={c.name}
                  color={c.color}
                  icon={<CategoryIcon name={c.icon} />}
                  spent={spending.byCategory.get(c.id) ?? 0}
                  budget={b}
                  pending={pending}
                  onSave={(cents) => saveBudget(c.id, cents)}
                  onRemove={() => b && remove.mutate(b.id)}
                />
              );
            })}
          </ul>
        )}
      </section>
    </>
  );
}
