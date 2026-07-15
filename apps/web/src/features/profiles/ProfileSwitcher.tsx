import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCurrentProfile } from './ProfileContext';
import './profiles.css';

export function ProfileSwitcher() {
  const { profiles, currentProfile, currentProfileId, selectProfile, isLoading } = useCurrentProfile();
  const [open, setOpen] = useState(false);
  const nav = useNavigate();

  if (isLoading) {
    return <span className="app-profile-pill" aria-live="polite"><span className="app-avatar" aria-hidden>…</span>Loading…</span>;
  }

  if (profiles.length === 0) {
    return (
      <button type="button" className="app-profile-pill pf-switch-btn" onClick={() => nav('/app/profiles')}>
        <span className="app-avatar" aria-hidden>+</span>
        <span>Create profile</span>
      </button>
    );
  }

  return (
    <div className="pf-switch">
      <button
        type="button"
        className="app-profile-pill pf-switch-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="app-avatar" aria-hidden>{(currentProfile?.name ?? '?').slice(0, 1).toUpperCase()}</span>
        <span className="pf-switch-name">
          {currentProfile?.name ?? 'Select profile'}
          <br />
          <small>switch ▾</small>
        </span>
      </button>

      {open && (
        <>
          <button type="button" className="pf-backdrop" aria-hidden tabIndex={-1} onClick={() => setOpen(false)} />
          <div className="pf-menu" role="menu">
            <div className="pf-menu-head">Profiles</div>
            {profiles.map((p) => (
              <button
                key={p.id}
                type="button"
                role="menuitemradio"
                aria-checked={p.id === currentProfileId}
                className={`pf-menu-item ${p.id === currentProfileId ? 'active' : ''}`}
                onClick={() => { selectProfile(p.id); setOpen(false); }}
              >
                <span className="pf-avatar sm" aria-hidden>{p.name.slice(0, 1).toUpperCase()}</span>
                {p.name}
                {p.id === currentProfileId && <span className="pf-check" aria-hidden>✓</span>}
              </button>
            ))}
            <button
              type="button"
              role="menuitem"
              className="pf-menu-item pf-menu-manage"
              onClick={() => { setOpen(false); nav('/app/profiles'); }}
            >
              ⚙ Manage profiles
            </button>
          </div>
        </>
      )}
    </div>
  );
}
