import React from 'react';
import './HeroSection.css';

function formatLastUpdate(value) {
  if (!value) {
    return 'waiting for device data';
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return 'waiting for device data';
  }

  const diffSeconds = Math.max(0, Math.floor((Date.now() - parsed.getTime()) / 1000));

  if (diffSeconds < 10) {
    return 'just now';
  }

  if (diffSeconds < 60) {
    return `${diffSeconds}s ago`;
  }

  const diffMinutes = Math.floor(diffSeconds / 60);

  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }

  const diffHours = Math.floor(diffMinutes / 60);

  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }

  return parsed.toLocaleString();
}

const HeroSection = ({ totalSavings, percent, updatedAt }) => {
  const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));
  const ringSize = 2 * Math.PI * 40;

  return (
    <section className="hero-root">
      <div className="hero-content">
        <div className="hero-label">TOTAL SAVINGS</div>
        <div className="hero-amount">฿ {Number(totalSavings || 0).toLocaleString()}</div>
        <div className="hero-update">Last update: {formatLastUpdate(updatedAt)}</div>
      </div>
      <div className="hero-capacity">
        <div className="hero-capacity-circle">
          <svg width="96" height="96" viewBox="0 0 96 96">
            <circle cx="48" cy="48" r="40" stroke="rgba(255,255,255,0.14)" strokeWidth="8" fill="none" />
            <circle
              cx="48"
              cy="48"
              r="40"
              stroke="#9CF2E8"
              strokeWidth="8"
              fill="none"
              strokeDasharray={ringSize}
              strokeDashoffset={ringSize * (1 - safePercent / 100)}
              strokeLinecap="round"
              style={{ transition: 'stroke-dashoffset 0.5s ease' }}
            />
          </svg>
          <div className="hero-capacity-text">{safePercent}%</div>
        </div>
        <div className="hero-capacity-label">VAULT CAPACITY</div>
      </div>
    </section>
  );
};

export default HeroSection;
