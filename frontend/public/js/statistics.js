// Statistics page initialization and logic
export function renderStatistics() {
  return `
    <div class="page" id="statistics-page">
      <div class="chart-section">
        <h2 class="chart-title">Coin Distribution</h2>
        <canvas id="distributionChart"></canvas>
      </div>

      <div class="chart-section">
        <h2 class="chart-title">Deposits Over Time</h2>
        <canvas id="depositsChart"></canvas>
      </div>
    </div>
  `;
}

export function initCharts() {
  const ctx1 = document.getElementById('distributionChart');
  if (ctx1 && !ctx1.chartInstance) {
    ctx1.chartInstance = new Chart(ctx1, {
      type: 'doughnut',
      data: {
        labels: ['10฿', '5฿', '2฿', '1฿'],
        datasets: [{ 
          data: [5, 3, 7, 12], 
          backgroundColor: ['#005C55', '#0F766E', '#14B8A6', '#5EEAD4'] 
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true
      }
    });
  }

  const ctx2 = document.getElementById('depositsChart');
  if (ctx2 && !ctx2.chartInstance) {
    ctx2.chartInstance = new Chart(ctx2, {
      type: 'line',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [{
          label: 'Daily Deposits (฿)',
          data: [10, 15, 12, 20, 18, 25, 22],
          borderColor: '#0F766E',
          backgroundColor: 'rgba(15, 118, 110, 0.1)',
          tension: 0.4,
          fill: true,
          pointRadius: 5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true
      }
    });
  }
}
