import React from 'react';
import './VaultStatus.css';

function formatDistance(value) {
  if (value === null || value === undefined || value === '') {
    return 'Sensor waiting for data';
  }

  const parsed = Number(value);

  if (Number.isNaN(parsed)) {
    return 'Sensor waiting for data';
  }

  return `${parsed.toFixed(2)} cm sensor distance`;
}

const VaultStatus = ({ percent, distance, isFull }) => {
  const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));

  return (
    <section className="vault-status-root">
      <div className="vault-status-header">
        <img src="/icon/sectionDashboardPage/IconVault%20Capacity.svg" alt="Vault" />
        <span>Vault Capacity</span>
      </div>
      <div className="vault-status-main">
        <div className="vault-status-percent">
          {safePercent}%
          <span className="vault-status-full">{isFull ? 'Full' : 'Filled'}</span>
        </div>
        <div className="vault-status-distance">{formatDistance(distance)}</div>
        <div className="vault-status-bar-bg" aria-label="Vault fill level">
          <div className="vault-status-bar-fg" style={{ width: `${safePercent}%` }}></div>
        </div>
      </div>
    </section>
  );
};

export default VaultStatus;
