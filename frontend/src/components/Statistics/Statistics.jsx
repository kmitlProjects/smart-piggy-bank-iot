import React, { useCallback, useEffect, useMemo, useState } from 'react';
import Sidebar from '../Dashboard/Sidebar';
import Topbar from '../Dashboard/Topbar';
import { COIN_COLORS } from '../../utils/coinColors';
import './Statistics.css';

const COIN_ORDER = [10, 5, 2, 1];
const COIN_LABELS = {
  1: '1 Baht',
  2: '2 Baht',
  5: '5 Baht',
  10: '10 Baht',
};

function formatNumber(value) {
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 0,
  }).format(Number(value) || 0);
}

function formatCurrency(value, options = {}) {
  const { minimumFractionDigits = 0, maximumFractionDigits = 0 } = options;

  return new Intl.NumberFormat('th-TH', {
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(Number(value) || 0);
}

function formatSignedPercent(value) {
  const numericValue = Number(value) || 0;
  const sign = numericValue > 0 ? '+' : '';
  return `${sign}${numericValue.toFixed(1)}%`;
}

function buildArcGradient(segments) {
  const total = segments.reduce((sum, segment) => sum + segment.count, 0);

  if (!total) {
    return 'conic-gradient(from -90deg, rgba(148, 163, 184, 0.24) 0deg 360deg)';
  }

  let cursor = 0;
  const stops = segments.map((segment) => {
    const sweep = (segment.count / total) * 360;
    const start = cursor;
    cursor += sweep;
    return `${segment.color} ${start}deg ${cursor}deg`;
  });

  return `conic-gradient(from -90deg, ${stops.join(', ')})`;
}

function LineChart({ series }) {
  const width = 720;
  const height = 260;
  const padding = { top: 20, right: 16, bottom: 42, left: 12 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const values = series.map((point) => Number(point.value) || 0);
  const maxValue = Math.max(...values, 1);

  const points = series.map((point, index) => {
    const x = padding.left + (
      series.length === 1 ? innerWidth / 2 : (innerWidth / Math.max(series.length - 1, 1)) * index
    );
    const y = padding.top + innerHeight - ((Number(point.value) || 0) / maxValue) * innerHeight;
    return { ...point, x, y };
  });

  const path = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(' ');

  const areaPath = points.length
    ? `${path} L ${points[points.length - 1].x.toFixed(2)} ${(padding.top + innerHeight).toFixed(2)} L ${points[0].x.toFixed(2)} ${(padding.top + innerHeight).toFixed(2)} Z`
    : '';

  return (
    <div className="statistics-line-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Savings growth over time">
        {[0, 1, 2, 3].map((lineIndex) => {
          const y = padding.top + (innerHeight / 3) * lineIndex;
          return <line key={lineIndex} x1={padding.left} x2={width - padding.right} y1={y} y2={y} />;
        })}
        {areaPath && <path className="statistics-line-area" d={areaPath} />}
        {path && <path className="statistics-line-path" d={path} />}
        {points.map((point) => (
          <g key={point.date}>
            <circle className="statistics-line-point-shadow" cx={point.x} cy={point.y} r="8" />
            <circle className="statistics-line-point" cx={point.x} cy={point.y} r="4.5" />
          </g>
        ))}
      </svg>
      <div className="statistics-line-labels">
        {series.map((point, index) => {
          const showLabel = series.length <= 10 || index === 0 || index === series.length - 1 || index % 5 === 0;
          return <span key={point.date}>{showLabel ? point.label : ''}</span>;
        })}
      </div>
    </div>
  );
}

function DistributionChart({ distribution }) {
  const segments = COIN_ORDER.map((denomination) => ({
    denomination,
    label: COIN_LABELS[denomination],
    color: COIN_COLORS[denomination],
    count: Number(distribution?.counts?.[String(denomination)] || 0),
    value: Number(distribution?.values?.[String(denomination)] || 0),
  }));
  const totalCount = Number(distribution?.total_count || 0);
  const gradient = buildArcGradient(segments);

  return (
    <div className="statistics-distribution-card">
      <div className="statistics-donut-wrap">
        <div className="statistics-donut" style={{ background: gradient }}>
          <div className="statistics-donut-center">
            <span>Total</span>
            <strong>{formatNumber(totalCount)}</strong>
          </div>
        </div>
      </div>
      <div className="statistics-legend">
        {segments.map((segment) => {
          const percentage = totalCount ? (segment.count / totalCount) * 100 : 0;
          return (
            <div key={segment.denomination} className="statistics-legend-item">
              <span className="statistics-legend-dot" style={{ backgroundColor: segment.color }}></span>
              <div>
                <strong>{segment.label}</strong>
                <span>
                  {formatNumber(segment.count)} coins · ฿{formatCurrency(segment.value)} · {percentage.toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Statistics({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [range, setRange] = useState('7d');

  const loadStatistics = useCallback(async () => {
    try {
      const response = await fetch('/api/statistics');
      if (!response.ok) {
        throw new Error(`Failed to fetch statistics (${response.status})`);
      }

      const payload = await response.json();
      setStats(payload);
      setError('');
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to fetch statistics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    const run = async () => {
      if (!mounted) {
        return;
      }
      await loadStatistics();
    };

    run();
    const intervalId = window.setInterval(run, 15000);

    return () => {
      mounted = false;
      window.clearInterval(intervalId);
    };
  }, [loadStatistics]);

  const summary = stats?.summary ?? {};
  const distribution = stats?.coin_distribution ?? { counts: {}, values: {}, total_count: 0 };
  const insights = stats?.insights ?? {};
  const device = stats?.device ?? {};
  const meta = stats?.meta ?? {};
  const lineSeries = stats?.savings_growth?.[range] ?? [];
  const mostFrequentCoinValue = summary?.most_frequent_coin?.value ?? null;
  const monthlyChange = Number(summary?.coins_vs_previous_30d_percent || 0);
  const trendLabel = summary?.coins_previous_30d > 0
    ? `${formatSignedPercent(monthlyChange)} vs previous 30 days`
    : (summary?.coins_last_30d > 0 ? 'First 30-day window recorded' : 'Waiting for coin activity');

  const mostFrequentCoinText = mostFrequentCoinValue ? `฿${mostFrequentCoinValue}` : 'No coin yet';
  const statsReady = Boolean(stats);
  const hasCoinData = Boolean(meta?.has_coin_data);
  const locked = device.is_locked === undefined ? true : Boolean(device.is_locked);

  const balanceHighlights = useMemo(() => ([
    {
      label: 'Recorded Snapshots',
      value: formatNumber(meta?.recorded_snapshots || 0),
      icon: '/icon/sectionStatisticsPage/Record.svg',
    },
    {
      label: 'Derived Deposits',
      value: formatNumber(meta?.derived_deposit_events || 0),
      icon: '/icon/sectionStatisticsPage/process.svg',
    },
  ]), [meta]);

  return (
    <div className="statistics-shell">
      <Sidebar active="statistics" onNavigate={onNavigate} />
      <main className="statistics-main">
        <Topbar wifi={Boolean(device.wifi_connected)} locked={locked} lastSeenAt={device.last_seen_at} />
        <div className="statistics-content">
          {error && (
            <div className="statistics-alert" role="alert">
              {error}
            </div>
          )}

          {!statsReady && loading ? (
            <div className="statistics-placeholder">Loading statistics from device timeseries...</div>
          ) : (
            <>
              <section className="statistics-hero">
                <div className="statistics-hero-copy">
                  <p className="statistics-eyebrow">Statistics</p>
                  <h1>Vault Analytics</h1>
                  <p className="statistics-hero-text">
                    Deep dive into savings growth, denomination mix, and vault health derived from the cumulative
                    timeseries snapshots stored in the backend database.
                  </p>
                </div>
                <div className="statistics-hero-panel">
                  <div className="statistics-hero-balance">
                    <span className="statistics-hero-label">Observed Balance</span>
                    <strong>฿{formatCurrency(summary?.total_value ?? insights?.current_balance ?? 0)}</strong>
                    <span className="statistics-hero-note">
                      {hasCoinData ? 'Derived from positive deltas between snapshots' : 'No deposit deltas recorded yet'}
                    </span>
                  </div>
                  <div className="statistics-hero-metrics">
                    {balanceHighlights.map((item) => (
                      <div key={item.label} className="statistics-hero-metric">
                        <img src={item.icon} alt="" aria-hidden="true" />
                        <div>
                          <span>{item.label}</span>
                          <strong>{item.value}</strong>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              <section className="statistics-summary-grid">
                <article className="statistics-summary-card is-primary">
                  <div className="statistics-summary-header">
                    <span>Total Coins Counted</span>
                    <img src="/icon/sectionStatisticsPage/statistics.svg" alt="" aria-hidden="true" />
                  </div>
                  <strong>{formatNumber(summary?.total_coins_counted || 0)}</strong>
                  <p>{trendLabel}</p>
                </article>

                <article className="statistics-summary-card">
                  <div className="statistics-summary-header">
                    <span>Most Frequent Coin</span>
                    <img src="/icon/sectionStatisticsPage/frequency.svg" alt="" aria-hidden="true" />
                  </div>
                  <strong>{mostFrequentCoinText}</strong>
                  <p>
                    {summary?.most_frequent_coin?.count
                      ? `${formatNumber(summary.most_frequent_coin.count)} recorded insertions`
                      : 'The system will flag a dominant denomination once deposits begin'}
                  </p>
                </article>

                <article className="statistics-summary-card">
                  <div className="statistics-summary-header">
                    <span>Average Coin Value</span>
                    <img src="/icon/sectionStatisticsPage/value.svg" alt="" aria-hidden="true" />
                  </div>
                  <strong>฿{formatCurrency(summary?.average_coin_value || 0, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                  <p>Mean value per detected coin insertion across the recorded history.</p>
                </article>
              </section>

              <section className="statistics-main-grid">
                <article className="statistics-card statistics-chart-card">
                  <div className="statistics-card-header">
                    <div>
                      <h2>Savings Growth Over Time</h2>
                      <p>
                        {range === '7d'
                          ? 'Observed balance across the last 7 days.'
                          : 'Observed balance across the last 30 days.'}
                      </p>
                    </div>
                    <div className="statistics-range-switcher" role="tablist" aria-label="Savings growth range">
                      <button
                        type="button"
                        className={range === '7d' ? 'active' : ''}
                        onClick={() => setRange('7d')}
                      >
                        Last 7 Days
                      </button>
                      <button
                        type="button"
                        className={range === '30d' ? 'active' : ''}
                        onClick={() => setRange('30d')}
                      >
                        Last Month
                      </button>
                    </div>
                  </div>
                  <LineChart series={lineSeries} />
                </article>

                <article className="statistics-card">
                  <div className="statistics-card-header">
                    <div>
                      <h2>Coin Distribution</h2>
                      <p>Share of each denomination across all inferred coin insertions.</p>
                    </div>
                    <img
                      src="/icon/sectionStatisticsPage/distribution.svg"
                      alt=""
                      aria-hidden="true"
                      className="statistics-card-icon"
                    />
                  </div>
                  <DistributionChart distribution={distribution} />
                </article>
              </section>

              <section className="statistics-insights-panel">
                <div className="statistics-insights-header">
                  <div>
                    <h2>System Insights</h2>
                    <p>Operational signals computed from savings history, live status, and vault telemetry.</p>
                  </div>
                </div>
                <div className="statistics-insights-grid">
                  <article className="statistics-insight-card">
                    <div className="statistics-insight-label">Growth Velocity</div>
                    <div className="statistics-insight-value">{formatSignedPercent(insights?.growth_velocity_percent || 0)}</div>
                    <div className="statistics-insight-meta">7-day value change vs the previous 7-day window</div>
                    <img src="/icon/sectionStatisticsPage/growth.svg" alt="" aria-hidden="true" />
                  </article>

                  <article className="statistics-insight-card">
                    <div className="statistics-insight-label">Avg Value</div>
                    <div className="statistics-insight-value">
                      ฿{formatCurrency(insights?.avg_coin_value || 0, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div className="statistics-insight-meta">Average denomination value per inserted coin</div>
                    <img src="/icon/sectionStatisticsPage/value.svg" alt="" aria-hidden="true" />
                  </article>

                  <article className="statistics-insight-card">
                    <div className="statistics-insight-label">Vault Capacity</div>
                    <div className="statistics-insight-value">{formatNumber(insights?.vault_capacity_percent || 0)}%</div>
                    <div className="statistics-insight-meta">Live fill percentage from the ultrasonic sensor</div>
                    <img src="/icon/sectionStatisticsPage/capacity.svg" alt="" aria-hidden="true" />
                  </article>

                  <article className="statistics-insight-card">
                    <div className="statistics-insight-label">Security Log</div>
                    <div className="statistics-insight-value">{insights?.security_status || 'Secure'}</div>
                    <div className="statistics-insight-meta">Current vault state: {insights?.lock_status || 'Locked'}</div>
                    <img src="/icon/sectionStatisticsPage/security.svg" alt="" aria-hidden="true" />
                  </article>
                </div>
              </section>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
