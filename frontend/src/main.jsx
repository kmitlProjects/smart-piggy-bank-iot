import React from 'react'
import ReactDOM from 'react-dom/client'
import { Buffer } from 'buffer'
import process from 'process'
import Dashboard from './components/Dashboard/Dashboard.jsx'
import Statistics from './components/Statistics/Statistics.jsx'
import Transactions from './components/Transactions/Transactions.jsx'
import Settings from './components/Settings/Settings.jsx'
import './index.css'

const PAGE_STORAGE_KEY = 'smart_piggy_active_page';
const ALLOWED_PAGES = new Set(['dashboard', 'statistics', 'transactions', 'settings']);
const PAGE_TO_PATH = {
  dashboard: '/dashboard',
  statistics: '/statistics',
  transactions: '/transactions',
  settings: '/settings',
};
const PATH_TO_PAGE = new Map([
  ['/', 'dashboard'],
  ['/dashboard', 'dashboard'],
  ['/statistics', 'statistics'],
  ['/transactions', 'transactions'],
  ['/settings', 'settings'],
]);

if (!window.global) {
  window.global = window
}
if (!window.Buffer) {
  window.Buffer = Buffer
}
if (!window.process) {
  window.process = process
}

function normalizePath(pathname) {
  if (!pathname) {
    return '/';
  }

  const normalized = pathname.replace(/\/+$/, '');
  return normalized || '/';
}

function getPageFromLocation() {
  return PATH_TO_PAGE.get(normalizePath(window.location.pathname)) || null;
}

function getInitialPage() {
  const routePage = getPageFromLocation();
  if (routePage) {
    return routePage;
  }

  const storedPage = window.localStorage.getItem(PAGE_STORAGE_KEY);
  return ALLOWED_PAGES.has(storedPage) ? storedPage : 'dashboard';
}

function AppRouter() {
  const [page, setPage] = React.useState(getInitialPage);

  React.useEffect(() => {
    window.localStorage.setItem(PAGE_STORAGE_KEY, page);
  }, [page]);

  React.useEffect(() => {
    const handlePopState = () => {
      const routePage = getPageFromLocation();
      setPage(routePage || 'dashboard');
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  React.useEffect(() => {
    const currentPageFromRoute = getPageFromLocation();
    if (!currentPageFromRoute) {
      const targetPath = PAGE_TO_PATH[page] || PAGE_TO_PATH.dashboard;
      window.history.replaceState(window.history.state, '', targetPath);
    }
  }, [page]);

  const handleNavigate = React.useCallback((id) => {
    const nextPage = ALLOWED_PAGES.has(id) ? id : 'dashboard';
    const targetPath = PAGE_TO_PATH[nextPage] || PAGE_TO_PATH.dashboard;
    const currentPath = normalizePath(window.location.pathname);

    setPage(nextPage);

    if (currentPath !== targetPath) {
      window.history.pushState(window.history.state, '', targetPath);
    }
  }, []);

  return (
    <>
      {page === 'dashboard' && <Dashboard onNavigate={handleNavigate} />}
      {page === 'statistics' && <Statistics onNavigate={handleNavigate} />}
      {page === 'transactions' && <Transactions onNavigate={handleNavigate} />}
      {page === 'settings' && <Settings onNavigate={handleNavigate} />}
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppRouter />
  </React.StrictMode>,
)
