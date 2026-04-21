const BriefingState = {
  country: null,  // will be hydrated from country-select on DOMContentLoaded
  workload: "training",
};

async function renderBriefing() {
  if (!BriefingState.country) return;
  const card = document.getElementById("note-card");
  if (!card) return;
  try {
    const params = new URLSearchParams({
      country: BriefingState.country, workload: BriefingState.workload,
    });
    const data = await fetchJson(`/api/briefing?${params}`);

    const nameEl = document.getElementById("note-country");
    const countryName = (window.MAP_NAMES && window.MAP_NAMES[data.country]) || data.country;
    if (nameEl) nameEl.textContent = countryName + " · " + BriefingState.workload;

    document.getElementById("note-headline").textContent = data.headline || "";

    const bulletsEl = document.getElementById("note-bullets");
    bulletsEl.innerHTML = (data.bullets || []).map(b => `<li>${b}</li>`).join("");

    const risk = (data.risk_flag || "med").toLowerCase();
    const riskEl = document.getElementById("note-risk");
    riskEl.classList.remove("risk-low", "risk-med", "risk-high");
    riskEl.classList.add("risk-" + risk);
    riskEl.querySelector(".note-risk-text").textContent = risk === "low" ? "site here" : risk === "med" ? "tradeoffs" : "avoid";

    document.getElementById("note-sources").textContent = (data.sources || []).join(" · ");

    const asof = data.as_of ? new Date(data.as_of) : null;
    document.getElementById("note-asof").textContent = asof
      ? "as of " + asof.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : "";
  } catch (e) {
    console.error("briefing render failed:", e);
    const headline = document.getElementById("note-headline");
    if (headline) headline.textContent = "Briefing unavailable — check backend.";
  }
}

function _observeCountryAndWorkload() {
  // Country changes via main selector
  const sel = document.getElementById("country-select");
  if (sel) {
    BriefingState.country = sel.value;
    sel.addEventListener("change", () => {
      BriefingState.country = sel.value;
      renderBriefing();
    });
  }

  // Workload changes from the ranking strip's workload switcher
  document.querySelectorAll(".workload-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      BriefingState.workload = btn.dataset.workload;
      renderBriefing();
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  _observeCountryAndWorkload();
  renderBriefing();
});
