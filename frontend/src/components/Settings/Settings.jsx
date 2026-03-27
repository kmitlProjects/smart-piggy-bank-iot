import React, { useEffect, useRef, useState } from 'react';
import './Settings.css';
import Sidebar from '../Dashboard/Sidebar';
import Topbar from '../Dashboard/Topbar';
import {
  readRefreshIntervalSec,
  writeRefreshIntervalSec,
} from '../../utils/dashboardRefresh';

const REFRESH_APPLY_DELAY_MS = 320;

function formatTimestamp(value) {
  if (!value) {
    return 'No heartbeat received yet';
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return 'No heartbeat received yet';
  }

  return parsed.toLocaleString();
}

function browserAccessInfo() {
  if (typeof window === 'undefined') {
    return {
      host: '',
      url: '',
    };
  }

  const { protocol, hostname, port } = window.location;
  const isLocalOnlyHost = hostname === 'localhost' || hostname === '127.0.0.1';

  if (isLocalOnlyHost || !hostname) {
    return {
      host: '',
      url: '',
    };
  }

  return {
    host: hostname,
    url: `${protocol}//${hostname}${port ? `:${port}` : ''}`,
  };
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, options);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

const Settings = ({ onNavigate }) => {
  const [device, setDevice] = useState({
    wifiSsid: 'Unknown',
    backendContainerIp: '127.0.0.1',
    esp32Ip: 'Unknown',
    connectionStatus: 'UNKNOWN',
    lastSeen: 'No heartbeat received yet',
    lastSeenAt: null,
    dashboardRefreshSec: readRefreshIntervalSec(),
    dashboardHost: '',
    dashboardUrl: '',
    apiUrl: '',
  });
  const [refreshInterval, setRefreshInterval] = useState(readRefreshIntervalSec);
  const [rfidCards, setRfidCards] = useState([]);
  const [enrollment, setEnrollment] = useState({
    active: false,
    pending_uid: null,
    last_scanned_at: null,
  });
  const [newCard, setNewCard] = useState({
    uid: '',
    ownerName: '',
  });
  const [editingCardId, setEditingCardId] = useState(null);
  const [editingCard, setEditingCard] = useState({
    uid: '',
    ownerName: '',
  });
  const [isUnlocking, setIsUnlocking] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [savingCard, setSavingCard] = useState(false);
  const [togglingEnroll, setTogglingEnroll] = useState(false);
  const [workingCardId, setWorkingCardId] = useState(null);
  const [refreshingConnection, setRefreshingConnection] = useState(false);
  const [savingInterval, setSavingInterval] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const intervalTimerRef = useRef(null);

  const refreshSettings = async ({ silent = false } = {}) => {
    if (!silent) {
      setError('');
    }

    try {
      const [deviceRes, cardsRes, statusRes, enrollmentRes] = await Promise.all([
        fetchJson('/api/device'),
        fetchJson('/api/rfid/cards?active_only=true'),
        fetchJson('/api/status'),
        fetchJson('/api/rfid/enroll-mode'),
      ]);

      const syncedRefreshInterval = Number.isFinite(Number(deviceRes.dashboard_refresh_sec))
        ? writeRefreshIntervalSec(deviceRes.dashboard_refresh_sec)
        : readRefreshIntervalSec();
      const browserAccess = browserAccessInfo();
      const dashboardHost = deviceRes.dashboard_host || browserAccess.host || '';
      const dashboardUrl = deviceRes.dashboard_url || browserAccess.url || '';

      setDevice({
        wifiSsid: deviceRes.wifi_ssid || 'Unknown',
        backendContainerIp: deviceRes.backend_container_ip || deviceRes.local_ip || '127.0.0.1',
        esp32Ip: deviceRes.esp32_ip || 'Unknown',
        connectionStatus: deviceRes.connection_status || 'UNKNOWN',
        lastSeen: formatTimestamp(deviceRes.last_seen_at),
        lastSeenAt: deviceRes.last_seen_at || null,
        dashboardRefreshSec: syncedRefreshInterval,
        dashboardHost,
        dashboardUrl,
        apiUrl: deviceRes.api_url || '',
      });
      setRefreshInterval(syncedRefreshInterval);
      setRfidCards(Array.isArray(cardsRes.cards) ? cardsRes.cards : []);
      setEnrollment(enrollmentRes.enrollment || {
        active: false,
        pending_uid: null,
        last_scanned_at: null,
      });

      const status = statusRes.status || {};
      setIsUnlocked(status.is_locked === false || status.is_locked === 0);
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to load settings');
    }
  };

  useEffect(() => {
    refreshSettings();

    return () => {
      if (intervalTimerRef.current) {
        window.clearTimeout(intervalTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!enrollment.active) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      refreshSettings({ silent: true });
    }, 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, [enrollment.active]);

  useEffect(() => {
    if (!enrollment.pending_uid) {
      return;
    }

    setNewCard((prev) => ({
      ...prev,
      uid: enrollment.pending_uid,
    }));
  }, [enrollment.pending_uid]);

  const handleRefreshConnection = async () => {
    setRefreshingConnection(true);

    try {
      await refreshSettings();
    } finally {
      setRefreshingConnection(false);
    }
  };

  const applyRefreshInterval = async (intervalSec) => {
    setSavingInterval(true);
    setError('');

    try {
      const response = await fetchJson('/api/device/refresh-interval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: 'esp32',
          interval_sec: intervalSec,
        }),
      });

      const appliedInterval = Number.isFinite(Number(response.dashboard_refresh_sec))
        ? writeRefreshIntervalSec(response.dashboard_refresh_sec)
        : writeRefreshIntervalSec(intervalSec);

      setRefreshInterval(appliedInterval);
      setDevice((prev) => ({
        ...prev,
        dashboardRefreshSec: appliedInterval,
      }));
    } catch (saveError) {
      setError(
        saveError.message
          || 'Refresh interval was saved in this browser, but the device heartbeat could not be updated.',
      );
    } finally {
      setSavingInterval(false);
    }
  };

  const handleIntervalChange = (value) => {
    const safeValue = writeRefreshIntervalSec(value);
    setRefreshInterval(safeValue);
    setDevice((prev) => ({
      ...prev,
      dashboardRefreshSec: safeValue,
    }));
    setSavingInterval(true);

    if (intervalTimerRef.current) {
      window.clearTimeout(intervalTimerRef.current);
    }

    intervalTimerRef.current = window.setTimeout(() => {
      applyRefreshInterval(safeValue);
    }, REFRESH_APPLY_DELAY_MS);
  };

  const handleUnlock = async () => {
    setIsUnlocking(true);
    setError('');
    setNotice('');

    try {
      await fetchJson('/api/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: 'esp32', duration_ms: 5000 }),
      });
      setNotice('Unlock command sent to ESP32.');
      await refreshSettings({ silent: true });
    } catch (unlockError) {
      setError(unlockError.message || 'Unlock failed');
    } finally {
      setIsUnlocking(false);
    }
  };

  const handleResetCounter = async () => {
    setResetting(true);
    setError('');
    setNotice('');

    try {
      await fetchJson('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clear_cards: false }),
      });
      setNotice('Reset command sent. Dashboard data will refresh shortly.');
      await refreshSettings({ silent: true });
    } catch (resetError) {
      setError(resetError.message || 'Reset failed');
    } finally {
      setResetting(false);
    }
  };

  const handleToggleEnroll = async (active) => {
    setTogglingEnroll(true);
    setError('');
    setNotice('');

    try {
      const response = await fetchJson('/api/rfid/enroll-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active }),
      });
      setEnrollment(response.enrollment || {
        active: false,
        pending_uid: null,
        last_scanned_at: null,
      });
      setNotice(active
        ? 'Scan mode enabled. RFID taps will be captured for enrollment and will not unlock the vault.'
        : 'Scan mode disabled. Normal unlock-by-card flow is restored.');
      if (!active) {
        setNewCard((prev) => ({ ...prev, uid: '' }));
      }
    } catch (enrollError) {
      setError(enrollError.message || 'Failed to update enroll mode');
    } finally {
      setTogglingEnroll(false);
    }
  };

  const handleCreateCard = async () => {
    if (!newCard.uid.trim()) {
      setError('Scan a card or type a UID before adding it.');
      return;
    }

    setSavingCard(true);
    setError('');
    setNotice('');

    try {
      await fetchJson('/api/rfid/cards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uid: newCard.uid.trim(),
          owner_name: newCard.ownerName.trim() || null,
        }),
      });
      setNewCard({ uid: '', ownerName: '' });
      setNotice('RFID card saved successfully.');
      await refreshSettings({ silent: true });
    } catch (saveError) {
      setError(saveError.message || 'Failed to save RFID card');
    } finally {
      setSavingCard(false);
    }
  };

  const startEditingCard = (card) => {
    setEditingCardId(card.id);
    setEditingCard({
      uid: card.uid || '',
      ownerName: card.owner_name || '',
    });
  };

  const cancelEditingCard = () => {
    setEditingCardId(null);
    setEditingCard({ uid: '', ownerName: '' });
  };

  const handleSaveCardEdit = async (cardId) => {
    if (!editingCard.uid.trim()) {
      setError('UID cannot be empty.');
      return;
    }

    setWorkingCardId(cardId);
    setError('');
    setNotice('');

    try {
      await fetchJson(`/api/rfid/cards/${cardId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uid: editingCard.uid.trim(),
          owner_name: editingCard.ownerName.trim() || null,
        }),
      });
      setNotice('RFID card updated.');
      cancelEditingCard();
      await refreshSettings({ silent: true });
    } catch (updateError) {
      setError(updateError.message || 'Failed to update RFID card');
    } finally {
      setWorkingCardId(null);
    }
  };

  const handleDeleteCard = async (cardId) => {
    setWorkingCardId(cardId);
    setError('');
    setNotice('');

    try {
      await fetchJson(`/api/rfid/cards/${cardId}`, {
        method: 'DELETE',
      });
      setNotice('RFID card removed.');
      if (editingCardId === cardId) {
        cancelEditingCard();
      }
      await refreshSettings({ silent: true });
    } catch (deleteError) {
      setError(deleteError.message || 'Failed to delete RFID card');
    } finally {
      setWorkingCardId(null);
    }
  };

  const isConnected = device.connectionStatus === 'CONNECTED';
  const locked = !isUnlocked;
  const scanStatusText = enrollment.last_scanned_at
    ? `Last scanned: ${formatTimestamp(enrollment.last_scanned_at)}`
    : 'No card scanned in scan mode yet.';

  return (
    <div className="settings-root">
      <Sidebar active="settings" onNavigate={onNavigate} />

      <main className="settings-page">
        <Topbar wifi={isConnected} locked={locked} lastSeenAt={device.lastSeenAt} />

        <div className="settings-content">
          <header className="settings-header">
            <h2>Configuration</h2>
            <div className="settings-desc">
              Tune the live dashboard cadence, manage RFID access, and keep service actions in one place.
            </div>
          </header>

          {(error || notice) && (
            <div className={`settings-banner ${error ? 'is-error' : 'is-success'}`}>
              {error || notice}
            </div>
          )}

          <div className="settings-shell">
            <div className="settings-overview-grid">
              <section className="settings-card settings-card-device">
              <div className="settings-card-head">
                <div className="settings-card-title">
                  <img className="settings-card-icon" src="/icon/sectionSettingPage/ipAddress.svg" alt="Device" />
                  <span>Device Connection</span>
                </div>
                <button
                  type="button"
                  className="settings-btn small secondary"
                  onClick={handleRefreshConnection}
                  disabled={refreshingConnection}
                >
                  {refreshingConnection ? 'Syncing...' : 'Sync now'}
                </button>
              </div>

              <div className="settings-status-strip">
                <span className={`settings-pill ${isConnected ? 'is-connected' : 'is-disconnected'}`}>
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
                <span className="settings-status-copy">Last heartbeat: {device.lastSeen}</span>
              </div>

              <div className="settings-detail-grid">
                <div className="settings-detail-item">
                  <span className="settings-label">Wi-Fi network</span>
                  <span className="settings-detail-value">{device.wifiSsid}</span>
                </div>
                <div className="settings-detail-item">
                  <span className="settings-label">Dashboard access host</span>
                  <span className="settings-detail-value settings-detail-value-code">
                    {device.dashboardHost || 'Set PUBLIC_DASHBOARD_HOST in backend/.env'}
                  </span>
                </div>
                <div className="settings-detail-item">
                  <span className="settings-label">ESP32 device IP</span>
                  <span className="settings-detail-value settings-detail-value-code">{device.esp32Ip}</span>
                </div>
                <div className="settings-detail-item">
                  <span className="settings-label">Current heartbeat cadence</span>
                  <span className="settings-detail-value">{device.dashboardRefreshSec}s</span>
                </div>
                <div className="settings-detail-item">
                  <span className="settings-label">Dashboard access URL</span>
                  <span className="settings-detail-value settings-detail-value-code">
                    {device.dashboardUrl || 'Open this page via LAN IP or set PUBLIC_DASHBOARD_HOST'}
                  </span>
                </div>
                <div className="settings-detail-item">
                  <span className="settings-label">Backend container IP</span>
                  <span className="settings-detail-value settings-detail-value-code">{device.backendContainerIp}</span>
                </div>
              </div>
              </section>

              <section className="settings-card settings-card-refresh">
              <div className="settings-card-head">
                <div className="settings-card-title">
                  <img className="settings-card-icon" src="/icon/sectionSettingPage/reflesh.svg" alt="Refresh" />
                  <span>Dashboard Refresh Interval</span>
                </div>
                <div className="settings-interval-meta">
                  <span className="settings-interval-value">{refreshInterval}s</span>
                  <span className={`settings-inline-state ${savingInterval ? 'is-pending' : 'is-live'}`}>
                    {savingInterval ? 'Applying...' : 'Live'}
                  </span>
                </div>
              </div>

              <div className="settings-interval-copy">
                <p>Controls how often the dashboard requests fresh backend data.</p>
                <p>This value is also sent to the ESP32 heartbeat interval. The board needs the latest firmware to acknowledge it.</p>
              </div>

              <input
                className="settings-slider"
                type="range"
                min={1}
                max={10}
                value={refreshInterval}
                onChange={(event) => handleIntervalChange(Number(event.target.value))}
              />

              <div className="settings-slider-scale" aria-hidden="true">
                <span>1s</span>
                <span>5s</span>
                <span>10s</span>
              </div>
              </section>
            </div>

            <section className="settings-card settings-card-wide settings-card-rfid">
              <div className="settings-card-head">
                <div className="settings-card-title">
                  <img className="settings-card-icon" src="/icon/sectionSettingPage/lockWarning.svg" alt="RFID" />
                  <span>RFID Access Control</span>
                </div>
                <span className={`settings-pill ${enrollment.active ? 'is-active' : 'is-muted'}`}>
                  {enrollment.active ? 'Scan mode on' : 'Scan mode off'}
                </span>
              </div>

            <div className="settings-note">
              When scan mode is on, RFID taps are captured for enrollment and unlock-by-card is paused temporarily.
            </div>

            <div className="settings-rfid-grid">
              <div className="settings-rfid-main">
                <div className={`settings-enroll-panel ${enrollment.active ? 'is-active' : ''}`}>
                  <div className="settings-enroll-text">
                    <div className="settings-enroll-title">
                      {enrollment.active ? 'Reader is waiting for a card' : 'Start scan mode before adding a new card'}
                    </div>
                    <div className="settings-enroll-desc">
                      {enrollment.active
                        ? 'Tap a card on the ESP32 reader. The captured UID will fill the form below automatically.'
                        : 'Enable scan mode when you want to capture a new UID without triggering a vault unlock.'}
                    </div>
                  </div>
                  <button
                    type="button"
                    className={`settings-btn small ${enrollment.active ? 'danger' : ''}`}
                    onClick={() => handleToggleEnroll(!enrollment.active)}
                    disabled={togglingEnroll}
                  >
                    {togglingEnroll
                      ? 'Updating...'
                      : enrollment.active
                        ? 'Stop'
                        : 'Start'}
                  </button>
                </div>

                <div className="settings-scan-result">
                  <div className="settings-field-head">
                    <span className="settings-label">Latest scanned UID</span>
                    <span className="settings-scan-meta">{scanStatusText}</span>
                  </div>
                  <div className="settings-display-box">
                    {enrollment.pending_uid || 'Waiting for RFID scan...'}
                  </div>
                </div>

                <div className="settings-card-form">
                  <div>
                    <div className="settings-label">Card UID</div>
                    <input
                      className="settings-textbox"
                      value={newCard.uid}
                      onChange={(event) => setNewCard((prev) => ({ ...prev, uid: event.target.value }))}
                      placeholder="e.g. [182, 188, 21, 6, 25]"
                    />
                  </div>
                  <div>
                    <div className="settings-label">Owner name</div>
                    <input
                      className="settings-textbox"
                      value={newCard.ownerName}
                      onChange={(event) => setNewCard((prev) => ({ ...prev, ownerName: event.target.value }))}
                      placeholder="Enter your owner name"
                    />
                  </div>
                </div>

                <div className="settings-form-actions">
                  <button
                    type="button"
                    className="settings-btn small"
                    onClick={handleCreateCard}
                    disabled={savingCard}
                  >
                    {savingCard ? 'Saving...' : 'Add card'}
                  </button>
                </div>
              </div>

              <div className="settings-rfid-side">
                <div className="settings-side-head">
                  <div className="settings-side-title">Authorized cards</div>
                  <div className="settings-side-count">{rfidCards.length} active</div>
                </div>

                <div className="settings-list">
                  {rfidCards.length === 0 ? (
                    <div className="settings-empty">No active RFID cards in backend yet.</div>
                  ) : (
                    rfidCards.map((card) => {
                      const isEditing = editingCardId === card.id;
                      const isWorking = workingCardId === card.id;

                      return (
                        <div className="settings-card-row" key={card.id}>
                          <div className="settings-card-row-main">
                            {isEditing ? (
                              <>
                                <input
                                  className="settings-textbox"
                                  value={editingCard.uid}
                                  onChange={(event) => setEditingCard((prev) => ({ ...prev, uid: event.target.value }))}
                                  placeholder="RFID UID"
                                />
                                <input
                                  className="settings-textbox"
                                  value={editingCard.ownerName}
                                  onChange={(event) => setEditingCard((prev) => ({ ...prev, ownerName: event.target.value }))}
                                  placeholder="Owner name"
                                />
                              </>
                            ) : (
                              <>
                                <div className="settings-card-row-title">
                                  {card.owner_name || 'Unnamed card'}
                                </div>
                                <div className="settings-card-row-subtitle">{card.uid}</div>
                              </>
                            )}
                          </div>

                          <div className="settings-card-row-actions">
                            {isEditing ? (
                              <>
                                <button
                                  type="button"
                                  className="settings-btn small"
                                  onClick={() => handleSaveCardEdit(card.id)}
                                  disabled={isWorking}
                                >
                                  {isWorking ? 'Saving...' : 'Save'}
                                </button>
                                <button
                                  type="button"
                                  className="settings-btn small secondary"
                                  onClick={cancelEditingCard}
                                  disabled={isWorking}
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  type="button"
                                  className="settings-btn small secondary"
                                  onClick={() => startEditingCard(card)}
                                  disabled={isWorking}
                                >
                                  Edit
                                </button>
                                <button
                                  type="button"
                                  className="settings-btn small danger"
                                  onClick={() => handleDeleteCard(card.id)}
                                  disabled={isWorking}
                                >
                                  {isWorking ? 'Removing...' : 'Delete'}
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
            </section>

            <section className="settings-card settings-card-wide settings-card-maintenance">
              <div className="settings-card-head">
                <div className="settings-card-title">
                  <img className="settings-card-icon" src="/icon/sectionSettingPage/unlock.svg" alt="Manual control" />
                  <span>Manual Vault Control</span>
                </div>
                <span className={`settings-pill ${isUnlocked ? 'is-active' : 'is-muted'}`}>
                  {isUnlocked ? 'Unlocked' : 'Locked'}
                </span>
              </div>

              <div className="settings-note">
                Use this action when you need a one-time web unlock. It does not replace RFID authorization.
              </div>

              <div className="settings-maintenance-actions">
                <button
                  className={`settings-btn unlock ${isUnlocked ? 'unlocked' : ''}`}
                  onClick={handleUnlock}
                  disabled={isUnlocking}
                >
                  {isUnlocking ? 'Unlocking...' : isUnlocked ? 'Vault unlocked' : 'Unlock vault'}
                </button>
              </div>
            </section>

            <section className="settings-card settings-card-wide settings-card-danger">
              <div className="settings-card-head">
                <div className="settings-card-title danger">
                  <img className="settings-card-icon" src="/icon/sectionSettingPage/warning.svg" alt="Danger" />
                  <span>Danger Zone</span>
                </div>
              </div>

              <div className="settings-danger-copy">
                Resetting the counter clears dashboard session data and recent device state. Authorized RFID cards stay stored.
              </div>

              <button className="settings-btn danger" onClick={handleResetCounter} disabled={resetting}>
                {resetting ? 'Resetting...' : 'Reset coin counter'}
              </button>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Settings;
