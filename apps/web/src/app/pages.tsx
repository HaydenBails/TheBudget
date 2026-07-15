// Production pages for the shell. Profiles → features/profiles/ProfilesPage,
// accounts → features/accounts/AccountsPage; categories → backlog.
import { useCurrentProfile } from '../features/profiles/ProfileContext';
import { useAccounts } from '../features/accounts/api';

function PageHead({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="app-head">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}

function Placeholder({ badge, title, body, task }: { badge: string; title: string; body: string; task: string }) {
  return (
    <div className="app-card app-placeholder">
      <span className="app-badge" aria-hidden>{badge}</span>
      <h2>{title}</h2>
      <p>{body}</p>
      <span className="app-tag">Arrives in {task}</span>
    </div>
  );
}

export function DashboardPage() {
  const { currentProfile, currentProfileId } = useCurrentProfile();
  const accounts = useAccounts(currentProfileId, false);
  return (
    <>
      <PageHead title="Dashboard" subtitle="Your workspace — connected to the local API in a later task." />
      <section className="app-tiles" aria-label="Workspace summary">
        <div className="app-tile">
          <div className="app-tile-k">Active profile</div>
          <div className="app-tile-v">{currentProfile?.name ?? '—'}</div>
        </div>
        <div className="app-tile">
          <div className="app-tile-k">Accounts</div>
          <div className="app-tile-v">{accounts.data ? accounts.data.length : '—'}</div>
        </div>
        <div className="app-tile">
          <div className="app-tile-k">Categories</div>
          <div className="app-tile-v">—</div>
        </div>
      </section>
      <Placeholder
        badge="◧"
        title="Spending insights are on the way"
        body="This production shell renders the Meridian design system with light and dark themes and keyboard-accessible navigation. Live profile, account, and spending data connect through the local API in the upcoming tasks."
        task="FE-03 → FE-05"
      />
    </>
  );
}

export function CategoriesPage() {
  return (
    <>
      <PageHead title="Categories" subtitle="Default and custom spending categories per profile." />
      <Placeholder
        badge="🏷️"
        title="Category management"
        body="Review the seeded default categories and add your own, with colours and icons. Backlog item after the profiles/accounts slice ships."
        task="a later stage"
      />
    </>
  );
}

export function SettingsPage() {
  return (
    <>
      <PageHead title="Settings" subtitle="Local, private, and yours — this app binds to your machine only." />
      <div className="app-card">
        <p style={{ margin: 0, color: 'var(--mrd-muted)', lineHeight: 1.6 }}>
          The spending tracker runs entirely on <b>127.0.0.1</b> with data in a local SQLite
          database. There is no account, login, or cloud sync. Theme preference is remembered in
          this browser. More settings appear as features land.
        </p>
      </div>
    </>
  );
}
