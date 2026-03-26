import React from 'react';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import HeroSection from './HeroSection';
import CoinBreakdown from './CoinBreakdown';
import VaultStatus from './VaultStatus';
import useDashboardData from './useDashboardData';
import { COIN_COLORS } from '../../utils/coinColors';
import SecurityStatus from './SecurityStatus';
import Banner from './Banner';
import './Dashboard.css';

function clampPercent(value) {
  const parsed = Number(value);

  if (Number.isNaN(parsed)) {
    return 0;
  }

  return Math.max(0, Math.min(100, Math.round(parsed)));
}

const Dashboard = () => {
  const {
    loading,
    error,
    unlockError,
    status,
    coins,
    isUnlocking,
    unlock,
  } = useDashboardData();

  const safeStatus = status || {};
  const safeCoins = coins || {};
  const totalSavings = Number(safeCoins.total ?? safeStatus.total ?? 0);
  const coinArr = [1, 2, 5, 10].map((value) => {
    const count = Number(safeCoins[`coin_${value}`] ?? 0);

    return {
      value,
      amount: value * count,
      count,
      color: COIN_COLORS[value],
    };
  });
  const locked = safeStatus.is_locked === undefined || safeStatus.is_locked === null
    ? true
    : Boolean(safeStatus.is_locked);
  const wifi = Boolean(safeStatus.wifi_connected);
  const percent = clampPercent(safeStatus.fill_percent);
  const distance = safeStatus.distance_cm;
  const updatedAt = safeStatus.updated_at || safeStatus.last_seen_at || null;
  const hasContent = Boolean(status || coins);

  return (
    <div className="dashboard-root">
      <Sidebar active="dashboard" />
      <main className="dashboard-main">
        <Topbar wifi={wifi} locked={locked} lastSeenAt={safeStatus.last_seen_at} />
        <div className="dashboard-content">
          {error && (
            <div className="dashboard-alert" role="alert">
              {error}
            </div>
          )}

          {!hasContent && loading ? (
            <div className="dashboard-placeholder">Loading dashboard data...</div>
          ) : (
            <>
              <HeroSection totalSavings={totalSavings} percent={percent} updatedAt={updatedAt} />
              <CoinBreakdown coins={coinArr} />
              <div className="dashboard-bento">
                <VaultStatus percent={percent} distance={distance} isFull={Boolean(safeStatus.is_full)} />
                <SecurityStatus
                  locked={locked}
                  wifi={wifi}
                  isUnlocking={isUnlocking}
                  onUnlock={unlock}
                  unlockError={unlockError}
                />
              </div>
              <Banner />
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
