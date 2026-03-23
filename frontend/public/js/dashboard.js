// Dashboard page initialization and logic
export function renderDashboard() {
  return `
    <div class="page active" id="dashboard-page">
      <!-- Hero Card -->
      <div class="hero-card">
        <div class="hero-blob-1"></div>
        <div class="hero-blob-2"></div>
        
        <div class="hero-container">
          <div class="hero-left">
            <span class="hero-label">Total Balance</span>
            <div class="hero-amount" id="total-amount">91฿</div>
            <div class="hero-meta">
              <span class="meta-badge">
                <span class="meta-text" id="total-coins">27 coins</span>
              </span>
            </div>
          </div>

          <div class="hero-ring">
            <svg class="ring-svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="6"/>
              <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(20,184,166,0.8)" stroke-width="6" stroke-dasharray="125.6 251.2" stroke-linecap="round"/>
            </svg>
            <span class="ring-label">50%</span>
          </div>
        </div>
      </div>

      <!-- Coins Grid -->
      <div class="coins-container">
        <h2 class="coins-title">Coins in Vault</h2>
        <div class="coins-grid">
          <div class="coin-card">
            <div class="coin-card-header">
              <div class="coin-icon-bg">🪙</div>
              <span class="coin-value">10฿</span>
            </div>
            <div class="coin-content">
              <div class="coin-amount">5</div>
              <span class="coin-count-text">50฿ total</span>
            </div>
          </div>

          <div class="coin-card">
            <div class="coin-card-header">
              <div class="coin-icon-bg">🪙</div>
              <span class="coin-value">5฿</span>
            </div>
            <div class="coin-content">
              <div class="coin-amount">3</div>
              <span class="coin-count-text">15฿ total</span>
            </div>
          </div>

          <div class="coin-card">
            <div class="coin-card-header">
              <div class="coin-icon-bg">🪙</div>
              <span class="coin-value">2฿</span>
            </div>
            <div class="coin-content">
              <div class="coin-amount">7</div>
              <span class="coin-count-text">14฿ total</span>
            </div>
          </div>

          <div class="coin-card">
            <div class="coin-card-header">
              <div class="coin-icon-bg">🪙</div>
              <span class="coin-value">1฿</span>
            </div>
            <div class="coin-content">
              <div class="coin-amount">12</div>
              <span class="coin-count-text">12฿ total</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Status Section -->
      <div class="status-container">
        <div class="status-card-left">
          <div class="status-header">
            <div class="status-icon"></div>
            <h3 class="status-title">Vault Capacity</h3>
          </div>
          <div style="margin-top: 32px; display: flex; flex-direction: column; gap: 16px;">
            <div style="background: rgba(15, 118, 110, 0.2); height: 8px; border-radius: 9999px; overflow: hidden;">
              <div style="background: #0F766E; height: 100%; width: 45%;"></div>
            </div>
            <div style="font-size: 16px; font-weight: 700; color: #005C55;">91 / 200 coins</div>
          </div>
        </div>

        <div class="status-card-right">
          <div class="status-header">
            <div class="status-icon"></div>
            <h3 class="status-title">Vault Security</h3>
          </div>
          <div style="margin-top: 64px; text-align: center;">
            <div style="font-size: 48px; margin-bottom: 16px;">🔒</div>
            <div style="font-size: 14px; font-weight: 700; color: #005C55; margin-bottom: 16px;">Secured</div>
            <button class="settings-btn" style="width: 100%; margin-top: 0;">Unlock Vault</button>
          </div>
        </div>
      </div>
    </div>
  `;
}
