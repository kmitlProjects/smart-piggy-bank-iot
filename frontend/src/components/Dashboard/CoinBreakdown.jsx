import React from 'react';
import './CoinBreakdown.css';

const CoinBreakdown = ({ coins, onViewHistory }) => (
  <section className="coin-breakdown-root">
    <div className="coin-breakdown-header">
      <span>Coin Breakdown</span>
      <button type="button" className="coin-breakdown-history" onClick={onViewHistory}>
        View History
      </button>
    </div>
    <div className="coin-breakdown-cards">
      {coins.map((coin) => (
        <div className="coin-card" key={coin.value} style={{borderBottom: `4px solid ${coin.color}20`}}>
          <div className="coin-card-top">
            <div className="coin-card-icon" style={{background: coin.color}}>{coin.value}</div>
            <span className="coin-card-unit">{coin.value} BAHT</span>
          </div>
          <div className="coin-card-amount">฿ {coin.amount.toLocaleString()}</div>
          <div className="coin-card-count">Count: {coin.count} coins</div>
        </div>
      ))}
    </div>
  </section>
);

export default CoinBreakdown;
