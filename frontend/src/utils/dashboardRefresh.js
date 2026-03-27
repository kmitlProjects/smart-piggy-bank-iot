export const DEFAULT_REFRESH_INTERVAL_SEC = 5;
export const REFRESH_INTERVAL_STORAGE_KEY = 'smart-piggy-refresh-interval-sec';
export const REFRESH_INTERVAL_EVENT = 'smart-piggy-refresh-interval-change';
export const MIN_REFRESH_INTERVAL_SEC = 1;
export const MAX_REFRESH_INTERVAL_SEC = 10;

export function clampRefreshIntervalSec(value) {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return DEFAULT_REFRESH_INTERVAL_SEC;
  }

  return Math.max(MIN_REFRESH_INTERVAL_SEC, Math.min(MAX_REFRESH_INTERVAL_SEC, Math.round(numericValue)));
}

export function readRefreshIntervalSec() {
  if (typeof window === 'undefined') {
    return DEFAULT_REFRESH_INTERVAL_SEC;
  }

  return clampRefreshIntervalSec(window.localStorage.getItem(REFRESH_INTERVAL_STORAGE_KEY));
}

export function writeRefreshIntervalSec(value) {
  const safeValue = clampRefreshIntervalSec(value);

  if (typeof window === 'undefined') {
    return safeValue;
  }

  window.localStorage.setItem(REFRESH_INTERVAL_STORAGE_KEY, String(safeValue));
  window.dispatchEvent(new CustomEvent(REFRESH_INTERVAL_EVENT, { detail: safeValue }));
  return safeValue;
}
