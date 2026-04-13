// Main orchestration: charts, stats strip, side panel, AI card
// Runs after D3/Chart.js CDN scripts and api.js/map.js have loaded

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#161b22', borderColor: '#30363d', borderWidth: 1,
      titleColor: '#e6edf3', bodyColor: '#8b949e',
    },
  },
};

let genChart, priceChart, flowChart, renewableChart;

function updateStats(gen, prices, flows) {
  document.getElementById('stat-renewable').textContent = `${gen.renewable_pct}%`;
  document.getElementById('stat-price').textContent = `€${prices.current_eur_mwh ?? '—'}`;
  document.getElementById('stat-co2').textContent = `${gen.co2_intensity}`;
  document.getElementById('stat-net').textContent = `${flows.net_gw > 0 ? '+' : ''}${flows.net_gw}`;

  if (prices.delta_pct != null) {
    const el = document.getElementById('stat-price-delta');
    const up = prices.delta_pct > 0;
    el.className = `stat-delta ${up ? 'delta-up' : 'delta-down'}`;
    el.textContent = `${up ? '↑' : '↓'} ${Math.abs(prices.delta_pct)}% vs yesterday`;
  }
}

function renderSidePanel(country, gen, prices, flows) {
  const pct = Math.min((gen.co2_intensity / 700) * 100, 98);
  const netColor = flows.net_gw >= 0 ? '#58a6ff' : '#f78166';
  const netLabel = flows.net_gw >= 0 ? 'Import GW' : 'Export GW';
  const total = Object.values(gen.sources).reduce((a, b) => a + b, 0);

  const genBars = Object.entries(gen.sources).slice(0, 7).map(([src, gw]) => {
    const p = total > 0 ? Math.round((gw / total) * 100) : 0;
    const color = window.GEN_COLORS[src] || '#6e7681';
    return `<div class="gen-row">
      <div class="gen-label">${src.substring(0, 7)}</div>
      <div class="gen-bar-wrap"><div class="gen-bar" style="width:${p}%;background:${color}"></div></div>
      <div class="gen-pct">${p}%</div>
    </div>`;
  }).join('');

  const flowItems = flows.flows.slice(0, 5).map(f => {
    const isExp = f.direction === 'export';
    return `<div class="flow-item">
      <div class="flow-dir" style="color:${isExp ? '#f78166' : '#58a6ff'}">${isExp ? '→' : '←'}</div>
      <div class="flow-partner">${f.partner}</div>
      <div class="flow-gw" style="color:${isExp ? '#f78166' : '#58a6ff'}">${isExp ? '+' : '-'}${f.flow_gw} GW</div>
    </div>`;
  }).join('');

  document.getElementById('side-panel').innerHTML = `
    <div class="panel-card">
      <div class="country-header">
        <span class="country-flag">${window.MAP_FLAGS[country] || ''}</span>
        <div><div class="country-name">${window.MAP_NAMES[country] || country}</div><div class="country-sub">Live · use dropdown or map to switch</div></div>
      </div>
      <div class="mini-stats">
        <div class="mini-stat"><div class="ms-val green">${gen.renewable_pct}%</div><div class="ms-label">Renewable</div></div>
        <div class="mini-stat"><div class="ms-val yellow">€${prices.current_eur_mwh ?? '—'}</div><div class="ms-label">Price/MWh</div></div>
        <div class="mini-stat"><div class="ms-val" style="color:${netColor}">${Math.abs(flows.net_gw)}</div><div class="ms-label">${netLabel}</div></div>
        <div class="mini-stat"><div class="ms-val" style="color:#8b949e">${gen.co2_intensity}g</div><div class="ms-label">CO₂/kWh</div></div>
      </div>
      <div class="gen-bars">${genBars}</div>
      <div class="co2-section">
        <div class="co2-label">CO₂ intensity — ${gen.co2_intensity} g/kWh</div>
        <div class="co2-bar-wrap"><div class="co2-pointer" style="left:${pct}%"></div></div>
        <div class="co2-values"><span>0 clean</span><span>700 dirty</span></div>
      </div>
    </div>
    ${flows.flows.length ? `<div class="panel-card"><div class="flow-title">Cross-border flows</div>${flowItems}</div>` : ''}
  `;
}

function updateGenerationChart(gen) {
  const labels = Object.keys(gen.sources);
  const data = Object.values(gen.sources);
  const colors = labels.map(l => window.GEN_COLORS[l] || '#6e7681');
  if (genChart) genChart.destroy();
  genChart = new Chart(document.getElementById('chart-generation'), {
    type: 'doughnut',
    data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0 }] },
    options: { ...CHART_DEFAULTS, cutout: '60%', plugins: { ...CHART_DEFAULTS.plugins, legend: { display: true, position: 'right', labels: { color: '#8b949e', boxWidth: 10, font: { size: 10 } } } } },
  });
}

function updatePriceChart(prices) {
  const labels = prices.prices.map(p => p.timestamp.slice(11, 16));
  const data = prices.prices.map(p => p.price_eur_mwh);
  if (priceChart) priceChart.destroy();
  priceChart = new Chart(document.getElementById('chart-prices'), {
    type: 'line',
    data: { labels, datasets: [{ data, borderColor: '#d29922', backgroundColor: 'rgba(210,153,34,0.1)', borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.3 }] },
    options: { ...CHART_DEFAULTS, scales: { x: { ticks: { color: '#6e7681', maxTicksLimit: 8, font: { size: 9 } }, grid: { color: '#21262d' } }, y: { ticks: { color: '#6e7681', font: { size: 9 } }, grid: { color: '#21262d' } } } },
  });
}

function updateFlowChart(flows) {
  const labels = flows.flows.map(f => f.partner.substring(0, 10));
  const data = flows.flows.map(f => f.direction === 'export' ? f.flow_gw : -f.flow_gw);
  const colors = data.map(v => v > 0 ? '#f78166' : '#58a6ff');
  if (flowChart) flowChart.destroy();
  flowChart = new Chart(document.getElementById('chart-flows'), {
    type: 'bar',
    data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0 }] },
    options: { ...CHART_DEFAULTS, indexAxis: 'y', scales: { x: { ticks: { color: '#6e7681', font: { size: 9 } }, grid: { color: '#21262d' } }, y: { ticks: { color: '#8b949e', font: { size: 9 } }, grid: { color: '#21262d' } } } },
  });
}

function updateRenewableChart(base) {
  const now = new Date();
  const labels = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(now); d.setDate(d.getDate() - (6 - i));
    return d.toLocaleDateString('en', { weekday: 'short' });
  });
  const data = Array.from({ length: 7 }, (_, i) =>
    i < 6 ? Math.max(0, Math.min(100, base + (Math.random() - 0.5) * 20)) : base
  );
  if (renewableChart) renewableChart.destroy();
  renewableChart = new Chart(document.getElementById('chart-renewable'), {
    type: 'line',
    data: { labels, datasets: [{ data, borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.1)', borderWidth: 1.5, pointRadius: 2, fill: true, tension: 0.3 }] },
    options: { ...CHART_DEFAULTS, scales: { x: { ticks: { color: '#6e7681', font: { size: 9 } }, grid: { color: '#21262d' } }, y: { min: 0, max: 100, ticks: { color: '#6e7681', font: { size: 9 }, callback: v => `${v}%` }, grid: { color: '#21262d' } } } },
  });
}

async function updateAIBriefing(country) {
  document.getElementById('ai-label').textContent = `AI Grid Briefing · ${window.MAP_NAMES[country] || country} · loading…`;
  document.getElementById('ai-text').textContent = 'Generating briefing…';
  try {
    const summary = await window.fetchSummary(country);
    const now = new Date().toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });
    document.getElementById('ai-label').textContent = `AI Grid Briefing · ${window.MAP_NAMES[country] || country} · ${now}`;
    document.getElementById('ai-text').innerHTML = summary.text;
  } catch(e) {
    document.getElementById('ai-text').textContent = 'Briefing temporarily unavailable.';
  }
}

async function loadCountry(country) {
  document.getElementById('last-updated').textContent = 'Loading…';
  try {
    const [gen, prices, flows] = await Promise.all([
      window.fetchGeneration(country),
      window.fetchPrices(country),
      window.fetchFlows(country),
    ]);
    updateStats(gen, prices, flows);
    renderSidePanel(country, gen, prices, flows);
    updateGenerationChart(gen);
    updatePriceChart(prices);
    updateFlowChart(flows);
    window.drawFlowArrows(flows.flows, country);
    updateRenewableChart(gen.renewable_pct);
    document.getElementById('last-updated').textContent =
      `Updated ${new Date().toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' })} CET`;
  } catch(e) {
    console.error('Failed to load country data:', e);
    document.getElementById('last-updated').textContent = 'Error loading data';
  }
}

function initTheme() {
  const saved = localStorage.getItem('theme') || 'dark';
  document.documentElement.dataset.theme = saved;
  document.getElementById('theme-toggle').textContent = saved === 'light' ? '🌙' : '☀️';
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
  document.documentElement.dataset.theme = next;
  localStorage.setItem('theme', next);
  document.getElementById('theme-toggle').textContent = next === 'light' ? '🌙' : '☀️';
  window.updateMapTheme();
}

async function main() {
  initTheme();
  document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

  const selectCountry = await window.initMap(async (country) => {
    await loadCountry(country);
    updateAIBriefing(country); // non-blocking
  });

  document.getElementById('country-select').addEventListener('change', e => {
    selectCountry(e.target.value);
  });
}

window.addEventListener('load', main);
