import { useMemo, useState } from 'react';
import { ApiError } from '../../api/client';
import {
  useArchiveProfile,
  useCreateProfile,
  useProfiles,
  useRestoreProfile,
  useUpdateProfile,
} from './api';
import { useCurrentProfile } from './ProfileContext';
import type { Profile } from './types';
import './profiles.css';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' });
}

export function ProfilesPage() {
  // Fetch everything (active + archived) for management.
  const { data, isLoading, isError, error, refetch } = useProfiles(true);
  const { currentProfileId, selectProfile } = useCurrentProfile();

  const create = useCreateProfile();
  const update = useUpdateProfile();
  const archive = useArchiveProfile();
  const restore = useRestoreProfile();

  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [confirmArchiveId, setConfirmArchiveId] = useState<number | null>(null);

  const { active, archived } = useMemo(() => {
    const list = data ?? [];
    return {
      active: list.filter((p) => !p.is_archived),
      archived: list.filter((p) => p.is_archived),
    };
  }, [data]);

  function submitCreate(e: React.FormEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    create.mutate(
      { name },
      {
        onSuccess: (p) => {
          selectProfile(p.id);
          setNewName('');
          setCreating(false);
        },
      },
    );
  }

  function submitRename(e: React.FormEvent, id: number) {
    e.preventDefault();
    const name = editName.trim();
    if (!name) return;
    update.mutate({ id, body: { name } }, { onSuccess: () => setEditingId(null) });
  }

  const createError = create.error instanceof ApiError ? create.error : null;

  return (
    <>
      <div className="app-head">
        <div>
          <h1>Profiles</h1>
          <p>Create, switch between, and manage fully-isolated profiles.</p>
        </div>
        {!creating && (
          <button type="button" className="app-btn primary" onClick={() => setCreating(true)}>
            + New profile
          </button>
        )}
      </div>

      {creating && (
        <form className="app-card pf-createcard" onSubmit={submitCreate}>
          <label htmlFor="pf-new-name" className="pf-label">New profile name</label>
          <div className="pf-createrow">
            <input
              id="pf-new-name"
              className="pf-input"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. Personal, Household, Business"
              maxLength={100}
              autoFocus
            />
            <button type="submit" className="app-btn primary" disabled={create.isPending || !newName.trim()}>
              {create.isPending ? 'Creating…' : 'Create'}
            </button>
            <button
              type="button"
              className="app-btn"
              onClick={() => {
                setCreating(false);
                setNewName('');
                create.reset();
              }}
            >
              Cancel
            </button>
          </div>
          {createError && (
            <p className="pf-error" role="alert">{createError.fieldError('name') ?? createError.message}</p>
          )}
        </form>
      )}

      {/* Loading */}
      {isLoading && <div className="app-card pf-state">Loading profiles…</div>}

      {/* Error */}
      {isError && (
        <div className="app-card pf-state pf-state-error" role="alert">
          <p>{error instanceof ApiError ? error.message : 'Could not load profiles.'}</p>
          <button type="button" className="app-btn" onClick={() => refetch()}>Try again</button>
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && active.length === 0 && archived.length === 0 && !creating && (
        <div className="app-card app-placeholder">
          <span className="app-badge" aria-hidden>◔</span>
          <h2>Create your first profile</h2>
          <p>Each profile keeps its own accounts, categories, and spending history — completely isolated from the others.</p>
          <button type="button" className="app-btn primary" style={{ marginTop: 14 }} onClick={() => setCreating(true)}>
            + New profile
          </button>
        </div>
      )}

      {/* Active list */}
      {active.length > 0 && (
        <ul className="pf-list">
          {active.map((p) => (
            <li key={p.id} className={`app-card pf-row ${p.id === currentProfileId ? 'current' : ''}`}>
              <span className="pf-avatar" aria-hidden>{p.name.slice(0, 1).toUpperCase()}</span>
              {editingId === p.id ? (
                <form className="pf-renameform" onSubmit={(e) => submitRename(e, p.id)}>
                  <label className="pf-visually-hidden" htmlFor={`rename-${p.id}`}>Rename profile</label>
                  <input
                    id={`rename-${p.id}`}
                    className="pf-input"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    maxLength={100}
                    autoFocus
                  />
                  <button type="submit" className="app-btn primary" disabled={update.isPending}>Save</button>
                  <button type="button" className="app-btn" onClick={() => setEditingId(null)}>Cancel</button>
                </form>
              ) : (
                <div className="pf-meta">
                  <div className="pf-name">
                    {p.name}
                    {p.id === currentProfileId && <span className="pf-badge">current</span>}
                  </div>
                  <div className="pf-sub">{p.base_currency} · created {formatDate(p.created_at)}</div>
                </div>
              )}

              {editingId !== p.id && confirmArchiveId !== p.id && (
                <div className="pf-actions">
                  {p.id !== currentProfileId && (
                    <button type="button" className="app-btn primary" onClick={() => selectProfile(p.id)}>Switch to</button>
                  )}
                  <button
                    type="button"
                    className="app-btn"
                    onClick={() => { setEditingId(p.id); setEditName(p.name); }}
                  >
                    Rename
                  </button>
                  <button type="button" className="app-btn pf-danger" onClick={() => setConfirmArchiveId(p.id)}>Archive</button>
                </div>
              )}

              {confirmArchiveId === p.id && (
                <div className="pf-actions pf-confirm" role="group" aria-label={`Confirm archiving ${p.name}`}>
                  <span className="pf-confirm-text">Archive this profile? Its data is kept and can be restored.</span>
                  <button
                    type="button"
                    className="app-btn pf-danger"
                    disabled={archive.isPending}
                    onClick={() => archive.mutate(p.id, { onSuccess: () => setConfirmArchiveId(null) })}
                  >
                    {archive.isPending ? 'Archiving…' : 'Archive'}
                  </button>
                  <button type="button" className="app-btn" onClick={() => setConfirmArchiveId(null)}>Cancel</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Archived */}
      {archived.length > 0 && (
        <>
          <h2 className="pf-section">Archived</h2>
          <ul className="pf-list">
            {archived.map((p) => (
              <li key={p.id} className="app-card pf-row pf-archived">
                <span className="pf-avatar" aria-hidden>{p.name.slice(0, 1).toUpperCase()}</span>
                <div className="pf-meta">
                  <div className="pf-name">{p.name}</div>
                  <div className="pf-sub">Archived · {p.base_currency}</div>
                </div>
                <div className="pf-actions">
                  <button
                    type="button"
                    className="app-btn"
                    disabled={restore.isPending}
                    onClick={() => restore.mutate(p.id)}
                  >
                    Restore
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="pf-note">
        Profiles are archived, never hard-deleted, so no financial history is lost. Deletion with
        export is a deliberate later step.
      </p>
    </>
  );
}

export type { Profile };
