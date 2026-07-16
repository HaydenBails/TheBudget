import { Link } from 'react-router-dom';
import { useCurrentProfile } from '../features/profiles/ProfileContext';
import { useAccounts } from '../features/accounts/api';
import { useCategories } from '../features/categories/api';

function PageHead({ title, subtitle }: { title: string; subtitle: string }) {
  return <div className="app-head"><div><h1>{title}</h1><p>{subtitle}</p></div></div>;
}

function countLabel(isLoading: boolean, isError: boolean, count?: number) {
  if (isLoading) return 'Loading…';
  if (isError) return 'Unavailable';
  return String(count ?? 0);
}

export function DashboardPage() {
  const { currentProfile, currentProfileId } = useCurrentProfile();
  const accounts = useAccounts(currentProfileId, false);
  const categories = useCategories(currentProfileId, false);
  return (
    <>
      <PageHead title="Dashboard" subtitle="A live summary of the data stored on this device." />
      <section className="app-tiles" aria-label="Workspace summary">
        <div className="app-tile"><div className="app-tile-k">Active profile</div><div className="app-tile-v">{currentProfile?.name ?? 'None'}</div></div>
        <div className="app-tile"><div className="app-tile-k">Active accounts</div><div className="app-tile-v">{countLabel(accounts.isLoading, accounts.isError, accounts.data?.length)}</div></div>
        <div className="app-tile"><div className="app-tile-k">Active categories</div><div className="app-tile-v">{countLabel(categories.isLoading, categories.isError, categories.data?.length)}</div></div>
      </section>
      <section className="app-card app-placeholder" aria-labelledby="workspace-title">
        <h2 id="workspace-title">Your Meridian workspace</h2>
        <p>Profiles, accounts, categories, and transactions are connected to the local API and ready to manage.</p>
        <div className="app-placeholder-actions">
          <Link className="app-btn" to="/app/profiles">Manage profiles</Link>
          <Link className="app-btn" to="/app/accounts">Manage accounts</Link>
          <Link className="app-btn" to="/app/categories">Manage categories</Link>
          <Link className="app-btn primary" to="/app/transactions">View transactions</Link>
        </div>
        <span className="app-tag">Local data only</span>
      </section>
    </>
  );
}

export function SettingsPage() {
  return (
    <>
      <PageHead title="Settings" subtitle="Local, private, and stored on your machine." />
      <section className="app-card" aria-labelledby="privacy-title">
        <h2 id="privacy-title">Privacy and appearance</h2>
        <p className="app-settings-copy">Meridian runs on <b>127.0.0.1</b> and stores application data in a local SQLite database. There is no login or cloud sync. Use the theme control in the top bar to switch appearance; that choice is remembered in this browser.</p>
      </section>
    </>
  );
}
