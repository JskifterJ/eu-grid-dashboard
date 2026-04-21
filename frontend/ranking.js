const RankingState = {
  preset: "balanced",
  workload: "training",
};

async function renderRanking() {
  const list = document.getElementById("ranking-list");
  try {
    const data = await fetchRanking(RankingState.preset === "balanced" ? null : RankingState.preset);
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
      // Workload shapes the simulator (Plan B); for now it annotates only.
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  wireRankingControls();
  renderRanking();
});
