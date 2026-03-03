// dashboard.js — All data from ML-enriched dataset APIs

// ── Helpers ──────────────────────────────────────────────────────
const fmt$ = (n) =>
  '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

const severityBadge = (s) => {
  const map    = { error: 'bg-red-100 text-red-600', warning: 'bg-amber-100 text-amber-700', info: 'bg-blue-100 text-blue-700' };
  const labels = { error: '🔴 Anomaly', warning: '🟡 Warning', info: '🔵 Info' };
  return `<span class="px-2 py-0.5 rounded-full text-xs font-medium ${map[s] || 'bg-slate-100 text-slate-600'}">${labels[s] || s}</span>`;
};


// ── 1. KPI Stats — Low_Stock, Near_Expiry, Is_Anomaly, Sales ─────
async function loadStats() {
  try {
    const data = await fetch('/api/dashboard/stats').then(r => r.json());

    document.getElementById('statProducts').textContent   = data.total_products ?? '—';
    document.getElementById('statLowStock').textContent   = data.low_stock      ?? '—';
    document.getElementById('statNearExpiry').textContent = data.near_expiry    ?? '—';
    document.getElementById('statAnomalies').textContent  = data.anomaly_count  ?? '—';
    document.getElementById('statSales').textContent      = fmt$(data.total_sales ?? 0);

    // Bell badge = total urgent alerts
    const urgent = (data.low_stock ?? 0) + (data.near_expiry ?? 0) + (data.anomaly_count ?? 0);
    if (urgent > 0) {
      const badge = document.getElementById('alertBadge');
      badge.textContent = urgent > 99 ? '99+' : urgent;
      badge.classList.remove('hidden');
      badge.classList.add('flex');
    }
  } catch {
    ['statProducts', 'statLowStock', 'statNearExpiry', 'statAnomalies', 'statSales']
      .forEach(id => { document.getElementById(id).textContent = '—'; });
  }
}


// ── 2. ARIMA Sales Trend — actual monthly + forecast ─────────────
async function loadSalesTrend() {
  try {
    const data = await fetch('/api/dashboard/sales_trend').then(r => r.json());

    document.getElementById('lineChartSkeleton').classList.add('hidden');
    const canvas = document.getElementById('lineChart');
    canvas.classList.remove('hidden');

    // Merge actual + forecast labels for full x-axis
    const allLabels      = [...data.labels, ...data.forecast_labels.filter(l => !data.labels.includes(l))];
    const actualPadded   = allLabels.map(l => data.labels.includes(l) ? data.actual[data.labels.indexOf(l)] : null);
    const forecastPadded = allLabels.map(l => data.forecast_labels.includes(l) ? data.forecast[data.forecast_labels.indexOf(l)] : null);

    new Chart(canvas, {
      type: 'line',
      data: {
        labels: allLabels,
        datasets: [
          {
            label: 'Actual Sales',
            data: actualPadded,
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37,99,235,0.07)',
            borderWidth: 2.5,
            pointRadius: 4,
            pointBackgroundColor: '#fff',
            pointBorderColor: '#2563eb',
            pointBorderWidth: 2,
            tension: 0.4,
            fill: true,
            spanGaps: false,
          },
          {
            label: 'ARIMA Forecast',
            data: forecastPadded,
            borderColor: '#7c3aed',
            borderWidth: 2,
            borderDash: [6, 4],
            pointRadius: 4,
            pointBackgroundColor: '#7c3aed',
            tension: 0.3,
            fill: false,
            spanGaps: false,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => ' ' + fmt$(ctx.parsed.y) } },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 }, maxRotation: 35 } },
          y: {
            grid: { color: '#f1f5f9' },
            ticks: { color: '#94a3b8', font: { size: 10 }, callback: v => '$' + (v / 1000).toFixed(0) + 'k' },
          },
        },
      },
    });
  } catch {
    document.getElementById('lineChartSkeleton').innerHTML =
      '<p class="text-center text-slate-400 text-xs pt-24">No sales data available.</p>';
  }
}


// ── 3. Random Forest — Demand by Sub-Category ────────────────────
async function loadTopProducts() {
  try {
    const data = await fetch('/api/dashboard/top_products').then(r => r.json());

    document.getElementById('barChartSkeleton').classList.add('hidden');
    const canvas = document.getElementById('barChart');
    canvas.classList.remove('hidden');

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Total Quantity',
          data: data.values,
          backgroundColor: ['#2563eb','#3b82f6','#60a5fa','#93c5fd','#7c3aed','#a78bfa','#10b981','#34d399'],
          borderRadius: 6,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y.toLocaleString()} units` } },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 }, maxRotation: 35 } },
          y: { grid: { color: '#f1f5f9' }, ticks: { color: '#94a3b8', font: { size: 10 } } },
        },
      },
    });
  } catch {
    document.getElementById('barChartSkeleton').innerHTML =
      '<p class="text-center text-slate-400 text-xs pt-24">No product data available.</p>';
  }
}


// ── 4. Profit Margin by Sub-Category — from ML EDA ───────────────
async function loadMarginChart() {
  try {
    const data = await fetch('/api/dashboard/margin_by_category').then(r => r.json());

    document.getElementById('marginChartSkeleton').classList.add('hidden');
    const canvas = document.getElementById('marginChart');
    canvas.classList.remove('hidden');

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Profit Margin %',
          data: data.margins,
          backgroundColor: data.margins.map(m => m < 0 ? '#ef4444' : m < 10 ? '#f59e0b' : '#10b981'),
          borderRadius: 4,
          borderSkipped: false,
        }],
      },
      options: {
        indexAxis: 'y',   // horizontal — matches your Jupyter EDA chart
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.x.toFixed(2)}% margin` } },
        },
        scales: {
          x: {
            grid: { color: '#f1f5f9' },
            ticks: { color: '#94a3b8', font: { size: 10 }, callback: v => v + '%' },
          },
          y: { grid: { display: false }, ticks: { color: '#475569', font: { size: 10 } } },
        },
      },
    });
  } catch {
    document.getElementById('marginChartSkeleton').innerHTML =
      '<p class="text-center text-slate-400 text-xs pt-20">No margin data available.</p>';
  }
}


// ── 5. ML Alert Table — anomalies + low stock + near expiry ──────
async function loadAlerts() {
  try {
    const rows = await fetch('/api/dashboard/recent_alerts').then(r => r.json());

    document.getElementById('tableSkeleton').classList.add('hidden');

    if (!rows.length) {
      document.getElementById('alertEmpty').classList.remove('hidden');
      return;
    }

    document.getElementById('alertBody').innerHTML = rows.map(r => `
      <tr class="hover:bg-slate-50 transition">
        <td class="py-3 pr-4 font-medium text-slate-700 whitespace-nowrap">${r.alert_type}</td>
        <td class="py-3 pr-4 text-slate-700">${r.sub_category}</td>
        <td class="py-3 pr-4 text-slate-500 text-xs">${r.state}, ${r.region}</td>
        <td class="py-3 pr-4 font-medium">${fmt$(r.sales)}</td>
        <td class="py-3 pr-4 text-slate-600">${r.discount_pct}%</td>
        <td class="py-3 pr-4 font-medium ${r.profit < 0 ? 'text-red-500' : 'text-emerald-600'}">
          ${r.profit < 0 ? '' : '+'}${fmt$(r.profit)}
        </td>
        <td class="py-3 pr-4 text-slate-600">${r.stock_level} / ${r.reorder_point}</td>
        <td class="py-3">${severityBadge(r.severity)}</td>
      </tr>`).join('');

    document.getElementById('alertTable').classList.remove('hidden');
  } catch {
    document.getElementById('tableSkeleton').innerHTML =
      '<p class="text-slate-400 text-sm py-4 text-center">Could not load ML alerts.</p>';
  }
}


// ── Init — run all loaders in parallel ───────────────────────────
(async () => {
  document.getElementById('lastUpdated').textContent =
    'ML Dataset · Last updated: ' + new Date().toLocaleTimeString();

  await Promise.all([
    loadStats(),
    loadSalesTrend(),
    loadTopProducts(),
    loadMarginChart(),
    loadAlerts(),
  ]);
})();