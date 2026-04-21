const RankingState = {
  preset: "balanced",
  workload: "training",
  region: "western",
};

async function renderRanking() {
  const list = document.getElementById("ranking-list");
  try {
    const params = new URLSearchParams({ workload: RankingState.workload });
    if (RankingState.workload === "inference") params.set("region", RankingState.region);
    if (RankingState.preset !== "balanced") params.set("weights", RankingState.preset);
    const data = await fetchJson(`/api/ranking?${params}`);
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
