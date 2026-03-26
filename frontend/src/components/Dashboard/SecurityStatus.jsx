import React from 'react';
import './SecurityStatus.css';

const SecurityStatus = ({ locked, wifi, isUnlocking, onUnlock, unlockError }) => {
  const securityIcon = '/icon/sectionDashboardPage/IconVaultSecurity.svg';
  const lockIcon = locked
    ? '/icon/gen/sectionState/stateLock.svg'
    : '/icon/gen/sectionState/stateUnlock.svg';
  const badgeLabel = locked ? 'SECURE' : 'UNLOCKED';
  const helperText = unlockError || (
    wifi
      ? (locked ? 'Send a 5-second unlock command over the web dashboard.' : 'Vault is open. You can send the unlock command again if needed.')
      : 'Device is offline. Reconnect WiFi before sending unlock commands.'
  );
  const buttonLabel = !wifi
    ? 'DEVICE OFFLINE'
    : (isUnlocking ? 'UNLOCKING...' : (locked ? 'UNLOCK VIA WEB' : 'UNLOCK AGAIN'));

  return (
    <section className={`security-status-root ${locked ? 'is-locked' : 'is-unlocked'}`}>
      <div className="security-status-header">
        <img src={securityIcon} alt="Security" />
        <span>Vault Security</span>
        <span className={`security-status-badge ${locked ? 'is-locked' : 'is-unlocked'}`}>{badgeLabel}</span>
      </div>
      <div className="security-status-main">
        <div className="security-status-lock">
          <div className={`security-status-lock-icon ${locked ? 'is-locked' : 'is-unlocked'}`}>
            <img src={lockIcon} alt="Lock" />
          </div>
          <div className="security-status-lock-info">
            <div className="security-status-lock-title">Vault {locked ? 'Locked' : 'Unlocked'}</div>
            <div className="security-status-lock-desc">Physical latch is {locked ? 'engaged' : 'disengaged'}.</div>
          </div>
        </div>
        <button
          type="button"
          className="security-status-btn"
          onClick={onUnlock}
          disabled={!wifi || isUnlocking}
        >
          {buttonLabel}
        </button>
        <div className={`security-status-note ${unlockError ? 'is-error' : ''}`}>{helperText}</div>
      </div>
    </section>
  );
};

export default SecurityStatus;
