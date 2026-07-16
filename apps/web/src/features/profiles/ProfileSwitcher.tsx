import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCurrentProfile } from './ProfileContext';
import './profiles.css';

export function ProfileSwitcher() {
  const { profiles, currentProfile, currentProfileId, selectProfile, isLoading } = useCurrentProfile();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const firstActionRef = useRef<HTMLButtonElement>(null);
  const nav = useNavigate();

  function closeChoices(focus: 'trigger' | 'main' = 'trigger') {
    setOpen(false);
    if (focus === 'trigger') {
      triggerRef.current?.focus();
      return;
    }
    requestAnimationFrame(() => document.getElementById('main-content')?.focus());
  }

  useEffect(() => {
    if (!open) return;
    firstActionRef.current?.focus();
    const close = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      closeChoices();
    };
    document.addEventListener('keydown', close);
    return () => document.removeEventListener('keydown', close);
  }, [open]);

  if (isLoading) {
    return <span className="app-profile-pill" aria-live="polite"><span className="app-avatar" aria-hidden="true">…</span><span className="pf-switch-name">Loading…</span></span>;
  }

  if (profiles.length === 0) {
    return <button type="button" className="app-profile-pill pf-switch-btn" onClick={() => nav('/app/profiles')}><span className="app-avatar" aria-hidden="true">+</span><span className="pf-switch-name">Create profile</span></button>;
  }

  return (
    <div className="pf-switch">
      <button
        ref={triggerRef}
        type="button"
        className="app-profile-pill pf-switch-btn"
        aria-expanded={open}
        aria-controls="profile-switcher-actions"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="app-avatar" aria-hidden="true">{(currentProfile?.name ?? '?').slice(0, 1).toUpperCase()}</span>
        <span className="pf-switch-name">{currentProfile?.name ?? 'Select profile'}<br /><small>Switch profile</small></span>
      </button>

      {open && (
        <>
          <button type="button" className="pf-backdrop" aria-label="Close profile choices" tabIndex={-1} onClick={() => closeChoices()} />
          <div id="profile-switcher-actions" className="pf-menu" role="group" aria-label="Choose a profile">
            <div className="pf-menu-head">Profiles</div>
            {profiles.map((profile, index) => (
              <button
                key={profile.id}
                ref={index === 0 ? firstActionRef : undefined}
                type="button"
                aria-pressed={profile.id === currentProfileId}
                className={`pf-menu-item ${profile.id === currentProfileId ? 'active' : ''}`}
                onClick={() => { selectProfile(profile.id); closeChoices(); }}
              >
                <span className="pf-avatar sm" aria-hidden="true">{profile.name.slice(0, 1).toUpperCase()}</span>
                {profile.name}
                {profile.id === currentProfileId && <span className="pf-check" aria-hidden="true">✓</span>}
              </button>
            ))}
            <button type="button" className="pf-menu-item pf-menu-manage" onClick={() => { nav('/app/profiles'); closeChoices('main'); }}>Manage profiles</button>
          </div>
        </>
      )}
    </div>
  );
}
