const RankingState = {
  preset: "balanced",
  workload: "training",
  region: "western",
  activeWeights: null,
  expanded: false,
};

const DIMS = [
  { key: "carbon_score",    label: "Carbon" },
  { key: "cost_score",      label: "Cost" },
  { key: "renewable_score", label: "Renewable" },
  { key: "stability_score", label: "Stability" },
];

const REGION_LABEL = {
  central: "Central EU",
  western: "Western EU",
  northern: "Northern EU",
  southern: "Southern EU",
  iberian: "Iberian",
};

const WORKLOAD_EXPLAINER = `
  <div class="wp-row">
    <h4>Training</h4>
    <p>Long, batch GPU runs (weeks). Latency to users doesn't matter — chase the cleanest + cheapest grid in Europe. Weights: <b>carbon 40 · cost 30 · renewable 20 · stability 10</b>.</p>
  </div>
  <div class="wp-row">
    <h4>Fine-tuning</h4>
    <p>Shorter runs (hours–days), often near the data source. Cost leans heavier than for training; carbon still matters. Weights: <b>carbon 30 · cost 40 · renewable 20 · stability 10</b>.</p>
  </div>
  <div class="wp-row">
    <h4>Inference</h4>
    <p>Continuous real-time serving. Every request is a user waiting — physical distance to the serving region matters. Each country's score is attenuated by a latency penalty based on its distance from the population centroid of the serving region. Weights: <b>carbon 20 · cost 45 · renewable 15 · stability 20</b>.</p>
  </div>
`;

function _rankTooltipHtml(c) {
  const w = RankingState.activeWeights || {};
  const wKey = {
    "carbon_score": "carbon", "cost_score": "cost",
    "renewable_score": "renewable", "stability_score": "stability",
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

function _updateCaption(totalCount) {
  const cap = document.getElementById("ranking-caption");
  if (!cap) return;
  if (RankingState.workload === "inference") {
    cap.textContent = `Inference mode · scoring ${totalCount} candidate sites, attenuated by distance from ${REGION_LABEL[RankingState.region] || RankingState.region}. Closer = better: a country 3000 km from the serving region loses up to 40% of its CSS.`;
    cap.classList.add("visible");
  } else if (RankingState.workload === "fine-tuning") {
    cap.textContent = `Fine-tuning mode · scoring ${totalCount} sites. Cost-leaning baseline; latency ignored (fine-tuning is batch).`;
    cap.classList.add("visible");
  } else {
    cap.textContent = `Training mode · scoring ${totalCount} sites across Europe. Long-running GPU workloads — clean + cheap dominate; location otherwise flexible.`;
    cap.classList.add("visible");
  }
}

function _renderList(countries) {
  const list = document.getElementById("ranking-list");
  const expandBtn = document.getElementById("ranking-expand-btn");
  list.innerHTML = "";
  const total = countries.length;

  // Collapsed view: top 6 + gap + bottom 4
  const TOP_N = 6, BOT_N = 4;
  const useCollapsed = !RankingState.expanded && total > (TOP_N + BOT_N + 1);
  const renderList = useCollapsed
    ? [...countries.slice(0, TOP_N), { _gap: true, _hidden: total - TOP_N - BOT_N }, ...countries.slice(-BOT_N)]
    : countries;

  renderList.forEach((c, i) => {
    if (c._gap) {
      const gap = document.createElement("div");
      gap.className = "rank-gap";
      gap.textContent = `… ${c._hidden} more …`;
      list.appendChild(gap);
      return;
    }
    const card = document.createElement("div");
    const isTopInOverall = countries[0].country === c.country;
    card.className = "rank-card" + (isTopInOverall ? " top" : "");
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

  if (expandBtn) {
    expandBtn.style.display = total > (TOP_N + BOT_N + 1) ? "" : "none";
    expandBtn.textContent = RankingState.expanded ? "Show less" : "Show all countries";
    expandBtn.classList.toggle("expanded", RankingState.expanded);
  }
}

async function renderRanking() {
  const list = document.getElementById("ranking-list");
  const title = document.getElementById("ranking-title");
  try {
    const params = new URLSearchParams({ workload: RankingState.workload });
    if (RankingState.workload === "inference") params.set("region", RankingState.region);
    if (RankingState.preset !== "balanced") params.set("weights", RankingState.preset);
    const data = await fetchJson(`/api/ranking?${params}`);
    RankingState.activeWeights = data.weights || null;
    if (title) {
      title.textContent = `Compute Siting Score · ${data.countries.length} countries`;
    }
    _updateCaption(data.countries.length);
    _renderList(data.countries);
  } catch (e) {
    list.textContent = "Failed to load ranking.";
    console.error(e);
  }
}

function _toggleWorkloadPopover(show) {
  let pop = document.getElementById("workload-popover");
  const btn = document.getElementById("workload-info-btn");
  if (!btn) return;
  if (show) {
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "workload-popover";
      pop.className = "workload-popover";
      pop.innerHTML = WORKLOAD_EXPLAINER;
      document.body.appendChild(pop);
    }
    const rect = btn.getBoundingClientRect();
    pop.classList.add("visible");
    // Position below the button; clamp to viewport
    pop.style.top = `${rect.bottom + window.scrollY + 6}px`;
    pop.style.left = `${Math.max(8, Math.min(window.innerWidth - pop.offsetWidth - 8, rect.left + window.scrollX - 80))}px`;
    btn.classList.add("active");
  } else if (pop) {
    pop.classList.remove("visible");
    if (btn) btn.classList.remove("active");
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

  // Workload info popover
  const infoBtn = document.getElementById("workload-info-btn");
  if (infoBtn) {
    infoBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const pop = document.getElementById("workload-popover");
      const visible = pop && pop.classList.contains("visible");
      _toggleWorkloadPopover(!visible);
    });
  }
  // Click outside to close the popover
  document.addEventListener("click", (e) => {
    const pop = document.getElementById("workload-popover");
    if (!pop || !pop.classList.contains("visible")) return;
    if (pop.contains(e.target) || e.target.id === "workload-info-btn") return;
    _toggleWorkloadPopover(false);
  });

  // Show-all expand button
  const expandBtn = document.getElementById("ranking-expand-btn");
  if (expandBtn) {
    expandBtn.addEventListener("click", () => {
      RankingState.expanded = !RankingState.expanded;
      renderRanking();
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  wireRankingControls();
  renderRanking();
});
