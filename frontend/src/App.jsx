import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [coins, setCoins] = useState({ '10': 0, '5': 0, '2': 0, '1': 0 })
  const [total, setTotal] = useState(0)

  useEffect(() => {
    const totalCoin =
      coins['10'] * 10 +
      coins['5'] * 5 +
      coins['2'] * 2 +
      coins['1'] * 1
    setTotal(totalCoin)
  }, [coins])

  return (
    <div className="container">
      <h1>🏦 Smart Piggy Bank</h1>
      <p style={{ color: '#888', marginBottom: '2rem' }}>Connected to MQTT ✅</p>

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
              {coins[coin.value]}
            </p>
            <p style={{ fontSize: '0.9rem', color: '#888', margin: 0 }}>
              = {coin.value * coins[coin.value]} บาท
            </p>
          </div>
        ))}
      </div>

      <div className="total-box">
        <h2>รวมทั้งหมด</h2>
        <p className="total-amount">{total} บาท</p>
      </div>

      <div className="status-grid">
        <div className="status-item">
          <span className="label">WiFi</span>
          <span className="value">✅ Connected</span>
        </div>
        <div className="status-item">
          <span className="label">Lock</span>
          <span className="value">🔒 Locked</span>
        </div>
        <div className="status-item">
          <span className="label">Fill</span>
          <span className="value">45%</span>
        </div>
        <div className="status-item">
          <span className="label">MQTT</span>
          <span className="value">🟢 Live</span>
        </div>
      </div>
    </div>
  )
}

export default App

