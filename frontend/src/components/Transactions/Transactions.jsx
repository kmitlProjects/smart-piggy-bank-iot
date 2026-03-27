import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Sidebar from '../Dashboard/Sidebar';
import Topbar from '../Dashboard/Topbar';
import { COIN_COLORS } from '../../utils/coinColors';
import './Transactions.css';

const COIN_FILTERS = ['all', '10', '5', '2', '1'];
const ROWS_PER_PAGE = 10;

function readTransactionsViewFromLocation() {
  if (typeof window === 'undefined') {
    return {
      search: '',
      coinFilter: 'all',
      page: 1,
    };
  }

  const params = new URLSearchParams(window.location.search);
  const coinFilter = params.get('coin') || 'all';
  const parsedPage = Number.parseInt(params.get('page') || '1', 10);

  return {
    search: params.get('q') || '',
    coinFilter: COIN_FILTERS.includes(coinFilter) ? coinFilter : 'all',
    page: Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : 1,
  };
}

function writeTransactionsViewToLocation({ search, coinFilter, page }) {
  if (typeof window === 'undefined') {
    return;
  }

  const params = new URLSearchParams(window.location.search);
  const trimmedSearch = search.trim();

  if (trimmedSearch) {
    params.set('q', trimmedSearch);
  } else {
    params.delete('q');
  }

  if (coinFilter && coinFilter !== 'all') {
    params.set('coin', coinFilter);
  } else {
    params.delete('coin');
  }

  if (page > 1) {
    params.set('page', String(page));
  } else {
    params.delete('page');
  }

  const query = params.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}`;
  const currentUrl = `${window.location.pathname}${window.location.search}`;

  if (nextUrl !== currentUrl) {
    window.history.replaceState(window.history.state, '', nextUrl);
  }
}

function formatNumber(value) {
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 0,
  }).format(Number(value) || 0);
}

function formatCurrency(value) {
  return new Intl.NumberFormat('th-TH', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value) || 0);
}

function getEventBadgeLabel(transaction) {
  if (transaction.coin_value) {
    return String(transaction.coin_value);
  }

  if (transaction.action_code === 'rfid_unlock') {
    return 'RFID';
  }

  if (transaction.action_code === 'web_unlock') {
    return 'WEB';
  }

  return 'SYS';
}

function paginate(totalItems, currentPage, pageSize) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const safePage = Math.min(Math.max(currentPage, 1), totalPages);
  const start = (safePage - 1) * pageSize;
  const end = start + pageSize;
  return { totalPages, safePage, start, end };
}

export default function Transactions({ onNavigate }) {
  const initialViewRef = useRef(readTransactionsViewFromLocation());
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState(initialViewRef.current.search);
  const [coinFilter, setCoinFilter] = useState(initialViewRef.current.coinFilter);
  const [page, setPage] = useState(initialViewRef.current.page);

  const loadTransactions = useCallback(async () => {
    try {
      const response = await fetch('/api/transactions');
      if (!response.ok) {
        throw new Error(`Failed to fetch transactions (${response.status})`);
      }

      const nextPayload = await response.json();
      setPayload(nextPayload);
      setError('');
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to fetch transactions');
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
      await loadTransactions();
    };

    run();
    const intervalId = window.setInterval(run, 15000);

    return () => {
      mounted = false;
      window.clearInterval(intervalId);
    };
  }, [loadTransactions]);

  useEffect(() => {
    const syncFromLocation = () => {
      const nextView = readTransactionsViewFromLocation();
      setSearch(nextView.search);
      setCoinFilter(nextView.coinFilter);
      setPage(nextView.page);
    };

    window.addEventListener('popstate', syncFromLocation);
    return () => window.removeEventListener('popstate', syncFromLocation);
  }, []);

  const hero = payload?.hero ?? {};
  const device = payload?.device ?? {};
  const transactions = payload?.transactions ?? [];
  const meta = payload?.meta ?? {};
  const locked = device.is_locked === undefined ? true : Boolean(device.is_locked);

  const filteredTransactions = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    return transactions.filter((transaction) => {
      const matchesCoin = coinFilter === 'all' || String(transaction.coin_value) === coinFilter;
      if (!matchesCoin) {
        return false;
      }

      if (!keyword) {
        return true;
      }

      const haystack = [
        transaction.coin_label,
        transaction.date_label,
        transaction.time_label,
        transaction.status,
        transaction.action,
        transaction.detail,
        transaction.reason_label,
        transaction.count,
        transaction.value,
      ]
        .join(' ')
        .toLowerCase();

      return haystack.includes(keyword);
    });
  }, [transactions, search, coinFilter]);

  const pagination = paginate(filteredTransactions.length, page, ROWS_PER_PAGE);
  const pageRows = filteredTransactions.slice(pagination.start, pagination.end);

  useEffect(() => {
    if (page !== pagination.safePage) {
      setPage(pagination.safePage);
    }
  }, [page, pagination.safePage]);

  useEffect(() => {
    writeTransactionsViewToLocation({
      search,
      coinFilter,
      page,
    });
  }, [search, coinFilter, page]);

  const handleExport = () => {
    const rows = filteredTransactions.map((transaction) => ({
      date: transaction.date_label,
      time: transaction.time_label,
      coin_type: transaction.coin_label,
      coin_value: transaction.coin_value,
      count: transaction.count,
      total_value: transaction.value,
      status: transaction.status,
      action: transaction.action,
      detail: transaction.detail,
      reason: transaction.reason_label,
    }));

    const header = Object.keys(rows[0] || {
      date: '',
      time: '',
      coin_type: '',
      coin_value: '',
      count: '',
      total_value: '',
      status: '',
      action: '',
      detail: '',
      reason: '',
    });
    const csv = [
      header.join(','),
      ...rows.map((row) => header.map((key) => JSON.stringify(row[key] ?? '')).join(',')),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'transactions.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="transactions-shell">
      <Sidebar active="transactions" onNavigate={onNavigate} />
      <main className="transactions-main">
        <Topbar wifi={Boolean(device.wifi_connected)} locked={locked} lastSeenAt={device.last_seen_at} />
        <div className="transactions-content">
          {error && (
            <div className="transactions-alert" role="alert">
              {error}
            </div>
          )}

          {!payload && loading ? (
            <div className="transactions-placeholder">Loading transaction history...</div>
          ) : (
            <>
              <section className="transactions-hero-grid">
                <article className="transactions-balance-card">
                  <div className="transactions-balance-copy">
                    <span className="transactions-card-label">Total Secured Savings</span>
                    <strong>฿ {formatCurrency(hero.total_secured_savings || 0)}</strong>
                  </div>
                  <div className="transactions-balance-meta">
                    <div>
                      <span>This Month</span>
                      <strong>+฿ {formatCurrency(hero.this_month_value || 0)}</strong>
                    </div>
                    <div>
                      <span>Verified Deposits</span>
                      <strong>{formatNumber(hero.verified_deposits || 0)}</strong>
                    </div>
                  </div>
                  <img
                    src="/icon/sectionTransactionsPage/pigIcon.svg"
                    alt=""
                    aria-hidden="true"
                    className="transactions-balance-art"
                  />
                </article>

                <div className="transactions-side-grid">
                  <article className="transactions-side-card">
                    <div className="transactions-side-icon">
                      <img src="/icon/sectionTransactionsPage/coins.svg" alt="" aria-hidden="true" />
                    </div>
                    <div>
                      <span className="transactions-card-label">Coins Counted</span>
                      <strong>{formatNumber(hero.coins_counted || 0)}</strong>
                    </div>
                  </article>

                  <article className="transactions-side-card">
                    <div className="transactions-side-icon is-tertiary">
                      <img src="/icon/sectionTransactionsPage/time.svg" alt="" aria-hidden="true" />
                    </div>
                    <div>
                      <span className="transactions-card-label">Peak Deposit Time</span>
                      <strong>{hero.peak_deposit_time || '--:--'}</strong>
                    </div>
                  </article>
                </div>
              </section>

              <section className="transactions-table-card">
                <div className="transactions-table-header">
                  <div>
                    <h1>Transaction Log</h1>
                    <p>Derived from positive deltas between cumulative coin snapshots.</p>
                  </div>
                  <div className="transactions-toolbar">
                    <label className="transactions-search">
                      <input
                        type="search"
                        value={search}
                        onChange={(event) => {
                          setSearch(event.target.value);
                          setPage(1);
                        }}
                        placeholder="Search transactions..."
                      />
                    </label>
                    <button type="button" className="transactions-toolbar-btn" onClick={handleExport}>
                      <img src="/icon/sectionTransactionsPage/export.svg" alt="" aria-hidden="true" />
                      <span>Export</span>
                    </button>
                  </div>
                </div>

                <div className="transactions-filter-row">
                  {COIN_FILTERS.map((filterValue) => (
                    <button
                      key={filterValue}
                      type="button"
                      className={`transactions-filter-btn${coinFilter === filterValue ? ' active' : ''}`}
                      onClick={() => {
                        setCoinFilter(filterValue);
                        setPage(1);
                      }}
                    >
                      {filterValue === 'all' ? 'All Coins' : `฿${filterValue}`}
                    </button>
                  ))}
                </div>

                <div className="transactions-table-wrap">
                  <table className="transactions-table">
                    <thead>
                      <tr>
                        <th>Date &amp; Time</th>
                        <th>Coin Type</th>
                        <th>Value</th>
                        <th>Status</th>
                        <th className="align-right">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pageRows.length === 0 && (
                        <tr>
                          <td colSpan="5" className="transactions-empty">
                            {meta.has_transactions
                              ? 'No transactions match the current filters.'
                              : 'No transaction rows have been derived from the timeseries yet.'}
                          </td>
                        </tr>
                      )}

                      {pageRows.map((transaction) => (
                        <tr key={transaction.id}>
                          <td>
                            <div className="transactions-date">
                              <strong>{transaction.date_label}</strong>
                              <span>{transaction.time_label}</span>
                            </div>
                          </td>
                          <td>
                            <div className="transactions-coin-cell">
                              <div
                                className={`transactions-coin-dot${transaction.coin_value ? '' : ' is-event'}`}
                                style={transaction.coin_value ? { backgroundColor: COIN_COLORS[transaction.coin_value] } : undefined}
                              >
                                {getEventBadgeLabel(transaction)}
                              </div>
                              <div>
                                <strong>{transaction.coin_label}</strong>
                                <span>
                                  {transaction.count
                                    ? `Count: ${formatNumber(transaction.count)} coin${transaction.count > 1 ? 's' : ''}`
                                    : (transaction.detail || 'No extra detail')}
                                </span>
                              </div>
                            </div>
                          </td>
                          <td>
                            {transaction.value === null || transaction.value === undefined ? (
                              <strong className="transactions-value is-muted">--</strong>
                            ) : (
                              <strong className="transactions-value">฿{formatCurrency(transaction.value)}</strong>
                            )}
                          </td>
                          <td>
                            <span className={`transactions-status-pill is-${transaction.status_code || 'neutral'}`}>
                              <img src="/icon/sectionTransactionsPage/status.svg" alt="" aria-hidden="true" />
                              {transaction.status}
                            </span>
                          </td>
                          <td className="align-right">
                            <div className="transactions-action-cell">
                              <span className={`transactions-action-pill is-${transaction.action_code || 'system'}`}>
                                {transaction.action}
                              </span>
                              {transaction.reason_label && (
                                <span className="transactions-action-detail">{transaction.reason_label}</span>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="transactions-table-footer">
                  <span>
                    Showing {pageRows.length} of {filteredTransactions.length} entries
                  </span>
                  <div className="transactions-pagination">
                    <button
                      type="button"
                      disabled={pagination.safePage <= 1}
                      onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                    >
                      ‹
                    </button>
                    {Array.from({ length: pagination.totalPages }, (_, index) => index + 1)
                      .slice(Math.max(0, pagination.safePage - 2), Math.max(3, pagination.safePage + 1))
                      .map((pageNumber) => (
                        <button
                          key={pageNumber}
                          type="button"
                          className={pageNumber === pagination.safePage ? 'active' : ''}
                          onClick={() => setPage(pageNumber)}
                        >
                          {pageNumber}
                        </button>
                      ))}
                    <button
                      type="button"
                      disabled={pagination.safePage >= pagination.totalPages}
                      onClick={() => setPage((currentPage) => Math.min(pagination.totalPages, currentPage + 1))}
                    >
                      ›
                    </button>
                  </div>
                </div>
              </section>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
