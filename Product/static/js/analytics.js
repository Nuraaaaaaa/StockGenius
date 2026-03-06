let revenueChartInstance = null;
let categoryChartInstance = null;

function formatCurrency(value) {
  return `$${Number(value || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

async function loadStats() {
  const res = await fetch("/api/dashboard/stats");
  const data = await res.json();

  document.getElementById("totalRevenue").textContent = formatCurrency(
    data.total_sales,
  );
  document.getElementById("totalTransactions").textContent =
    data.total_records ?? 0;
  document.getElementById("avgOrderValue").textContent = formatCurrency(
    data.avg_order_value ?? 0,
  );
}

async function loadSalesTrend() {
  const res = await fetch("/api/dashboard/sales_trend");
  const data = await res.json();

  const labels = data.labels || [];
  const values = data.actual || [];

  document.getElementById("trendSubtitle").textContent = values.length
    ? `Monthly revenue trend • ${labels[0]} to ${labels[labels.length - 1]}`
    : "No revenue trend data available";

  const ctx = document.getElementById("revenueChart").getContext("2d");

  if (revenueChartInstance) {
    revenueChartInstance.destroy();
  }

  revenueChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Revenue",
          data: values,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.12)",
          tension: 0.4,
          fill: false,
          pointRadius: 0,
          pointHoverRadius: 4,
          borderWidth: 3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          grid: {
            color: "rgba(148, 163, 184, 0.15)",
          },
          ticks: {
            color: "#64748b",
            font: { size: 10 },
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: "rgba(148, 163, 184, 0.15)",
          },
          ticks: {
            color: "#64748b",
            font: { size: 10 },
            callback: function (value) {
              return value;
            },
          },
        },
      },
    },
  });
}

async function loadTopProducts() {
  const res = await fetch("/api/dashboard/top_products");
  const data = await res.json();

  const labels = data.labels || [];
  const values = data.values || [];
  const sales = data.sales || [];

  if (labels.length) {
    document.getElementById("topCategory").textContent = labels[0];
    document.getElementById("topCategoryMeta").textContent =
      `${values[0]} units • ${formatCurrency(sales[0])}`;
  }

  const ctx = document.getElementById("categoryChart").getContext("2d");

  if (categoryChartInstance) {
    categoryChartInstance.destroy();
  }

  categoryChartInstance = new Chart(ctx, {
    type: "pie",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: [
            "#2563eb",
            "#10b981",
            "#f59e0b",
            "#ef4444",
            "#8b5cf6",
            "#06b6d4",
            "#84cc16",
            "#f97316",
          ],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            boxWidth: 10,
            boxHeight: 10,
            color: "#475569",
            font: { size: 11 },
          },
        },
      },
    },
  });
}

async function initAnalytics() {
  try {
    await Promise.all([loadStats(), loadSalesTrend(), loadTopProducts()]);
  } catch (error) {
    console.error("Analytics load error:", error);
  }
}

document.addEventListener("DOMContentLoaded", initAnalytics);
