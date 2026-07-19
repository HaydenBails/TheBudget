import { QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { useTheme } from '../theme';
import { queryClient } from '../api/queryClient';
import { useHealth } from '../api/health';
import { ProfileProvider, useCurrentProfile } from '../features/profiles/ProfileContext';
import { ProfileSwitcher } from '../features/profiles/ProfileSwitcher';
import { useTransactions } from '../features/transactions/api';
import type { TransactionFilters } from '../features/transactions/types';
import { ProfilesPage } from '../features/profiles/ProfilesPage';
import { AccountsPage } from '../features/accounts/AccountsPage';
import { CategoriesPage } from '../features/categories/CategoriesPage';
import { BudgetsPage } from '../features/budgets/BudgetsPage';
import { RecurringPage } from '../features/recurring/RecurringPage';
import { IncomePage } from '../features/income/IncomePage';
import { ReviewPage } from '../features/review/ReviewPage';
import { TransactionsPage } from '../features/transactions/TransactionsPage';
import { MerchantsPage } from '../features/merchants/MerchantsPage';
import { ImportPage } from '../features/imports/ImportPage';
import { DashboardPage, SettingsPage } from './pages';
import './app.css';

type IconName = 'dashboard' | 'transactions' | 'merchants' | 'review' | 'profiles' | 'accounts' | 'categories' | 'budgets' | 'recurring' | 'income' | 'settings' | 'import' | 'sun' | 'moon';

const NAV_GROUPS: { heading: string; items: { to: string; label: string; icon: IconName }[] }[] = [
  {
    heading: 'Money',
    items: [
      { to: '/app/dashboard', label: 'Dashboard', icon: 'dashboard' },
      { to: '/app/transactions', label: 'Transactions', icon: 'transactions' },
      { to: '/app/merchants', label: 'Merchants', icon: 'merchants' },
      { to: '/app/review', label: 'Review', icon: 'review' },
    ],
  },
  {
    heading: 'Plan',
    items: [
      { to: '/app/budgets', label: 'Budgets', icon: 'budgets' },
      { to: '/app/recurring', label: 'Recurring', icon: 'recurring' },
      { to: '/app/income', label: 'Income', icon: 'income' },
    ],
  },
  {
    heading: 'Manage',
    items: [
      { to: '/app/profiles', label: 'Profiles', icon: 'profiles' },
      { to: '/app/accounts', label: 'Accounts', icon: 'accounts' },
      { to: '/app/categories', label: 'Categories', icon: 'categories' },
      { to: '/app/settings', label: 'Settings', icon: 'settings' },
    ],
  },
];

function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    dashboard: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    transactions: <><path d="M4 5h16M4 12h16M4 19h16" /><circle cx="7" cy="5" r="1" /><circle cx="17" cy="12" r="1" /><circle cx="10" cy="19" r="1" /></>,
    merchants: <><path d="M3 9h18l-1.5 11a1 1 0 0 1-1 .9H5.5a1 1 0 0 1-1-.9L3 9Z" /><path d="M8 9V6a4 4 0 0 1 8 0v3" /></>,
    review: <><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></>,
    profiles: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
    accounts: <><rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20M6 15h4" /></>,
    categories: <><path d="M20.6 13.6 11 4H4v7l9.6 9.6a2 2 0 0 0 2.8 0l4.2-4.2a2 2 0 0 0 0-2.8Z" /><circle cx="7.5" cy="7.5" r=".5" /></>,
    budgets: <><path d="M3 3v18h18" /><rect x="7" y="12" width="3" height="6" rx="1" /><rect x="12" y="8" width="3" height="10" rx="1" /><rect x="17" y="5" width="3" height="13" rx="1" /></>,
    recurring: <><path d="M3 12a9 9 0 0 1 15-6.7L21 8" /><path d="M21 3v5h-5" /><path d="M21 12a9 9 0 0 1-15 6.7L3 16" /><path d="M3 21v-5h5" /></>,
    income: <><path d="M12 1v22" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21h-4v-.1A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.2 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H2.4v-4h.1A1.7 1.7 0 0 0 4.2 8.6a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 8.6 4.2a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V2.4h4v.1A1.7 1.7 0 0 0 15 4.2a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 8.6a1.7 1.7 0 0 0 .6 1 1.7 1.7 0 0 0 1.1.4h.1v4h-.1a1.7 1.7 0 0 0-1.7 1Z" /></>,
    import: <><path d="M12 3v12m0-12L7 8m5-5 5 5" /><path d="M4 14v6h16v-6" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41" /></>,
    moon: <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />,
  };
  return <svg className="app-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

const REVIEW_COUNT_FILTERS: TransactionFilters = {
  accountId: null, categoryId: null, type: null, dateFrom: '', dateTo: '',
  includedInSpending: null, search: '', includeDeleted: false,
};

/** Live count of uncategorized transactions; updates as categorize mutations invalidate the query. */
function useUncategorizedCount() {
  const { currentProfileId } = useCurrentProfile();
  const txns = useTransactions(currentProfileId, REVIEW_COUNT_FILTERS);
  return (txns.data ?? []).filter((t) => t.category_id == null && t.deleted_at == null).length;
}

function Sidebar() {
  const { theme, toggle } = useTheme();
  const reviewCount = useUncategorizedCount();
  return (
    <aside className="app-sidebar" aria-label="Primary">
      <NavLink to="/app/dashboard" className="app-brand" aria-label="Meridian dashboard">
        <span className="app-logo" aria-hidden="true" />
        <span>MERIDIAN</span>
      </NavLink>
      <NavLink to="/app/imports" className={({ isActive }) => `app-import-action ${isActive ? 'active' : ''}`}>
        <Icon name="import" /><span>Import statement</span>
      </NavLink>
      <nav className="app-side-nav" aria-label="Sections">
        {NAV_GROUPS.map((group) => (
          <div key={group.heading} className="app-nav-group">
            <span className="app-nav-heading">{group.heading}</span>
            {group.items.map((item) => (
              <NavLink key={item.to} to={item.to} className={({ isActive }) => `app-tab ${isActive ? 'active' : ''}`}>
                <Icon name={item.icon} />
                <span>{item.label}</span>
                {item.to === '/app/review' && reviewCount > 0 && (
                  <span className="app-tab-badge" aria-label={`${reviewCount} to review`}>{reviewCount}</span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="app-side-foot">
        <ApiStatus />
        <div className="app-side-foot-row">
          <button type="button" className="app-iconbtn" onClick={toggle} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}>
            <Icon name={theme === 'light' ? 'moon' : 'sun'} />
            <span className="app-theme-label">{theme === 'light' ? 'Dark' : 'Light'}</span>
          </button>
          <ProfileSwitcher />
        </div>
      </div>
    </aside>
  );
}

function ApiStatus() {
  const { isLoading, isError, data } = useHealth();
  const state = isLoading ? 'checking' : isError || !data ? 'offline' : 'online';
  const label = state === 'checking' ? 'Checking API…' : state === 'offline' ? 'API offline' : 'API connected';
  return <span className={`app-status ${state}`} role="status" title={label}><span className="app-status-dot" aria-hidden="true" />{label}</span>;
}

export function AppShell() {
  return (
    <QueryClientProvider client={queryClient}>
      <ProfileProvider>
        <div className="app mrd app-has-sidebar">
          <a className="app-skip" href="#main-content">Skip to content</a>
          <Sidebar />
          <main className="app-body" id="main-content" tabIndex={-1}>
            <Routes>
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="transactions" element={<TransactionsPage />} />
              <Route path="merchants" element={<MerchantsPage />} />
              <Route path="review" element={<ReviewPage />} />
              <Route path="imports" element={<ImportPage />} />
              <Route path="profiles" element={<ProfilesPage />} />
              <Route path="accounts" element={<AccountsPage />} />
              <Route path="categories" element={<CategoriesPage />} />
              <Route path="budgets" element={<BudgetsPage />} />
              <Route path="recurring" element={<RecurringPage />} />
              <Route path="income" element={<IncomePage />} />
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
