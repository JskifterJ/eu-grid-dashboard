const SimState = {
  workload: "training",
  country: "FR",
  mw: 10,
  hours: 6,
  region: "western",
  carbon_price: 75,
};

const SIM_COUNTRIES = [
  ["DE","Germany"],["FR","France"],["GB","United Kingdom"],["NO","Norway"],["SE","Sweden"],
  ["DK","Denmark"],["FI","Finland"],["CH","Switzerland"],["AT","Austria"],["NL","Netherlands"],
  ["BE","Belgium"],["PL","Poland"],["ES","Spain"],["IT","Italy"],["CZ","Czech Republic"],
  ["PT","Portugal"],["RO","Romania"],["GR","Greece"],["IE","Ireland"],["HU","Hungary"],
  ["EE","Estonia"],["LV","Latvia"],["LT","Lithuania"],["SK","Slovakia"],["SI","Slovenia"],
  ["HR","Croatia"],["BG","Bulgaria"],["RS","Serbia"],["BA","Bosnia & Herzegovina"],
  ["ME","Montenegro"],["MK","North Macedonia"],["AL","Albania"],["IS","Iceland"],
  ["CY","Cyprus"],["LU","Luxembourg"],
];

const FLAG = {"DE":"🇩🇪","FR":"🇫🇷","GB":"🇬🇧","NO":"🇳🇴","SE":"🇸🇪","DK":"🇩🇰","FI":"🇫🇮","CH":"🇨🇭","AT":"🇦🇹","NL":"🇳🇱","BE":"🇧🇪","PL":"🇵🇱","ES":"🇪🇸","IT":"🇮🇹","CZ":"🇨🇿","PT":"🇵🇹","RO":"🇷🇴","GR":"🇬🇷","IE":"🇮🇪","HU":"🇭🇺","EE":"🇪🇪","LV":"🇱🇻","LT":"🇱🇹","SK":"🇸🇰","SI":"🇸🇮","HR":"🇭🇷","BG":"🇧🇬","RS":"🇷🇸","BA":"🇧🇦","ME":"🇲🇪","MK":"🇲🇰","AL":"🇦🇱","IS":"🇮🇸","CY":"🇨🇾","LU":"🇱🇺"};

function _populateCountrySelect() {
  const sel = document.getElementById("sim-country");
  if (!sel) return;
  sel.innerHTML = SIM_COUNTRIES
    .map(([code, name]) => `<option value="${code}">${FLAG[code] || ''} ${name}</option>`)
    .join("");
  sel.value = SimState.country;
}

function _fmtT(t) {
  if (t >= 100) return `${t.toFixed(0)}`;
  if (t >= 10) return `${t.toFixed(1)}`;
  return `${t.toFixed(2)}`;
}

function _fmtEur(v) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1000) return `${(v / 1000).toFixed(1)}k`;
  return `${v.toFixed(0)}`;
}

function _fmtHour(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: "UTC" }) + " UTC";
}

function _renderOutput(result) {
  const el = document.getElementById("sim-output");
  if (!el) return;
  const countryName = (SIM_COUNTRIES.find(([c]) => c === result.country) || [])[1] || result.country;
  const hubName = (SIM_COUNTRIES.find(([c]) => c === result.hub_country) || [])[1] || result.hub_country;
  const deltaVsHubCo2 = ((result.hub_t_co2 - result.current_hour_t_co2) / result.hub_t_co2 * 100).toFixed(0);
  const deltaVsHubCost = ((result.hub_cost_eur - result.current_hour_cost_eur) / result.hub_cost_eur * 100).toFixed(0);

  const bestHourHtml = (result.best_hour_t_co2 !== null) ? `
    <div class="sim-output-row">
      <span class="sim-k">Best hour next 24h</span>
      <span>
        <span class="sim-v">${_fmtT(result.best_hour_t_co2)}<span class="sim-unit-sm"> t CO₂</span></span>
        <div class="sim-sub">€${_fmtEur(result.best_hour_cost_eur)} · starts ${_fmtHour(result.best_hour_start)}</div>
      </span>
    </div>
  ` : `
    <div class="sim-output-row">
      <span class="sim-k">Best hour next 24h</span>
      <span>
        <span class="sim-v" style="color:var(--dim)">n/a for inference</span>
        <div class="sim-sub">inference is continuous — no "best hour" window to pick</div>
      </span>
    </div>
  `;

  const latencyHtml = (result.workload === "inference" && result.latency_penalty > 0) ? `
    <div class="sim-verdict">
      <span class="sim-tag">latency</span>
      <strong>${countryName}</strong> is ${Math.round(result.latency_penalty * 100)}% penalized for serving ${SimState.region.replace(/^./, c => c.toUpperCase())} EU — the physics of real-time inference. CSS is multiplied by (1 − ${result.latency_penalty.toFixed(2)}).
    </div>
  ` : '';

  el.innerHTML = `
    <div class="sim-output-row">
      <span class="sim-k">Current hour</span>
      <span>
        <span class="sim-v">${_fmtT(result.current_hour_t_co2)}<span class="sim-unit-sm"> t CO₂</span></span>
        <div class="sim-sub">€${_fmtEur(result.current_hour_cost_eur)} total cost</div>
      </span>
    </div>
    ${bestHourHtml}
    <div class="sim-output-row">
      <span class="sim-k">vs. ${hubName} hub</span>
      <span>
        <span class="sim-v" style="color:${result.current_hour_t_co2 < result.hub_t_co2 ? 'var(--green)' : 'var(--orange)'}">
          ${result.current_hour_t_co2 < result.hub_t_co2 ? '−' : '+'}${Math.abs(deltaVsHubCo2)}%<span class="sim-unit-sm"> CO₂</span>
        </span>
        <div class="sim-sub">${result.current_hour_t_co2 < result.hub_t_co2 ? '−' : '+'}${Math.abs(deltaVsHubCost)}% cost · ${hubName} would emit ${_fmtT(result.hub_t_co2)} t</div>
      </span>
    </div>
    <div class="sim-output-row">
      <span class="sim-k">CSS percentile</span>
      <span class="sim-percentile">
        <span class="sim-percentile-bar"><span class="sim-percentile-fill" style="width:${result.css_percentile}%"></span></span>
        <b>${result.css_percentile}<sup>th</sup></b>
      </span>
    </div>
    ${latencyHtml}
  `;
}

async function runSimulation() {
  const el = document.getElementById("sim-output");
  if (el) el.innerHTML = '<div class="sim-loading">Computing…</div>';
  try {
    const params = new URLSearchParams({
      country: SimState.country,
      mw: SimState.mw,
      hours: SimState.hours,
      workload: SimState.workload,
      carbon_price: SimState.carbon_price,
    });
    if (SimState.workload === "inference") params.set("region", SimState.region);
    const data = await fetchJson(`/api/simulate?${params}`);
    _renderOutput(data);
    _syncUrl();
  } catch (e) {
    if (el) el.innerHTML = `<div class="sim-loading" style="color:var(--orange)">Failed: ${e.message || e}</div>`;
    console.error(e);
  }
}

// Debounced run
let _runTimer = null;
function _debouncedRun() {
  clearTimeout(_runTimer);
  _runTimer = setTimeout(runSimulation, 180);
}

// URL state sync
function _syncUrl() {
  const params = new URLSearchParams();
  params.set("workload", SimState.workload);
  params.set("country", SimState.country);
  params.set("mw", SimState.mw);
  params.set("hours", SimState.hours);
  params.set("carbon_price", SimState.carbon_price);
  if (SimState.workload === "inference") params.set("region", SimState.region);
  // Only update if simulator section is present
  if (document.getElementById("simulator")) {
    history.replaceState(null, "", `${window.location.pathname}?${params}${window.location.hash.includes('#') ? '' : '#simulator'}`);
  }
}

function _hydrateFromUrl() {
  const p = new URLSearchParams(window.location.search);
  if (p.has("workload") && ["training","fine-tuning","inference"].includes(p.get("workload"))) SimState.workload = p.get("workload");
  if (p.has("country")) SimState.country = p.get("country");
  if (p.has("mw")) SimState.mw = parseFloat(p.get("mw")) || SimState.mw;
  if (p.has("hours")) SimState.hours = parseFloat(p.get("hours")) || SimState.hours;
  if (p.has("carbon_price")) SimState.carbon_price = parseFloat(p.get("carbon_price")) || SimState.carbon_price;
  if (p.has("region")) SimState.region = p.get("region");
}

function _applyStateToInputs() {
  document.querySelectorAll("#sim-workload .sim-pill").forEach(b => {
    b.classList.toggle("active", b.dataset.value === SimState.workload);
  });
  const countrySel = document.getElementById("sim-country");
  const regionSel = document.getElementById("sim-region");
  const mw = document.getElementById("sim-mw");
  const hours = document.getElementById("sim-hours");
  const carbon = document.getElementById("sim-carbon");
  const regionField = document.getElementById("sim-region-field");
  if (countrySel) countrySel.value = SimState.country;
  if (regionSel) regionSel.value = SimState.region;
  if (mw) mw.value = SimState.mw;
  if (hours) hours.value = SimState.hours;
  if (carbon) carbon.value = SimState.carbon_price;
  if (regionField) regionField.style.display = SimState.workload === "inference" ? "" : "none";
}

function _wireInputs() {
  document.querySelectorAll("#sim-workload .sim-pill").forEach(btn => {
    btn.addEventListener("click", () => {
      SimState.workload = btn.dataset.value;
      _applyStateToInputs();
      runSimulation();
    });
  });
  const countrySel = document.getElementById("sim-country");
  if (countrySel) countrySel.addEventListener("change", () => { SimState.country = countrySel.value; runSimulation(); });
  const regionSel = document.getElementById("sim-region");
  if (regionSel) regionSel.addEventListener("change", () => { SimState.region = regionSel.value; runSimulation(); });
  const mw = document.getElementById("sim-mw");
  if (mw) mw.addEventListener("input", () => { SimState.mw = parseFloat(mw.value) || 1; _debouncedRun(); });
  const hours = document.getElementById("sim-hours");
  if (hours) hours.addEventListener("input", () => { SimState.hours = parseFloat(hours.value) || 1; _debouncedRun(); });
  const carbon = document.getElementById("sim-carbon");
  if (carbon) carbon.addEventListener("input", () => { SimState.carbon_price = parseFloat(carbon.value) || 0; _debouncedRun(); });

  const shareBtn = document.getElementById("sim-share-btn");
  if (shareBtn) shareBtn.addEventListener("click", async () => {
    const href = window.location.href;
    try {
      await navigator.clipboard.writeText(href);
      shareBtn.textContent = "✓ Copied";
      shareBtn.classList.add("copied");
      setTimeout(() => {
        shareBtn.textContent = "Copy shareable link";
        shareBtn.classList.remove("copied");
      }, 2000);
    } catch (e) {
      shareBtn.textContent = href;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  _hydrateFromUrl();
  _populateCountrySelect();
  _applyStateToInputs();
  _wireInputs();
  runSimulation();
});
