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

function _co2ColorForRibbon(val) {
  // Scale 0..600 g/kWh → green..amber..red
  const pct = Math.min(1, Math.max(0, val / 600));
  if (pct < 0.25) {
    const t = pct / 0.25;
    return `rgba(${63 + (210 - 63) * t}, ${185 + (153 - 185) * t}, ${80 + (34 - 80) * t}, 0.95)`;
  } else if (pct < 0.6) {
    const t = (pct - 0.25) / 0.35;
    return `rgba(${210}, ${153 + (82 - 153) * t}, ${34}, 0.95)`;
  } else {
    const t = Math.min(1, (pct - 0.6) / 0.4);
    return `rgba(${210 + (248 - 210) * t}, ${82 + (81 - 82) * t}, ${34 + (73 - 34) * t}, 0.95)`;
  }
}

async function renderTimeOfDay() {
  const ribbon = document.getElementById("tod-ribbon");
  const savings = document.getElementById("tod-savings");
  if (!ribbon || !savings) return;
  try {
    const params = new URLSearchParams({
      country: SimState.country, mw: SimState.mw, hours: SimState.hours,
    });
    const data = await fetchJson(`/api/time-of-day?${params}`);

    // Mark hours within the best/worst windows
    const bestStartIdx = data.hours.findIndex(h => h.timestamp === data.best_window.start);
    const worstStartIdx = data.hours.findIndex(h => h.timestamp === data.worst_window.start);
    const w = Math.max(1, Math.ceil(SimState.hours));

    ribbon.innerHTML = data.hours.map((h, i) => {
      const isBest = i >= bestStartIdx && i < bestStartIdx + w;
      const isWorst = i >= worstStartIdx && i < worstStartIdx + w;
      const ts = new Date(h.timestamp);
      const hh = ts.getUTCHours().toString().padStart(2, "0");
      const showLabel = i % 4 === 0;  // label every 4 hours
      return `
        <div class="tod-hour ${isBest ? 'best' : ''} ${isWorst ? 'worst' : ''}"
             style="background:${_co2ColorForRibbon(h.co2_g_per_kwh)}"
             data-ts="${h.timestamp}" data-co2="${h.co2_g_per_kwh.toFixed(0)}" data-price="${h.price_eur_mwh.toFixed(1)}">
          ${showLabel ? `<div class="tod-hour-label">${hh}:00</div>` : ''}
        </div>
      `;
    }).join("");

    // Tooltip wiring using existing window.showTooltip infrastructure from map.js
    ribbon.querySelectorAll(".tod-hour").forEach(el => {
      el.addEventListener("mouseenter", (event) => {
        const ts = new Date(el.dataset.ts);
        const hh = ts.getUTCHours().toString().padStart(2, "0");
        const html = `
          <div class="tt-title">${hh}:00 UTC</div>
          <div class="tt-row"><span>CO₂</span><b>${el.dataset.co2} g/kWh</b></div>
          <div class="tt-row"><span>Price</span><b>€${el.dataset.price}/MWh</b></div>
        `;
        window.showTooltip && window.showTooltip(html, event);
      });
      el.addEventListener("mousemove", (event) => window.moveTooltip && window.moveTooltip(event));
      el.addEventListener("mouseleave", () => window.hideTooltip && window.hideTooltip());
    });

    const bestStart = new Date(data.best_window.start);
    const bestHH = bestStart.getUTCHours().toString().padStart(2, "0");
    const worstStart = new Date(data.worst_window.start);
    const worstHH = worstStart.getUTCHours().toString().padStart(2, "0");

    if (data.co2_savings_pct > 1) {
      savings.innerHTML = `
        Start at <strong>${bestHH}:00 UTC</strong> instead of ${worstHH}:00 UTC and save
        <strong>${data.co2_savings_pct.toFixed(0)}% CO₂</strong> ·
        <em>${data.co2_savings_kg.toFixed(0)} kg avoided</em>
      `;
    } else {
      savings.innerHTML = `<em>The grid is flat for this window — timing doesn't matter today.</em>`;
    }
  } catch (e) {
    console.error("time-of-day render failed:", e);
  }
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
    renderTimeOfDay();  // NEW: refresh ribbon
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
