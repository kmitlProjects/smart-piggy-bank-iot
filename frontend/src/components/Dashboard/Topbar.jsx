import React from 'react';
import './Topbar.css';

function formatLastSeen(value) {
  if (!value) {
    return 'Waiting for device heartbeat';
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return 'Waiting for device heartbeat';
  }

  return `Last seen ${parsed.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })}`;
}

const Topbar = ({ wifi, locked, lastSeenAt }) => {
  const hasWifiState = typeof wifi === 'boolean';
  const hasLockState = typeof locked === 'boolean';
  const wifiIcon = hasWifiState
    ? (wifi ? '/icon/gen/sectionState/stateWiFiconect.svg' : '/icon/gen/sectionState/stateWiFidisconnect.svg')
    : '/icon/gen/sectionState/stateWiFiconect.svg';
  const lockIcon = hasLockState
    ? (locked ? '/icon/gen/sectionState/stateLock.svg' : '/icon/gen/sectionState/stateUnlock.svg')
    : '/icon/gen/sectionState/stateLock.svg';
  const wifiStateClass = hasWifiState ? (wifi ? 'is-online' : 'is-offline') : 'is-syncing';
  const wifiText = hasWifiState ? (wifi ? 'Connected' : 'Disconnected') : 'Syncing';
  const wifiChipText = hasWifiState ? (wifi ? 'Online' : 'Offline') : 'Checking';
  const topbarMeta = hasWifiState
    ? (wifi ? 'Live device data' : formatLastSeen(lastSeenAt))
    : 'Syncing latest device status';
  const lockStateClass = hasLockState ? (locked ? 'is-locked' : 'is-unlocked') : 'is-neutral';
  const lockText = hasLockState ? (locked ? 'Locked' : 'Unlocked') : 'Status';

  return (
    <header className="topbar-root">
      <div className="topbar-title-group">
        <div className="topbar-brand">
          <img
            className="topbar-brand-logo"
            src="/logo/miniLogopiggy.svg"
            alt="Smart Piggy Bank logo"
          />
          <div className="topbar-title">Smart Piggy Bank</div>
        </div>
        <span className={`topbar-status ${wifiStateClass}`}>
          <span className="topbar-dot"></span>
          <span className="topbar-status-text">{wifiText}</span>
        </span>
        <span className="topbar-meta">{topbarMeta}</span>
      </div>
      <div className="topbar-icons">
        <div className={`topbar-icon-chip ${wifiStateClass}`}>
          <img src={wifiIcon} alt={hasWifiState ? (wifi ? 'WiFi connected' : 'WiFi disconnected') : 'Checking WiFi status'} />
          <span>{wifiChipText}</span>
        </div>
        <div className={`topbar-icon-chip ${lockStateClass}`}>
          <img src={lockIcon} alt={hasLockState ? (locked ? 'Vault locked' : 'Vault unlocked') : 'Checking vault status'} />
          <span>{lockText}</span>
        </div>
      </div>
    </header>
  );
};

export default Topbar;
