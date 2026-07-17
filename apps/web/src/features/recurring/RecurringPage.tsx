import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { useCurrentProfile } from '../profiles/ProfileContext';
import { useCategories } from '../categories/api';
import { CategoryIcon } from '../categories/CategoryIcon';
import { formatCad } from '../transactions/money';
import {
  useDeleteRecurring,
  useDetectRecurring,
  useRecurringSeries,
  useUpdateRecurring,
} from './api';
import {
  CADENCE_LABEL,
  annualCostCents,
  monthlyCostCents,
  type Confidence,
  type RecurringSeries,
  type RecurringStatus,
} from './types';
import type { Category } from '../categories/types';
import './recurring.css';

function formatDay(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' });
}
function daysUntil(iso: string) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${iso}T00:00:00`);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}
function dueLabel(iso: string) {
  const d = daysUntil(iso);
  if (d < 0) return `${Math.abs(d)}d overdue`;
  if (d === 0) return 'Due today';
  if (d === 1) return 'Due tomorrow';
  return `in ${d}d`;
}

const confidenceClass: Record<Confidence, string> = { high: 'high', medium: 'med', low: 'low' };
const confidenceLabel: Record<Confidence, string> = { high: 'High', medium: 'Medium', low: 'Low' };

const STATUS_ACTIONS: { value: RecurringStatus; label: string }[] = [
  { value: 'keep', label: 'Keep' },
  { value: 'review', label: 'Review' },
  { value: 'cancel', label: 'Cancel' },
  { value: 'ignored', label: 'Ignore' },
];

function SeriesCard({
  series,
  category,
  pending,
  onStatus,
  onDelete,
}: {
  series: RecurringSeries;
  category?: Category;
  pending: boolean;
  onStatus: (status: RecurringStatus) => void;
  onDelete: () => void;
}) {
  const color = category?.color ?? '#8a90a6';
  const variable = series.amount_min_cents !== series.amount_max_cents;
  return (
    <li className="app-card rc-card">
      <div className="rc-main">
        <span className="rc-icon" style={{ color, background: `color-mix(in srgb, ${color} 16%, transparent)` }} aria-hidden>
          <CategoryIcon name={category?.icon} />
        </span>
        <div className="rc-meta">
          <div className="rc-name">
            {series.display_name}
            <span className={`rc-conf ${confidenceClass[series.confidence]}`} title="Detection confidence">
              {confidenceLabel[series.confidence]}
            </span>
            {series.confirmed_by_user && <span className="rc-confirmed" title="Confirmed by you">✓ confirmed</span>}
          </div>
          <div className="rc-sub">
            {CADENCE_LABEL[series.cadence]} · {series.occurrence_count} charges · {category?.name ?? 'Uncategorised'}
          </div>
          <div className="rc-rationale">{series.rationale}</div>
        </div>
        <div className="rc-amounts">
          <div className="rc-amount">
            {variable
              ? `${formatCad(series.amount_min_cents)}–${formatCad(series.amount_max_cents)}`
              : formatCad(series.amount_cents)}
          </div>
          <div className="rc-cost">≈ {formatCad(monthlyCostCents(series))}/mo · {formatCad(annualCostCents(series))}/yr</div>
        </div>
      </div>
      <div className="rc-foot">
        <span className={`rc-due ${daysUntil(series.next_expected_date) < 0 ? 'over' : ''}`}>
          Next: {formatDay(series.next_expected_date)} <b>({dueLabel(series.next_expected_date)})</b>
        </span>
        <div className="rc-actions" role="group" aria-label={`Status for ${series.display_name}`}>
          {STATUS_ACTIONS.map((action) => (
            <button
              key={action.value}
              type="button"
              className={`rc-status-btn ${series.status === action.value ? 'active' : ''}`}
              aria-pressed={series.status === action.value}
              disabled={pending}
              onClick={() => onStatus(action.value)}
            >
              {action.label}
            </button>
          ))}
          <button type="button" className="rc-status-btn rc-remove" disabled={pending} onClick={onDelete} aria-label={`Remove ${series.display_name}`}>
            Remove
          </button>
        </div>
      </div>
    </li>
  );
}

export function RecurringPage() {
  const { currentProfile, currentProfileId } = useCurrentProfile();
  const categories = useCategories(currentProfileId, false);
  const { data, isLoading, isError, error, refetch } = useRecurringSeries(currentProfileId);
  const detect = useDetectRecurring(currentProfileId ?? 0);
  const update = useUpdateRecurring(currentProfileId ?? 0);
  const remove = useDeleteRecurring(currentProfileId ?? 0);
  const pending = detect.isPending || update.isPending || remove.isPending;

  const catById = useMemo(
    () => new Map<number, Category>((categories.data ?? []).map((c) => [c.id, c])),
    [categories.data],
  );

  if (currentProfileId == null) {
    return (
      <>
        <div className="app-head"><div><h1>Recurring</h1><p>Subscriptions and repeating charges for the active profile.</p></div></div>
        <div className="app-card app-placeholder">
          <h2>No profile selected</h2>
          <p>Recurring charges belong to a profile. Create or select a profile first.</p>
          <Link className="app-btn primary" to="/app/profiles" style={{ marginTop: 14 }}>Go to profiles</Link>
        </div>
      </>
    );
  }

  const series = data ?? [];
  const active = series.filter((s) => s.status !== 'ignored' && s.status !== 'ended');
  const dismissed = series.filter((s) => s.status === 'ignored' || s.status === 'ended');
  const monthlyTotal = active
    .filter((s) => s.status !== 'cancel')
    .reduce((sum, s) => sum + monthlyCostCents(s), 0);

  return (
    <>
      <div className="app-head">
        <div>
          <h1>Recurring charges</h1>
          <p>Subscriptions and repeating charges for <b>{currentProfile?.name}</b>, detected from your transactions.</p>
        </div>
        <button type="button" className="app-btn primary" disabled={pending} onClick={() => detect.mutate()}>
          {detect.isPending ? 'Detecting…' : 'Detect recurring'}
        </button>
      </div>

      {detect.error instanceof ApiError && (
        <div className="app-card pf-state pf-state-error" role="alert"><p>{detect.error.message}</p></div>
      )}

      {isLoading && <div className="app-card pf-state">Loading recurring charges…</div>}

      {isError && (
        <div className="app-card pf-state pf-state-error" role="alert">
          <p>{error instanceof ApiError ? error.message : 'Could not load recurring charges.'}</p>
          <button type="button" className="app-btn" onClick={() => refetch()}>Try again</button>
        </div>
      )}

      {!isLoading && !isError && series.length === 0 && (
        <div className="app-card app-placeholder">
          <h2>No recurring charges yet</h2>
          <p>Run detection to find subscriptions and repeating charges across your transaction history. You need at least two charges from the same merchant on a regular cadence.</p>
          <button type="button" className="app-btn primary" style={{ marginTop: 14 }} disabled={pending} onClick={() => detect.mutate()}>
            {detect.isPending ? 'Detecting…' : 'Detect recurring'}
          </button>
        </div>
      )}

      {active.length > 0 && (
        <>
          <div className="rc-summary app-card">
            <div><span className="rc-summary-k">Tracked</span><span className="rc-summary-v">{active.filter((s) => s.status !== 'cancel').length}</span></div>
            <div><span className="rc-summary-k">Est. monthly</span><span className="rc-summary-v">{formatCad(monthlyTotal)}</span></div>
            <div><span className="rc-summary-k">Est. yearly</span><span className="rc-summary-v">{formatCad(monthlyTotal * 12)}</span></div>
          </div>
          <ul className="rc-list">
            {active.map((s) => (
              <SeriesCard
                key={s.id}
                series={s}
                category={s.category_id != null ? catById.get(s.category_id) : undefined}
                pending={pending}
                onStatus={(status) => update.mutate({ id: s.id, body: { status, confirmed_by_user: true } })}
                onDelete={() => remove.mutate(s.id)}
              />
            ))}
          </ul>
        </>
      )}

      {dismissed.length > 0 && (
        <>
          <h2 className="pf-section">Ignored</h2>
          <ul className="rc-list">
            {dismissed.map((s) => (
              <li key={s.id} className="app-card rc-card rc-dismissed">
                <div className="rc-main">
                  <div className="rc-meta"><div className="rc-name">{s.display_name}</div><div className="rc-sub">{CADENCE_LABEL[s.cadence]} · {formatCad(s.amount_cents)}</div></div>
                  <button type="button" className="rc-status-btn" disabled={pending} onClick={() => update.mutate({ id: s.id, body: { status: 'keep', confirmed_by_user: true } })}>Restore</button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
