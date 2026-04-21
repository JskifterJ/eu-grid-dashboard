let _forecastChart = null;

async function renderForecastChart(country) {
  const canvas = document.getElementById("forecast-chart");
  const nameEl = document.getElementById("forecast-country-name");
  if (!canvas) return;
  try {
    const data = await fetchJson(`/api/forecast?country=${country}`);
    if (!data.points || data.points.length === 0) return;

    const countryNames = window.MAP_NAMES || {};
    if (nameEl) nameEl.textContent = countryNames[country] || country;

    const labels = data.points.map(p => {
      const d = new Date(p.timestamp);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    });
    const co2 = data.points.map(p => p.co2_g_per_kwh);
    const price = data.points.map(p => p.price_eur_mwh);

    const isLight = document.documentElement.dataset.theme === "light";
    const textCol = isLight ? "#24292f" : "#f3eee3";
    const gridCol = isLight ? "#e8e0d0" : "#3a362f";

    if (_forecastChart) _forecastChart.destroy();
    _forecastChart = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "CO₂ (g/kWh)",
            data: co2,
            yAxisID: "yCO2",
            borderColor: "#c69a56",
            backgroundColor: "rgba(198,154,86,0.12)",
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.3,
            fill: true,
          },
          {
            label: "Price (€/MWh)",
            data: price,
            yAxisID: "yPrice",
            borderColor: "#8db6d1",
            backgroundColor: "rgba(141,182,209,0.06)",
            borderWidth: 2,
            borderDash: [4, 3],
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.3,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: textCol, boxWidth: 12, font: { size: 11 } },
          },
          tooltip: {
            callbacks: {
              title: (items) => items[0].label + " (forecast)",
              label: (ctx) => {
                if (ctx.dataset.yAxisID === "yCO2") return `CO₂  ${Math.round(ctx.parsed.y)} g/kWh`;
                return `Price €${Math.round(ctx.parsed.y)}/MWh`;
              },
            },
          },
        },
        scales: {
          x: {
            ticks: { color: textCol, maxTicksLimit: 8, font: { size: 10 } },
            grid: { color: gridCol, drawBorder: false },
          },
          yCO2: {
            position: "left",
            title: { display: true, text: "g CO₂ / kWh", color: textCol, font: { size: 10 } },
            ticks: { color: textCol, font: { size: 10 } },
            grid: { color: gridCol },
            beginAtZero: true,
          },
          yPrice: {
            position: "right",
            title: { display: true, text: "€ / MWh", color: textCol, font: { size: 10 } },
            ticks: { color: textCol, font: { size: 10 } },
            grid: { drawOnChartArea: false },
          },
        },
      },
    });
  } catch (e) {
    console.error("forecast chart failed:", e);
  }
}

window.renderForecastChart = renderForecastChart;

async function renderForecastEval(country) {
  try {
    const [co2Data, priceData] = await Promise.all([
      fetchJson(`/api/eval?country=${country}&metric=co2`),
      fetchJson(`/api/eval?country=${country}&metric=price`),
    ]);
    _renderEvalRow("eval-co2", co2Data, 30);      // 30 = chart upper bound for CO₂ MAPE
    _renderEvalRow("eval-price", priceData, 30);
  } catch (e) {
    console.error("eval render failed:", e);
  }
}

function _renderEvalRow(hostId, data, maxPct) {
  const host = document.getElementById(hostId);
  if (!host) return;
  const rows = [
    { label: "market", pct: data.market_mape_pct, cls: "market" },
    { label: "naive",  pct: data.naive_mape_pct,  cls: "naive"  },
  ];
  host.innerHTML = rows.map(r => `
    <div class="eval-bar-row ${r.cls}">
      <span class="bar-label">${r.label}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${Math.min(100, r.pct / maxPct * 100)}%"></span></span>
      <span class="bar-val">${r.pct.toFixed(1)}%</span>
    </div>
  `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  const sel = document.getElementById("country-select");
  const initial = (sel && sel.value) || "DK";
  renderForecastChart(initial);
  renderForecastEval(initial);
  if (sel) sel.addEventListener("change", () => {
    renderForecastChart(sel.value);
    renderForecastEval(sel.value);
  });
});
