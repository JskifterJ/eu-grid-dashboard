const RankingState = {
  preset: "balanced",
  workload: "training",
  region: "western",
  activeWeights: null,  // populated after each fetch
};

const DIMS = [
  { key: "carbon_score",   label: "Carbon" },
  { key: "cost_score",     label: "Cost" },
  { key: "renewable_score",label: "Renewable" },
  { key: "stability_score",label: "Stability" },
];

function _rankTooltipHtml(c) {
  const w = RankingState.activeWeights || {};
  const wKey = {
    "carbon_score": "carbon", "cost_score": "cost",
    "renewable_score": "renewable", "stability_score": "stability"
  };
  const rows = DIMS.map(d => {
    const val = c[d.key] ?? 0;
    const weight = w[wKey[d.key]] ?? 0;
    return `<div class="tt-dim">
      <span class="label">${d.label} · ${weight}%</span>
      <span class="bar-wrap"><span class="bar" style="width:${Math.max(0, Math.min(100, val))}%"></span></span>
      <span class="val">${Math.round(val)}</span>
    </div>`;
  }).join('');
  return `
    <div class="tt-rank-name">${c.name}</div>
    <div class="tt-rank-css">CSS ${Math.round(c.css)}</div>
    ${rows}
    <div class="tt-weight-note">Each bar is min-max normalized against all countries. The weighted sum = CSS.</div>
  `;
}

async function renderRanking() {
  const list = document.getElementById("ranking-list");
  try {
    const params = new URLSearchParams({ workload: RankingState.workload });
    if (RankingState.workload === "inference") params.set("region", RankingState.region);
    if (RankingState.preset !== "balanced") params.set("weights", RankingState.preset);
    const data = await fetchJson(`/api/ranking?${params}`);
    RankingState.activeWeights = data.weights || null;
    list.innerHTML = "";
    data.countries.forEach((c, i) => {
      const card = document.createElement("div");
      card.className = "rank-card" + (i === 0 ? " top" : "");
      card.dataset.country = c.country;
      card.innerHTML = `<div class="num">${Math.round(c.css)}</div><div class="name">${c.name}</div>`;
      card.addEventListener("click", () => {
        const sel = document.getElementById("country-select");
        if (sel) { sel.value = c.country; sel.dispatchEvent(new Event("change")); }
      });
      card.addEventListener("mouseenter", (event) => window.showTooltip && window.showTooltip(_rankTooltipHtml(c), event));
      card.addEventListener("mousemove",  (event) => window.moveTooltip && window.moveTooltip(event));
      card.addEventListener("mouseleave", () => window.hideTooltip && window.hideTooltip());
      list.appendChild(card);
    });
  } catch (e) {
    list.textContent = "Failed to load ranking.";
    console.error(e);
  }
}

function wireRankingControls() {
  document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      RankingState.preset = btn.dataset.preset;
      renderRanking();
    });
  });
  document.querySelectorAll(".workload-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".workload-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      RankingState.workload = btn.dataset.workload;
      const regionSel = document.getElementById("region-select");
      if (regionSel) regionSel.style.display = btn.dataset.workload === "inference" ? "" : "none";
      renderRanking();
    });
  });
  const regionSel = document.getElementById("region-select");
  if (regionSel) regionSel.addEventListener("change", () => {
    RankingState.region = regionSel.value;
    renderRanking();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  wireRankingControls();
  renderRanking();
});
