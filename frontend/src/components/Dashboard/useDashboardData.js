import { useEffect, useRef, useState } from 'react';
import {
  DEFAULT_REFRESH_INTERVAL_SEC,
  REFRESH_INTERVAL_EVENT,
  REFRESH_INTERVAL_STORAGE_KEY,
  clampRefreshIntervalSec,
  readRefreshIntervalSec,
} from '../../utils/dashboardRefresh';

function getPollIntervalMs(value = readRefreshIntervalSec()) {
  return clampRefreshIntervalSec(value) * 1000;
}

async function fetchJson(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 7000);

  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    return response.json();
  } finally {
    clearTimeout(timeout);
  }
}

export default function useDashboardData() {
  const [data, setData] = useState({
    loading: true,
    error: null,
    unlockError: null,
    status: null,
    coins: null,
    isUnlocking: false,
  });

  const mountedRef = useRef(false);
  const pollingRef = useRef(null);
  const followUpRefreshRef = useRef(null);
  const inFlightRef = useRef(false);

  const restartPolling = (value) => {
    if (typeof window === 'undefined') {
      return;
    }

    if (pollingRef.current) {
      window.clearInterval(pollingRef.current);
    }

    pollingRef.current = window.setInterval(() => {
      refresh();
    }, getPollIntervalMs(value));
  };

  const refresh = async ({ showLoading = false } = {}) => {
    if (inFlightRef.current) {
      return;
    }

    inFlightRef.current = true;

    if (showLoading) {
      setData((prev) => ({ ...prev, loading: true, error: null }));
    } else {
      setData((prev) => ({ ...prev, error: null }));
    }

    try {
      const [statusRes, coinsRes] = await Promise.all([
        fetchJson('/api/status'),
        fetchJson('/api/coins/summary'),
      ]);

      if (!mountedRef.current) {
        return;
      }

      setData((prev) => ({
        ...prev,
        loading: false,
        error: null,
        status: statusRes.status || {},
        coins: coinsRes.summary || {},
      }));
    } catch (error) {
      if (!mountedRef.current) {
        return;
      }

      setData((prev) => ({
        ...prev,
        loading: false,
        error: error.message || 'Cannot load dashboard data',
      }));
    } finally {
      inFlightRef.current = false;
    }
  };

  const unlock = async () => {
    setData((prev) => ({
      ...prev,
      isUnlocking: true,
      unlockError: null,
    }));

    try {
      await fetchJson('/api/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: 'esp32', duration_ms: 5000 }),
      });

      await refresh();

      if (followUpRefreshRef.current) {
        clearTimeout(followUpRefreshRef.current);
      }

      followUpRefreshRef.current = setTimeout(() => {
        refresh();
      }, 1200);

      return true;
    } catch (error) {
      if (!mountedRef.current) {
        return false;
      }

      setData((prev) => ({
        ...prev,
        unlockError: error.message || 'Unlock failed',
      }));

      return false;
    } finally {
      if (mountedRef.current) {
        setData((prev) => ({
          ...prev,
          isUnlocking: false,
        }));
      }
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }

    mountedRef.current = true;
    refresh({ showLoading: true });
    restartPolling();

    const handleRefreshIntervalChange = (event) => {
      const nextValue = clampRefreshIntervalSec(event?.detail ?? readRefreshIntervalSec());
      window.localStorage.setItem(REFRESH_INTERVAL_STORAGE_KEY, String(nextValue));
      restartPolling(nextValue);
      refresh();
    };

    const handleStorageSync = (event) => {
      if (event.key !== REFRESH_INTERVAL_STORAGE_KEY) {
        return;
      }

      handleRefreshIntervalChange({ detail: event.newValue ?? DEFAULT_REFRESH_INTERVAL_SEC });
    };

    window.addEventListener(REFRESH_INTERVAL_EVENT, handleRefreshIntervalChange);
    window.addEventListener('storage', handleStorageSync);

    return () => {
      mountedRef.current = false;

      if (pollingRef.current) {
        window.clearInterval(pollingRef.current);
      }

      if (followUpRefreshRef.current) {
        window.clearTimeout(followUpRefreshRef.current);
      }

      window.removeEventListener(REFRESH_INTERVAL_EVENT, handleRefreshIntervalChange);
      window.removeEventListener('storage', handleStorageSync);
    };
  }, []);

  return {
    ...data,
    refresh,
    unlock,
  };
}
