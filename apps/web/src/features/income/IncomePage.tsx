import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { useCurrentProfile } from '../profiles/ProfileContext';
import { formatCad, parseCadToCents, centsToInput } from '../transactions/money';
import {
  useCreateIncome,
  useDeleteIncome,
  useIncomeOccurrences,
  useIncomeSchedules,
  useUpdateIncome,
} from './api';
import {
  FREQUENCY_LABEL,
  monthlyEquivalentCents,
  type Frequency,
  type IncomeSchedule,
  type IncomeScheduleCreate,
} from './types';
import './income.css';

const pad = (n: number) => String(n).padStart(2, '0');
function monthBounds(now: Date) {
  const y = now.getFullYear();
  const m = now.getMonth();
  return {
    from: `${y}-${pad(m + 1)}-01`,
    to: `${y}-${pad(m + 1)}-${pad(new Date(y, m + 1, 0).getDate())}`,
    label: now.toLocaleDateString('en-CA', { month: 'long', year: 'numeric' }),
  };
}
function formatDay(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' });
}

interface FormValues {
  name: string;
  amount: string;
  frequency: Frequency;
  start_date: string;
  end_date: string;
  notes: string;
}

function IncomeForm({
  initial,
  submitLabel,
  pending,
  error,
  onSubmit,
  onCancel,
}: {
  initial?: IncomeSchedule;
  submitLabel: string;
  pending: boolean;
  error: ApiError | null;
  onSubmit: (v: IncomeScheduleCreate) => void;
  onCancel: () => void;
}) {
  const [v, setV] = useState<FormValues>({
    name: initial?.name ?? '',
    amount: initial ? centsToInput(initial.amount_cents) : '',
    frequency: initial?.frequency ?? 'biweekly',
    start_date: initial?.start_date ?? new Date().toISOString().slice(0, 10),
    end_date: initial?.end_date ?? '',
    notes: initial?.notes ?? '',
  });
  const [touched, setTouched] = useState(false);
  const cents = parseCadToCents(v.amount);
  const nameInvalid = v.name.trim().length === 0;
  const amountInvalid = cents == null || cents <= 0;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (nameInvalid || amountInvalid || !v.start_date) return;
    onSubmit({
      name: v.name.trim(),
      amount_cents: cents as number,
      frequency: v.frequency,
      start_date: v.start_date,
      end_date: v.end_date || null,
      notes: v.notes.trim() || null,
    });
  }

  return (
    <form className="app-card inc-form" onSubmit={submit}>
      <div className="inc-form-grid">
        <div className="inc-field">
          <label htmlFor="inc-name" className="pf-label">Source</label>
          <input id="inc-name" className="pf-input" value={v.name} maxLength={100} placeholder="e.g. Acme payroll" onChange={(e) => setV({ ...v, name: e.target.value })} />
          {touched && nameInvalid && <p className="pf-error" role="alert">A source name is required.</p>}
        </div>
        <div className="inc-field">
          <label htmlFor="inc-amount" className="pf-label">Net amount</label>
          <div className="inc-money"><span aria-hidden>$</span><input id="inc-amount" className="pf-input" inputMode="decimal" placeholder="0.00" value={v.amount} onChange={(e) => setV({ ...v, amount: e.target.value })} /></div>
          {touched && amountInvalid && <p className="pf-error" role="alert">Enter an amount greater than $0.</p>}
        </div>
        <div className="inc-field">
          <label htmlFor="inc-freq" className="pf-label">Frequency</label>
          <select id="inc-freq" className="pf-input" value={v.frequency} onChange={(e) => setV({ ...v, frequency: e.target.value as Frequency })}>
            <option value="weekly">Weekly</option>
            <option value="biweekly">Every 2 weeks</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        <div className="inc-field">
          <label htmlFor="inc-start" className="pf-label">First payment</label>
          <input id="inc-start" type="date" className="pf-input" value={v.start_date} onChange={(e) => setV({ ...v, start_date: e.target.value })} />
        </div>
        <div className="inc-field">
          <label htmlFor="inc-end" className="pf-label">Ends (optional)</label>
          <input id="inc-end" type="date" className="pf-input" value={v.end_date} min={v.start_date} onChange={(e) => setV({ ...v, end_date: e.target.value })} />
        </div>
      </div>
      {error && <p className="pf-error" role="alert">{error.fieldError('amount_cents') ?? error.fieldError('end_date') ?? error.message}</p>}
      <div className="inc-form-actions">
        <button type="submit" className="app-btn primary" disabled={pending}>{pending ? 'Saving…' : submitLabel}</button>
        <button type="button" className="app-btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

export function IncomePage() {
  const { currentProfile, currentProfileId } = useCurrentProfile();
  const { data, isLoading, isError, error, refetch } = useIncomeSchedules(currentProfileId);
  const month = useMemo(() => monthBounds(new Date()), []);
  const occurrences = useIncomeOccurrences(currentProfileId, month.from, month.to);

  const create = useCreateIncome(currentProfileId ?? 0);
  const update = useUpdateIncome(currentProfileId ?? 0);
  const remove = useDeleteIncome(currentProfileId ?? 0);
  const pending = create.isPending || update.isPending || remove.isPending;

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<IncomeSchedule | null>(null);

  if (currentProfileId == null) {
    return (
      <>
        <div className="app-head"><div><h1>Income</h1><p>Scheduled income for the active profile.</p></div></div>
        <div className="app-card app-placeholder">
          <h2>No profile selected</h2>
          <p>Income schedules belong to a profile. Create or select a profile first.</p>
          <Link className="app-btn primary" to="/app/profiles" style={{ marginTop: 14 }}>Go to profiles</Link>
        </div>
      </>
    );
  }

  const schedules = data ?? [];
  const active = schedules.filter((s) => s.is_active);
  const monthlyTotal = active.reduce((sum, s) => sum + monthlyEquivalentCents(s), 0);
  const expectedThisMonth = (occurrences.data ?? []).reduce((sum, o) => sum + o.amount_cents, 0);
  const createError = create.error instanceof ApiError ? create.error : null;
  const updateError = update.error instanceof ApiError ? update.error : null;

  return (
    <>
      <div className="app-head">
        <div>
          <h1>Income</h1>
          <p>Scheduled income for <b>{currentProfile?.name}</b>. Used to estimate what's available to save.</p>
        </div>
        {!creating && !editing && (
          <button type="button" className="app-btn primary" onClick={() => { setCreating(true); create.reset(); }}>+ Add income</button>
        )}
      </div>

      {schedules.length > 0 && (
        <div className="inc-summary app-card">
          <div><span className="inc-summary-k">Monthly-equivalent</span><span className="inc-summary-v">{formatCad(monthlyTotal)}</span></div>
          <div><span className="inc-summary-k">Expected in {month.label}</span><span className="inc-summary-v">{formatCad(expectedThisMonth)}</span></div>
          <div><span className="inc-summary-k">Active sources</span><span className="inc-summary-v">{active.length}</span></div>
        </div>
      )}

      {creating && (
        <IncomeForm submitLabel="Add income" pending={create.isPending} error={createError}
          onSubmit={(body) => create.mutate(body, { onSuccess: () => setCreating(false) })}
          onCancel={() => setCreating(false)} />
      )}
      {editing && (
        <IncomeForm initial={editing} submitLabel="Save changes" pending={update.isPending} error={updateError}
          onSubmit={(body) => update.mutate({ id: editing.id, body }, { onSuccess: () => setEditing(null) })}
          onCancel={() => setEditing(null)} />
      )}

      {isLoading && <div className="app-card pf-state">Loading income…</div>}
      {isError && (
        <div className="app-card pf-state pf-state-error" role="alert">
          <p>{error instanceof ApiError ? error.message : 'Could not load income schedules.'}</p>
          <button type="button" className="app-btn" onClick={() => refetch()}>Try again</button>
        </div>
      )}

      {!isLoading && !isError && schedules.length === 0 && !creating && (
        <div className="app-card app-placeholder">
          <h2>No income scheduled yet</h2>
          <p>Add your paycheque or other regular income so the dashboard can estimate what's left to save after spending and recurring charges.</p>
          <button type="button" className="app-btn primary" style={{ marginTop: 14 }} onClick={() => { setCreating(true); create.reset(); }}>+ Add income</button>
        </div>
      )}

      {!editing && schedules.length > 0 && (
        <ul className="inc-list">
          {schedules.map((s) => (
            <li key={s.id} className={`app-card inc-row ${s.is_active ? '' : 'inc-paused'}`}>
              <div className="inc-meta">
                <div className="inc-name">{s.name}{!s.is_active && <span className="inc-badge">Paused</span>}</div>
                <div className="inc-sub">
                  {FREQUENCY_LABEL[s.frequency]} · {formatCad(s.amount_cents)}
                  {s.is_active && s.next_expected_date && <> · next {formatDay(s.next_expected_date)}</>}
                </div>
              </div>
              <div className="inc-amt">
                <div className="inc-amt-v">{formatCad(monthlyEquivalentCents(s))}<span>/mo</span></div>
              </div>
              <div className="inc-actions">
                <button type="button" className="app-btn" disabled={pending} onClick={() => update.mutate({ id: s.id, body: { is_active: !s.is_active } })}>
                  {s.is_active ? 'Pause' : 'Resume'}
                </button>
                <button type="button" className="app-btn" onClick={() => { setEditing(s); update.reset(); }}>Edit</button>
                <button type="button" className="app-btn pf-danger" disabled={pending} onClick={() => remove.mutate(s.id)}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
