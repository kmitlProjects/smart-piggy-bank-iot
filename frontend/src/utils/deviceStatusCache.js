const DEVICE_STATUS_STORAGE_KEY = 'piggybank:last-device-status';

function normalizeDeviceStatus(device) {
  if (!device || typeof device !== 'object') {
    return null;
  }

  const normalized = {};

  if (device.wifi_connected !== undefined && device.wifi_connected !== null) {
    normalized.wifi_connected = Boolean(device.wifi_connected);
  }

  if (device.is_locked !== undefined && device.is_locked !== null) {
    normalized.is_locked = Boolean(device.is_locked);
  }

  if (device.last_seen_at) {
    normalized.last_seen_at = device.last_seen_at;
  }

  if (device.updated_at) {
    normalized.updated_at = device.updated_at;
  }

  if (device.connection_status) {
    normalized.connection_status = device.connection_status;
  }

  return Object.keys(normalized).length ? normalized : null;
}

export function readCachedDeviceStatus() {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(DEVICE_STATUS_STORAGE_KEY);
    if (!raw) {
      return null;
    }

    return normalizeDeviceStatus(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function writeCachedDeviceStatus(device) {
  if (typeof window === 'undefined') {
    return null;
  }

  const normalized = normalizeDeviceStatus(device);
  if (!normalized) {
    return null;
  }

  try {
    window.localStorage.setItem(DEVICE_STATUS_STORAGE_KEY, JSON.stringify(normalized));
  } catch {
    return normalized;
  }

  return normalized;
}

