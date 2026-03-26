import React from 'react';
import './Sidebar.css';

const Sidebar = ({ active }) => {
  const logo = '/logo/logo.svg';
  const dashboardIcon = '/icon/gen/sectionTabMenu/IconDashboad.svg';
  const statisticsIcon = '/icon/gen/sectionTabMenu/IconStatistics.svg';
  const settingsIcon = '/icon/gen/sectionTabMenu/IconSettings.svg';
  const items = [
    { id: 'dashboard', label: 'Dashboard', icon: dashboardIcon },
    { id: 'statistics', label: 'Statistics', icon: statisticsIcon },
    { id: 'settings', label: 'Settings', icon: settingsIcon },
  ];

  return (
    <aside className="sidebar-root">
      <div className="sidebar-logo">
        <img src={logo} alt="logo" />
      </div>
      <nav className="sidebar-menu">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`sidebar-link${active === item.id ? ' active' : ''}`}
            aria-current={active === item.id ? 'page' : undefined}
          >
            <img src={item.icon} alt={item.label} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
