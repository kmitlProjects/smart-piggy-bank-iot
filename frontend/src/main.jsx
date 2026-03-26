import React from 'react'
import ReactDOM from 'react-dom/client'
import { Buffer } from 'buffer'
import process from 'process'
import Dashboard from './components/Dashboard/Dashboard.jsx'
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

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Dashboard />
  </React.StrictMode>,
)
