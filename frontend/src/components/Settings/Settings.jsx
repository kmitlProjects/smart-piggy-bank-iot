import React, { useEffect, useState } from 'react';
import './Settings.css';
import Sidebar from '../Dashboard/Sidebar';

const DEFAULT_REFRESH_INTERVAL_SEC = 5;
const REFRESH_INTERVAL_STORAGE_KEY = 'smart-piggy-refresh-interval-sec';

function readRefreshInterval() {
  if (typeof window === 'undefined') {
    return DEFAULT_REFRESH_INTERVAL_SEC;
  }

  const storedValue = Number(window.localStorage.getItem(REFRESH_INTERVAL_STORAGE_KEY));

  if (!Number.isFinite(storedValue)) {
    return DEFAULT_REFRESH_INTERVAL_SEC;
  }

  return Math.max(1, Math.min(10, storedValue));
}

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
    localIp: '127.0.0.1',
    esp32Ip: 'Unknown',
    connectionStatus: 'UNKNOWN',
    lastSeen: 'No heartbeat received yet',
  });
  const [refreshInterval, setRefreshInterval] = useState(readRefreshInterval);
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
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

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

      setDevice({
        wifiSsid: deviceRes.wifi_ssid || 'Unknown',
        localIp: deviceRes.local_ip || '127.0.0.1',
        esp32Ip: deviceRes.esp32_ip || 'Unknown',
        connectionStatus: deviceRes.connection_status || 'UNKNOWN',
        lastSeen: formatTimestamp(deviceRes.last_seen_at),
      });
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
    await refreshSettings();
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

  const handleIntervalChange = (value) => {
    const safeValue = Math.max(1, Math.min(10, value));
    setRefreshInterval(safeValue);

    if (typeof window !== 'undefined') {
      window.localStorage.setItem(REFRESH_INTERVAL_STORAGE_KEY, String(safeValue));
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
        ? 'RFID enroll mode enabled. The reader will scan cards without unlocking the vault.'
        : 'RFID enroll mode disabled. Normal unlock flow is restored.');
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

  return (
    <div className="settings-root">
      <Sidebar active="settings" onNavigate={onNavigate} />

      <div className="settings-page">
        <div className="settings-header">
          <h2>Configuration</h2>
          <div className="settings-desc">
            Manage device connection, dashboard refresh, and RFID enrollment from the web dashboard.
          </div>
        </div>

        {(error || notice) && (
          <div className={`settings-banner ${error ? 'is-error' : 'is-success'}`}>
            {error || notice}
          </div>
        )}

        <div className="settings-grid">
          <section className="settings-card">
            <div className="settings-card-title">
              <img className="settings-card-icon" src="/icon/sectionSettingPage/Icon.svg" alt="Device" />
              <span>Device Connection</span>
            </div>
            <div className="settings-card-fields">
              <div className="settings-label">Wi-Fi Network</div>
              <div className="settings-input">{device.wifiSsid}</div>
              <div className="settings-label">Backend Host IP</div>
              <div className="settings-input">{device.localIp}</div>
              <div className="settings-label">ESP32 Device IP</div>
              <div className="settings-input">{device.esp32Ip}</div>
              <div className="settings-label">Connection Status</div>
              <div className="settings-input">{device.connectionStatus}</div>
              <div className="settings-label">Last Heartbeat</div>
              <div className="settings-input">{device.lastSeen}</div>
            </div>
            <button className="settings-btn" onClick={handleRefreshConnection}>
              Refresh Connection
            </button>
          </section>

          <section className="settings-card">
            <div className="settings-card-title">
              <img className="settings-card-icon" src="/icon/sectionSettingPage/reflesh.svg" alt="Refresh" />
              <span>Dashboard Refresh Interval</span>
              <span className="settings-interval-value">{refreshInterval}s</span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              value={refreshInterval}
              onChange={(event) => handleIntervalChange(Number(event.target.value))}
            />
            <div className="settings-interval-desc">
              Saved locally in this browser. The dashboard reads this value each time the dashboard page opens.
            </div>
          </section>

          <section className="settings-card settings-card-wide">
            <div className="settings-card-title">
              <img className="settings-card-icon" src="/icon/sectionSettingPage/lockWarning.svg" alt="RFID" />
              <span>RFID Access Control</span>
            </div>
            <div className="settings-note">
              Use scan mode when registering a new card. While scan mode is active, RFID scans are captured for enrollment and will not unlock the vault.
            </div>

            <div className={`settings-enroll-panel ${enrollment.active ? 'is-active' : ''}`}>
              <div className="settings-enroll-text">
                <div className="settings-enroll-title">
                  {enrollment.active ? 'Enrollment Mode Active' : 'Enrollment Mode Inactive'}
                </div>
                <div className="settings-enroll-desc">
                  {enrollment.active
                    ? 'Tap an RFID card on the reader. The latest scanned UID will appear below.'
                    : 'Start scan mode to temporarily pause unlock-by-card and capture the next RFID UID.'}
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
                    ? 'Stop Scan Mode'
                    : 'Start Scan Mode'}
              </button>
            </div>

            <div className="settings-scan-result">
              <div className="settings-label">Latest Scanned UID</div>
              <div className="settings-input">{enrollment.pending_uid || 'Waiting for RFID scan...'}</div>
              <div className="settings-scan-meta">
                {enrollment.last_scanned_at
                  ? `Last scanned: ${formatTimestamp(enrollment.last_scanned_at)}`
                  : 'No card scanned in enrollment mode yet.'}
              </div>
            </div>

            <div className="settings-card-form">
              <div>
                <div className="settings-label">Card UID</div>
                <input
                  className="settings-textbox"
                  value={newCard.uid}
                  onChange={(event) => setNewCard((prev) => ({ ...prev, uid: event.target.value }))}
                  placeholder="[182, 188, 21, 6, 25]"
                />
              </div>
              <div>
                <div className="settings-label">Owner Name</div>
                <input
                  className="settings-textbox"
                  value={newCard.ownerName}
                  onChange={(event) => setNewCard((prev) => ({ ...prev, ownerName: event.target.value }))}
                  placeholder="Student Card / Owner Name"
                />
              </div>
            </div>

            <div className="settings-actions">
              <button
                type="button"
                className="settings-btn small"
                onClick={() => setNewCard((prev) => ({ ...prev, uid: enrollment.pending_uid || prev.uid }))}
                disabled={!enrollment.pending_uid}
              >
                Use Scanned UID
              </button>
              <button
                type="button"
                className="settings-btn small"
                onClick={handleCreateCard}
                disabled={savingCard}
              >
                {savingCard ? 'Saving...' : 'Add Card'}
              </button>
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
          </section>

          <section className="settings-card settings-card-danger">
            <div className="settings-card-title danger">
              <img className="settings-card-icon danger" src="/icon/sectionSettingPage/warning.svg" alt="Danger" />
              <span>Danger Zone</span>
            </div>
            <div className="settings-danger-desc">
              Resetting the counter clears dashboard session data. Authorized RFID cards remain stored.
            </div>
            <button className="settings-btn danger" onClick={handleResetCounter} disabled={resetting}>
              {resetting ? 'Resetting...' : 'Reset coin counter'}
            </button>
          </section>

          <section className="settings-unlock-section">
            <button
              className={`settings-btn unlock ${isUnlocked ? 'unlocked' : ''}`}
              onClick={handleUnlock}
              disabled={isUnlocking}
            >
              {isUnlocking ? 'Unlocking...' : isUnlocked ? 'Vault Unlocked' : 'Unlock vault'}
            </button>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Settings;
