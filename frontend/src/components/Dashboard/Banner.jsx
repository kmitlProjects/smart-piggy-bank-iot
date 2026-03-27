import React from 'react';
import './Banner.css';

const Banner = ({ onExplore }) => (
  <section className="dashboard-banner">
    <div className="dashboard-banner-bg">
      <img src="/image/imageDashboardPage/financialtexture.png" alt="Banner" />
      <div className="dashboard-banner-gradient"></div>
    </div>
    <div className="dashboard-banner-content">
      <div className="dashboard-banner-title">Smart Saving Insights</div>
      <div className="dashboard-banner-desc">Discover how your saving habits have improved over the last 30 days.</div>
      <button type="button" className="dashboard-banner-btn" onClick={onExplore}>
        EXPLORE ANALYTICS <img src="/icon/sectionDashboardPage/IconNext.svg" alt="Next" />
      </button>
    </div>
  </section>
);

export default Banner;
