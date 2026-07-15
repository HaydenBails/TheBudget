import { QueryClientProvider } from '@tanstack/react-query';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { useTheme } from '../theme';
import { queryClient } from '../api/queryClient';
import { useHealth } from '../api/health';
import { ProfileProvider } from '../features/profiles/ProfileContext';
import { ProfileSwitcher } from '../features/profiles/ProfileSwitcher';
import { ProfilesPage } from '../features/profiles/ProfilesPage';
import { AccountsPage } from '../features/accounts/AccountsPage';
import { CategoriesPage, DashboardPage, SettingsPage } from './pages';
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
        <ApiStatus />
        <button type="button" className="app-iconbtn" onClick={toggle} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}>
          {theme === 'light' ? '🌙 Dark' : '☀ Light'}
        </button>
        <ProfileSwitcher />
      </div>
    </nav>
  );
}

/** Live connection state for the local API (loading / error / success). */
function ApiStatus() {
  const { isLoading, isError, data } = useHealth();
  const state = isLoading ? 'checking' : isError || !data ? 'offline' : 'online';
  const label = state === 'checking' ? 'Checking API…' : state === 'offline' ? 'API offline' : 'API connected';
  return (
    <span className={`app-status ${state}`} role="status" title={label}>
      <span className="app-status-dot" aria-hidden />
      {label}
    </span>
  );
}

/**
 * Production application shell (FE-02 + FE-03). Mounted at `/app/*`, separate
 * from the prototype comparison harness. Renders the Meridian design system
 * (top nav + theme) and nested routes, wrapped in the TanStack Query client so
 * data features (FE-04…FE-05) can consume the local API.
 */
export function AppShell() {
  return (
    <QueryClientProvider client={queryClient}>
      <ProfileProvider>
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
      </ProfileProvider>
    </QueryClientProvider>
  );
}

export default AppShell;
