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
  const wifiIcon = wifi
    ? '/icon/gen/sectionState/stateWiFiconect.svg'
    : '/icon/gen/sectionState/stateWiFidisconnect.svg';
  const lockIcon = locked
    ? '/icon/gen/sectionState/stateLock.svg'
    : '/icon/gen/sectionState/stateUnlock.svg';

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
        <span className={`topbar-status ${wifi ? 'is-online' : 'is-offline'}`}>
          <span className="topbar-dot"></span>
          <span className="topbar-status-text">{wifi ? 'Connected' : 'Disconnected'}</span>
        </span>
        <span className="topbar-meta">{wifi ? 'Live device data' : formatLastSeen(lastSeenAt)}</span>
      </div>
      <div className="topbar-icons">
        <div className={`topbar-icon-chip ${wifi ? 'is-online' : 'is-offline'}`}>
          <img src={wifiIcon} alt={wifi ? 'WiFi connected' : 'WiFi disconnected'} />
          <span>{wifi ? 'Online' : 'Offline'}</span>
        </div>
        <div className={`topbar-icon-chip ${locked ? 'is-locked' : 'is-unlocked'}`}>
          <img src={lockIcon} alt={locked ? 'Vault locked' : 'Vault unlocked'} />
          <span>{locked ? 'Locked' : 'Unlocked'}</span>
        </div>
      </div>
    </header>
  );
};

export default Topbar;
