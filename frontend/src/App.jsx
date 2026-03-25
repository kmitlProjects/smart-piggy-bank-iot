import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE = ''

const initialSummary = {
  coin_1: 0,
  coin_2: 0,
  coin_5: 0,
  coin_10: 0,
  total: 0,
  events: 0,
}

function App() {
  const [status, setStatus] = useState(null)
  const [summary, setSummary] = useState(initialSummary)
  const [history, setHistory] = useState([])
  const [accessLogs, setAccessLogs] = useState([])
  const [cards, setCards] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isResetting, setIsResetting] = useState(false)

  const coins = useMemo(
    () => ({
      '1': summary.coin_1 || 0,
      '2': summary.coin_2 || 0,
      '5': summary.coin_5 || 0,
      '10': summary.coin_10 || 0,
    }),
    [summary]
  )

  const fetchJson = async (path, options) => {
    const response = await fetch(`${API_BASE}${path}`, options)
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`)
    }
    return response.json()
  }

  const refreshData = async (showLoading = false) => {
    if (showLoading) {
      setLoading(true)
    }
    setError('')

    try {
      const [statusRes, summaryRes, historyRes, accessRes, cardsRes] = await Promise.all([
        fetchJson('/api/status'),
        fetchJson('/api/coins/summary'),
        fetchJson('/api/coins/history?limit=30'),
        fetchJson('/api/access/history?limit=30'),
        fetchJson('/api/rfid/cards'),
      ])

      setStatus(statusRes.status || null)
      setSummary(summaryRes.summary || initialSummary)
      setHistory(Array.isArray(historyRes.history) ? historyRes.history : [])
      setAccessLogs(Array.isArray(accessRes.history) ? accessRes.history : [])
      setCards(Array.isArray(cardsRes.cards) ? cardsRes.cards : [])
    } catch (err) {
      setError(err.message || 'Cannot load backend data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshData(true)

    const timer = setInterval(() => {
      refreshData(false)
    }, 3000)

    return () => clearInterval(timer)
  }, [])

  const handleReset = async () => {
    setIsResetting(true)
    setError('')
    try {
      await fetchJson('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clear_cards: false }),
      })
      await refreshData(false)
    } catch (err) {
      setError(err.message || 'Reset failed')
    } finally {
      setIsResetting(false)
    }
  }

  // NOTE: RFID enrollment functions have been removed.
  // System now uses locked RFID UIDs (hardcoded whitelist on backend).
  const handleDeleteCard = async (uid) => {
    // Delete endpoint also removed - locked UIDs cannot be deleted
    setError('Locked RFID system: card cannot be deleted.')
  }

  const fmtTs = (value) => {
    if (!value) return '-'
    try {
      return new Date(value).toLocaleString()
    } catch {
      return value
    }
  }

  return (
    <div className="container">
      <h1>Smart Piggy Bank Dashboard</h1>
      <p className="subtitle">Backend API: {API_BASE || '/api (vite proxy)'}</p>

      <div className="toolbar">
        <button className="primary-btn" onClick={() => refreshData(false)} disabled={loading || isResetting}>
          Refresh
        </button>
        <button className="danger-btn" onClick={handleReset} disabled={loading || isResetting}>
          {isResetting ? 'Resetting...' : 'Reset Data'}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}
      {loading && <div className="loading-box">Loading data...</div>}

      <div className="coins-grid">
        {[
          { value: 10, baht: '10 บาท' },
          { value: 5, baht: '5 บาท' },
          { value: 2, baht: '2 บาท' },
          { value: 1, baht: '1 บาท' },
        ].map((coin) => (
          <div key={coin.value} className="coin-card">
            <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>💰</div>
            <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>{coin.baht}</h3>
            <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#10b981', margin: '0.5rem 0' }}>
              {coins[String(coin.value)]}
            </p>
            <p style={{ fontSize: '0.9rem', color: '#888', margin: 0 }}>
              = {coin.value * coins[String(coin.value)]} บาท
            </p>
          </div>
        ))}
      </div>

      <div className="total-box">
        <h2>รวมทั้งหมด</h2>
        <p className="total-amount">{summary.total || 0} บาท</p>
        <p className="mini">events: {summary.events || 0}</p>
      </div>

      <div className="status-grid">
        <div className="status-item">
          <span className="label">WiFi</span>
          <span className="value">{status?.wifi_connected ? 'Connected' : 'Offline'}</span>
        </div>
        <div className="status-item">
          <span className="label">Lock</span>
          <span className="value">{status?.is_locked ? 'Locked' : 'Unlocked'}</span>
        </div>
        <div className="status-item">
          <span className="label">Fill</span>
          <span className="value">{Math.round(status?.fill_percent || 0)}%</span>
        </div>
        <div className="status-item">
          <span className="label">Distance</span>
          <span className="value">
            {status?.distance_cm === null || status?.distance_cm === undefined
              ? '-'
              : Number(status.distance_cm).toFixed(2) + ' cm'}
          </span>
        </div>
      </div>

      <section className="panel">
        <h3>Coin History (Latest 30)</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>1</th>
                <th>2</th>
                <th>5</th>
                <th>10</th>
                <th>Total</th>
                <th>WiFi</th>
                <th>Lock</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 && (
                <tr>
                  <td colSpan="8" className="empty">No history</td>
                </tr>
              )}
              {history.map((row) => (
                <tr key={row.id}>
                  <td>{fmtTs(row.created_at)}</td>
                  <td>{row.coin_1}</td>
                  <td>{row.coin_2}</td>
                  <td>{row.coin_5}</td>
                  <td>{row.coin_10}</td>
                  <td>{row.total}</td>
                  <td>{row.wifi_connected ? 'Y' : 'N'}</td>
                  <td>{row.is_locked ? 'Locked' : 'Unlocked'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h3>Access Logs (Latest 30)</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>UID</th>
                <th>WiFi</th>
                <th>Authorized</th>
                <th>Granted</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {accessLogs.length === 0 && (
                <tr>
                  <td colSpan="6" className="empty">No access logs</td>
                </tr>
              )}
              {accessLogs.map((row) => (
                <tr key={row.id}>
                  <td>{fmtTs(row.created_at)}</td>
                  <td>{row.uid || '-'}</td>
                  <td>{row.wifi_connected ? 'Y' : 'N'}</td>
                  <td>{row.authorized ? 'Y' : 'N'}</td>
                  <td>{row.access_granted ? 'Y' : 'N'}</td>
                  <td>{row.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h3>RFID Config</h3>
        {/* NOTE: Enrollment UI has been removed. System uses CLOSED locked RFID UIDs only. */}
        <p className="rfid-hint">
          🔒 <strong>Closed RFID System:</strong> Only 2 authorized UIDs can unlock the device:<br/>
          • UID #1: [182, 188, 21, 6, 25]<br/>
          • UID #2: [195, 118, 240, 6, 67]<br/>
          All other cards are DENIED.
        </p>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Authorized UID</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>[182, 188, 21, 6, 25]</td>
                <td>✓ Active</td>
              </tr>
              <tr>
                <td>[195, 118, 240, 6, 67]</td>
                <td>✓ Active</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

export default App;
