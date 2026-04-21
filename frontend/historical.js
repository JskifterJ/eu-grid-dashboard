const HIST_CARDS = [
  {
    label: "Renewable share (EU-27 power)",
    then: "2015 · 29%",
    now: "48%",
    delta: "+19 pp",
    pos: true,
    bar: 48,
  },
  {
    label: "Wind + solar share",
    then: "2015 · ~10%",
    now: "28%",
    delta: "+18 pp",
    pos: true,
    bar: 28,
  },
  {
    label: "Coal share",
    then: "2015 · 25%",
    now: "12%",
    delta: "−52%",
    pos: false,
    bar: 12,
  },
  {
    label: "Avg CO₂ intensity",
    then: "2015 · 380 g/kWh",
    now: "240",
    nowUnit: " g/kWh",
    delta: "−37%",
    pos: false,
    bar: 63,  // inverted: 240 / 380 × 100
  },
];

function renderHistorical() {
  const host = document.getElementById("hist-cards");
  if (!host) return;
  host.innerHTML = HIST_CARDS.map(c => `
    <div class="hist-card">
      <div class="hist-label">${c.label}</div>
      <div class="hist-then">${c.then} <span class="hist-arrow">→</span> today</div>
      <div class="hist-now">${c.now}${c.nowUnit ? `<span style="font-size:18px;color:var(--muted);"> ${c.nowUnit}</span>` : ""}</div>
      <div class="hist-delta ${c.pos ? 'positive' : 'negative'}">${c.delta}</div>
      <div class="hist-bar"><div class="hist-bar-fill" style="width:${c.bar}%"></div></div>
    </div>
  `).join("");
}

document.addEventListener("DOMContentLoaded", renderHistorical);
