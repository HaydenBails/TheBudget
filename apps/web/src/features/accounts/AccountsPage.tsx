import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { useCurrentProfile } from '../profiles/ProfileContext';
import {
  useAccounts,
  useArchiveAccount,
  useCreateAccount,
  useRestoreAccount,
  useUpdateAccount,
} from './api';
import { CARD_COLORS, ISSUERS, type Account, type AccountCreate, type IssuerCode } from './types';
import './accounts.css';

interface FormValues {
  issuer: IssuerCode;
  display_name: string;
  color: string;
  last4: string;
}

function AccountForm({
  initial,
  submitLabel,
  pending,
  error,
  onSubmit,
  onCancel,
}: {
  initial?: Account;
  submitLabel: string;
  pending: boolean;
  error: ApiError | null;
  onSubmit: (v: AccountCreate) => void;
  onCancel: () => void;
}) {
  const [v, setV] = useState<FormValues>({
    issuer: initial?.issuer ?? 'TD',
    display_name: initial?.display_name ?? '',
    color: initial?.color ?? CARD_COLORS[0],
    last4: initial?.last4 ?? '',
  });
  const [touched, setTouched] = useState(false);

  const last4Invalid = v.last4.length > 0 && !/^\d{4,5}$/.test(v.last4);
  const nameInvalid = v.display_name.trim().length === 0;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (nameInvalid || last4Invalid) return;
    onSubmit({
      issuer: v.issuer,
      display_name: v.display_name.trim(),
      color: v.color,
      last4: v.last4 ? v.last4 : null,
    });
  }

  return (
    <form className="app-card ac-form" onSubmit={submit}>
      <div className="ac-form-grid">
        <div className="ac-field">
          <label htmlFor="ac-issuer" className="pf-label">Issuer</label>
          <select
            id="ac-issuer"
            className="pf-input"
            value={v.issuer}
            onChange={(e) => setV({ ...v, issuer: e.target.value as IssuerCode })}
          >
            {ISSUERS.map((i) => (
              <option key={i.code} value={i.code}>{i.label}</option>
            ))}
          </select>
        </div>
        <div className="ac-field">
          <label htmlFor="ac-name" className="pf-label">Display name</label>
          <input
            id="ac-name"
            className="pf-input"
            value={v.display_name}
            onChange={(e) => setV({ ...v, display_name: e.target.value })}
            placeholder="e.g. TD Cash Back Visa"
            maxLength={100}
          />
          {touched && nameInvalid && <p className="pf-error" role="alert">A display name is required.</p>}
        </div>
        <div className="ac-field">
          <label htmlFor="ac-last4" className="pf-label">Last digits <span className="ac-optional">(optional)</span></label>
          <input
            id="ac-last4"
            className="pf-input"
            value={v.last4}
            inputMode="numeric"
            onChange={(e) => setV({ ...v, last4: e.target.value.replace(/\D/g, '').slice(0, 5) })}
            placeholder="4821"
          />
          {touched && last4Invalid && <p className="pf-error" role="alert">Enter 4 or 5 digits, or leave blank.</p>}
        </div>
      </div>

      <div className="ac-field">
        <span className="pf-label" id="ac-color-label">Card colour</span>
        <div className="ac-swatches" role="radiogroup" aria-labelledby="ac-color-label">
          {CARD_COLORS.map((c) => (
            <button
              key={c}
              type="button"
              role="radio"
              aria-checked={v.color === c}
              aria-label={`Colour ${c}`}
              className={`ac-swatch ${v.color === c ? 'selected' : ''}`}
              style={{ background: c }}
              onClick={() => setV({ ...v, color: c })}
            />
          ))}
        </div>
      </div>

      {error && <p className="pf-error" role="alert">{error.fieldError('last4') ?? error.fieldError('display_name') ?? error.message}</p>}

      <div className="ac-form-actions">
        <button type="submit" className="app-btn primary" disabled={pending}>
          {pending ? 'Saving…' : submitLabel}
        </button>
        <button type="button" className="app-btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function AccountRow({
  account,
  onEdit,
  onArchive,
  archiving,
}: {
  account: Account;
  onEdit: () => void;
  onArchive: () => void;
  archiving: boolean;
}) {
  const [confirm, setConfirm] = useState(false);
  return (
    <li className="app-card ac-row">
      <span className="ac-card-chip" style={{ background: account.color }} aria-hidden>
        {account.issuer}
      </span>
      <div className="ac-meta">
        <div className="ac-name">{account.display_name}</div>
        <div className="ac-sub">
          {account.issuer} · {account.currency}
          {account.last4 ? ` · ····${account.last4}` : ''}
        </div>
      </div>
      {!confirm ? (
        <div className="pf-actions">
          <button type="button" className="app-btn" onClick={onEdit}>Edit</button>
          <button type="button" className="app-btn pf-danger" onClick={() => setConfirm(true)}>Archive</button>
        </div>
      ) : (
        <div className="pf-actions pf-confirm" role="group" aria-label={`Confirm archiving ${account.display_name}`}>
          <span className="pf-confirm-text">Archive this account? History is kept and can be restored.</span>
          <button type="button" className="app-btn pf-danger" disabled={archiving} onClick={onArchive}>
            {archiving ? 'Archiving…' : 'Archive'}
          </button>
          <button type="button" className="app-btn" onClick={() => setConfirm(false)}>Cancel</button>
        </div>
      )}
    </li>
  );
}

export function AccountsPage() {
  const { currentProfile, currentProfileId } = useCurrentProfile();
  const { data, isLoading, isError, error, refetch } = useAccounts(currentProfileId, true);

  const create = useCreateAccount(currentProfileId ?? 0);
  const update = useUpdateAccount(currentProfileId ?? 0);
  const archive = useArchiveAccount(currentProfileId ?? 0);
  const restore = useRestoreAccount(currentProfileId ?? 0);

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);

  if (currentProfileId == null) {
    return (
      <>
        <div className="app-head"><div><h1>Accounts</h1><p>Manage the cards for the active profile.</p></div></div>
        <div className="app-card app-placeholder">
          <span className="app-badge" aria-hidden>▤</span>
          <h2>No profile selected</h2>
          <p>Accounts belong to a profile. Create or select a profile first, then add its cards here.</p>
          <Link className="app-btn primary" to="/app/profiles" style={{ marginTop: 14 }}>Go to profiles</Link>
        </div>
      </>
    );
  }

  const list = data ?? [];
  const active = list.filter((a) => !a.is_archived);
  const archived = list.filter((a) => a.is_archived);
  const createError = create.error instanceof ApiError ? create.error : null;
  const updateError = update.error instanceof ApiError ? update.error : null;

  return (
    <>
      <div className="app-head">
        <div>
          <h1>Accounts</h1>
          <p>Cards for <b>{currentProfile?.name}</b> — fully isolated from other profiles.</p>
        </div>
        {!creating && !editing && (
          <button type="button" className="app-btn primary" onClick={() => { setCreating(true); create.reset(); }}>
            + Add account
          </button>
        )}
      </div>

      {creating && (
        <AccountForm
          submitLabel="Add account"
          pending={create.isPending}
          error={createError}
          onSubmit={(body) => create.mutate(body, { onSuccess: () => setCreating(false) })}
          onCancel={() => setCreating(false)}
        />
      )}

      {editing && (
        <AccountForm
          initial={editing}
          submitLabel="Save changes"
          pending={update.isPending}
          error={updateError}
          onSubmit={(body) => update.mutate({ id: editing.id, body }, { onSuccess: () => setEditing(null) })}
          onCancel={() => setEditing(null)}
        />
      )}

      {isLoading && <div className="app-card pf-state">Loading accounts…</div>}

      {isError && (
        <div className="app-card pf-state pf-state-error" role="alert">
          <p>{error instanceof ApiError ? error.message : 'Could not load accounts.'}</p>
          <button type="button" className="app-btn" onClick={() => refetch()}>Try again</button>
        </div>
      )}

      {!isLoading && !isError && active.length === 0 && archived.length === 0 && !creating && (
        <div className="app-card app-placeholder">
          <span className="app-badge" aria-hidden>▤</span>
          <h2>No accounts yet</h2>
          <p>Add the credit cards you want to track for {currentProfile?.name}. You can archive them later without losing history.</p>
          <button type="button" className="app-btn primary" style={{ marginTop: 14 }} onClick={() => setCreating(true)}>+ Add account</button>
        </div>
      )}

      {active.length > 0 && !editing && (
        <ul className="pf-list">
          {active.map((a) => (
            <AccountRow
              key={a.id}
              account={a}
              archiving={archive.isPending}
              onEdit={() => { setEditing(a); update.reset(); }}
              onArchive={() => archive.mutate(a.id)}
            />
          ))}
        </ul>
      )}

      {archived.length > 0 && !editing && (
        <>
          <h2 className="pf-section">Archived</h2>
          <ul className="pf-list">
            {archived.map((a) => (
              <li key={a.id} className="app-card ac-row pf-archived">
                <span className="ac-card-chip" style={{ background: a.color }} aria-hidden>{a.issuer}</span>
                <div className="ac-meta">
                  <div className="ac-name">{a.display_name}</div>
                  <div className="ac-sub">Archived{a.last4 ? ` · ····${a.last4}` : ''}</div>
                </div>
                <div className="pf-actions">
                  <button type="button" className="app-btn" disabled={restore.isPending} onClick={() => restore.mutate(a.id)}>Restore</button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
