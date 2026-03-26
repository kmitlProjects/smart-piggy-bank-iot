import React from 'react'
import ReactDOM from 'react-dom/client'
import { Buffer } from 'buffer'
import process from 'process'
import Dashboard from './components/Dashboard/Dashboard.jsx'
import Settings from './components/Settings/Settings.jsx'
import './index.css'

if (!window.global) {
  window.global = window
}
if (!window.Buffer) {
  window.Buffer = Buffer
}
if (!window.process) {
  window.process = process
}

function AppRouter() {
  const [page, setPage] = React.useState('dashboard');
  const handleNavigate = (id) => setPage(id);
  return (
    <>
      {page === 'dashboard' && <Dashboard onNavigate={handleNavigate} />}
      {page === 'settings' && <Settings onNavigate={handleNavigate} />}
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppRouter />
  </React.StrictMode>,
)
