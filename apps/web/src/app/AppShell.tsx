import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { useTheme } from '../theme';
import { AccountsPage, CategoriesPage, DashboardPage, ProfilesPage, SettingsPage } from './pages';
import './app.css';

const NAV: { to: string; label: string; icon: string }[] = [
  { to: 'dashboard', label: 'Dashboard', icon: '◧' },
  { to: 'profiles', label: 'Profiles', icon: '◔' },
  { to: 'accounts', label: 'Accounts', icon: '▤' },
  { to: 'categories', label: 'Categories', icon: '🏷️' },
  { to: 'settings', label: 'Settings', icon: '⚙' },
];

function TopNav() {
  const { theme, toggle } = useTheme();
  return (
    <nav className="app-nav" aria-label="Primary">
      <NavLink to="dashboard" className="app-brand">
        <span className="app-logo" aria-hidden>◈</span>
        Spending Tracker
      </NavLink>
      <div className="app-tabs">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} className={({ isActive }) => `app-tab ${isActive ? 'active' : ''}`}>
            <span className="app-tab-ico" aria-hidden>{n.icon}</span>
            {n.label}
          </NavLink>
        ))}
      </div>
      <div className="app-nav-right">
        <button type="button" className="app-iconbtn" onClick={toggle} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}>
          {theme === 'light' ? '🌙 Dark' : '☀ Light'}
        </button>
        <span className="app-profile-pill">
          <span className="app-avatar" aria-hidden>?</span>
          <span>
            No profile<br />
            <small>select one</small>
          </span>
        </span>
      </div>
    </nav>
  );
}

/**
 * Production application shell (FE-02). Mounted at `/app/*`, separate from the
 * prototype comparison harness. Renders the Meridian design system (top nav +
 * theme) and nested routes; data features connect in FE-03…FE-05.
 */
export function AppShell() {
  return (
    <div className="app mrd">
      <TopNav />
      <main className="app-body">
        <Routes>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="profiles" element={<ProfilesPage />} />
          <Route path="accounts" element={<AccountsPage />} />
          <Route path="categories" element={<CategoriesPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default AppShell;
