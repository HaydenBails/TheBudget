import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { useCurrentProfile } from '../profiles/ProfileContext';
import {
  useArchiveCategory,
  useCategories,
  useCreateCategory,
  useRestoreCategory,
  useUpdateCategory,
} from './api';
import { CategoryIcon, normalizeCategoryIcon } from './CategoryIcon';
import { CATEGORY_COLORS, CATEGORY_ICON_CHOICES, type Category, type CategoryCreate } from './types';
import './categories.css';

interface FormValues {
  name: string;
  color: string;
  icon: string;
  excluded_from_spending: boolean;
}

function CategoryForm({
  initial,
  submitLabel,
  pending,
  error,
  onSubmit,
  onCancel,
}: {
  initial?: Category;
  submitLabel: string;
  pending: boolean;
  error: ApiError | null;
  onSubmit: (v: CategoryCreate) => void;
  onCancel: () => void;
}) {
  const [v, setV] = useState<FormValues>({
    name: initial?.name ?? '',
    color: initial?.color ?? CATEGORY_COLORS[0],
    icon: normalizeCategoryIcon(initial?.icon ?? CATEGORY_ICON_CHOICES[0].value),
    excluded_from_spending: initial?.excluded_from_spending ?? false,
  });
  const [touched, setTouched] = useState(false);
  const nameInvalid = v.name.trim().length === 0;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (nameInvalid) return;
    onSubmit({
      name: v.name.trim(),
      color: v.color,
      icon: v.icon,
      excluded_from_spending: v.excluded_from_spending,
    });
  }

  return (
    <form className="app-card ct-form" onSubmit={submit}>
      <div className="ct-form-grid">
        <div className="ct-field">
          <label htmlFor="ct-name" className="pf-label">Category name</label>
          <input
            id="ct-name"
            className="pf-input"
            value={v.name}
            onChange={(e) => setV({ ...v, name: e.target.value })}
            placeholder="e.g. Subscriptions"
            maxLength={100}
          />
          {touched && nameInvalid && <p className="pf-error" role="alert">A name is required.</p>}
        </div>
        <div className="ct-field">
          <span className="pf-label" id="ct-icon-label">Icon</span>
          <div className="ct-icons" role="radiogroup" aria-labelledby="ct-icon-label">
            {CATEGORY_ICON_CHOICES.map((icon) => (
              <button
                key={icon.value}
                type="button"
                role="radio"
                aria-checked={v.icon === icon.value}
                aria-label={icon.label}
                className={`ct-icon ${v.icon === icon.value ? 'selected' : ''}`}
                onClick={() => setV({ ...v, icon: icon.value })}
              >
                <CategoryIcon name={icon.value} />
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="ct-field">
        <span className="pf-label" id="ct-color-label">Colour</span>
        <div className="ac-swatches" role="radiogroup" aria-labelledby="ct-color-label">
          {CATEGORY_COLORS.map((c) => (
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

      <label className="ct-toggle">
        <input
          type="checkbox"
          checked={v.excluded_from_spending}
          onChange={(e) => setV({ ...v, excluded_from_spending: e.target.checked })}
        />
        Exclude from spending totals (e.g. savings, debt, fees)
      </label>

      {error && <p className="pf-error" role="alert">{error.fieldError('name') ?? error.fieldError('color') ?? error.message}</p>}

      <div className="ct-form-actions">
        <button type="submit" className="app-btn primary" disabled={pending}>
          {pending ? 'Saving…' : submitLabel}
        </button>
        <button type="button" className="app-btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function CategoryRow({
  category,
  onEdit,
  onArchive,
  archiving,
}: {
  category: Category;
  onEdit: () => void;
  onArchive: () => void;
  archiving: boolean;
}) {
  const [confirm, setConfirm] = useState(false);
  return (
    <li className="app-card ct-row">
      <span className="ct-chip" style={{ background: category.color + '22' }} aria-hidden>
        <CategoryIcon name={category.icon} />
      </span>
      <div className="ct-meta">
        <div className="ct-name">
          {category.name}
          {category.is_default && <span className="ct-badge">default</span>}
          {category.excluded_from_spending && <span className="ct-badge ct-badge-muted">excluded</span>}
        </div>
        <div className="ct-sub">{category.slug}</div>
      </div>
      {!confirm ? (
        <div className="pf-actions">
          <button type="button" className="app-btn" onClick={onEdit}>Edit</button>
          <button type="button" className="app-btn pf-danger" onClick={() => setConfirm(true)}>Archive</button>
        </div>
      ) : (
        <div className="pf-actions pf-confirm" role="group" aria-label={`Confirm archiving ${category.name}`}>
          <span className="pf-confirm-text">Archive this category? It can be restored.</span>
          <button type="button" className="app-btn pf-danger" disabled={archiving} onClick={onArchive}>
            {archiving ? 'Archiving…' : 'Archive'}
          </button>
          <button type="button" className="app-btn" onClick={() => setConfirm(false)}>Cancel</button>
        </div>
      )}
    </li>
  );
}

export function CategoriesPage() {
  const { currentProfile, currentProfileId } = useCurrentProfile();
  const { data, isLoading, isError, error, refetch } = useCategories(currentProfileId, true);

  const create = useCreateCategory(currentProfileId ?? 0);
  const update = useUpdateCategory(currentProfileId ?? 0);
  const archive = useArchiveCategory(currentProfileId ?? 0);
  const restore = useRestoreCategory(currentProfileId ?? 0);

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Category | null>(null);

  if (currentProfileId == null) {
    return (
      <>
        <div className="app-head"><div><h1>Categories</h1><p>Spending categories for the active profile.</p></div></div>
        <div className="app-card app-placeholder">
          <span className="app-badge" aria-hidden><CategoryIcon name="category" /></span>
          <h2>No profile selected</h2>
          <p>Categories belong to a profile. Create or select a profile first.</p>
          <Link className="app-btn primary" to="/app/profiles" style={{ marginTop: 14 }}>Go to profiles</Link>
        </div>
      </>
    );
  }

  const list = data ?? [];
  const active = list.filter((c) => !c.is_archived);
  const archived = list.filter((c) => c.is_archived);
  const createError = create.error instanceof ApiError ? create.error : null;
  const updateError = update.error instanceof ApiError ? update.error : null;

  return (
    <>
      <div className="app-head">
        <div>
          <h1>Categories</h1>
          <p>Spending categories for <b>{currentProfile?.name}</b> — defaults are seeded; add your own.</p>
        </div>
        {!creating && !editing && (
          <button type="button" className="app-btn primary" onClick={() => { setCreating(true); create.reset(); }}>
            + New category
          </button>
        )}
      </div>

      {creating && (
        <CategoryForm
          submitLabel="Create category"
          pending={create.isPending}
          error={createError}
          onSubmit={(body) => create.mutate(body, { onSuccess: () => setCreating(false) })}
          onCancel={() => setCreating(false)}
        />
      )}

      {editing && (
        <CategoryForm
          initial={editing}
          submitLabel="Save changes"
          pending={update.isPending}
          error={updateError}
          onSubmit={(body) => update.mutate({ id: editing.id, body }, { onSuccess: () => setEditing(null) })}
          onCancel={() => setEditing(null)}
        />
      )}

      {isLoading && <div className="app-card pf-state">Loading categories…</div>}

      {isError && (
        <div className="app-card pf-state pf-state-error" role="alert">
          <p>{error instanceof ApiError ? error.message : 'Could not load categories.'}</p>
          <button type="button" className="app-btn" onClick={() => refetch()}>Try again</button>
        </div>
      )}

      {active.length > 0 && !editing && (
        <ul className="ct-list">
          {active.map((c) => (
            <CategoryRow
              key={c.id}
              category={c}
              archiving={archive.isPending}
              onEdit={() => { setEditing(c); update.reset(); }}
              onArchive={() => archive.mutate(c.id)}
            />
          ))}
        </ul>
      )}

      {archived.length > 0 && !editing && (
        <>
          <h2 className="pf-section">Archived</h2>
          <ul className="ct-list">
            {archived.map((c) => (
              <li key={c.id} className="app-card ct-row pf-archived">
                <span className="ct-chip" style={{ background: c.color + '22' }} aria-hidden><CategoryIcon name={c.icon} /></span>
                <div className="ct-meta">
                  <div className="ct-name">{c.name}</div>
                  <div className="ct-sub">Archived</div>
                </div>
                <div className="pf-actions">
                  <button type="button" className="app-btn" disabled={restore.isPending} onClick={() => restore.mutate(c.id)}>Restore</button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
