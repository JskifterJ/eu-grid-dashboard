const DeferredState = {
  tokens_m: 1000,
  kwh_per_m: 0.30,
  discount_pct: 30,
  country: null,
};

function _fmt(v, digits = 1) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1000) return `${(v / 1000).toFixed(1)}k`;
  if (v < 10 && v >= 0.1) return v.toFixed(digits + 1);
  return v.toFixed(digits);
}

async function renderDeferred() {
  if (!DeferredState.country) return;
  const host = document.getElementById("def-output");
  const nameEl = document.getElementById("def-country-name");
  if (!host) return;

  try {
    // hours=6 just to populate the API; we use average windows, not total workload cost
    const params = new URLSearchParams({
      country: DeferredState.country, mw: 1, hours: 6,
    });
    const data = await fetchJson(`/api/time-of-day?${params}`);

    if (nameEl) {
      const name = (window.MAP_NAMES && window.MAP_NAMES[DeferredState.country]) || DeferredState.country;
      nameEl.textContent = name;
    }

    const tokens_m = DeferredState.tokens_m;
    const kwh_per_m = DeferredState.kwh_per_m;
    const total_kwh = tokens_m * kwh_per_m;

    // Peak hour = worst window (dirtiest, priciest)
    const peak_co2 = data.worst_window.avg_co2_g_per_kwh;
    const peak_price = data.worst_window.avg_price_eur_mwh;
    // Off-peak = best window, with discount rebated from price
    const off_co2 = data.best_window.avg_co2_g_per_kwh;
    const off_price_raw = data.best_window.avg_price_eur_mwh;
    const off_price = off_price_raw * (1 - DeferredState.discount_pct / 100);

    // kg CO₂ = kWh × g/kWh / 1000
    const peak_co2_kg = total_kwh * peak_co2 / 1000;
    const off_co2_kg = total_kwh * off_co2 / 1000;
    // € cost: kWh × €/MWh / 1000 = kWh × €/(1000 kWh) ... wait: €/MWh = €/(1000 kWh); so kWh × €/MWh / 1000
    const peak_cost = total_kwh * peak_price / 1000;
    const off_cost = total_kwh * off_price / 1000;

    const co2_saved_pct = peak_co2_kg > 0 ? ((peak_co2_kg - off_co2_kg) / peak_co2_kg * 100) : 0;
    const cost_saved_pct = peak_cost > 0 ? ((peak_cost - off_cost) / peak_cost * 100) : 0;
    const co2_saved_kg = peak_co2_kg - off_co2_kg;
    const cost_saved_eur = peak_cost - off_cost;

    host.innerHTML = `
      <div class="def-row">
        <div class="def-card peak">
          <span class="def-kind">On-demand · peak hour</span>
          <div class="def-value">${_fmt(peak_co2_kg)}<span style="font-size:13px;color:var(--muted);margin-left:4px;">kg CO₂</span></div>
          <div class="def-sub2">€${_fmt(peak_cost)} · ${peak_co2.toFixed(0)} g/kWh @ €${peak_price.toFixed(0)}/MWh</div>
        </div>
        <div class="def-card off-peak">
          <span class="def-kind">Deferred · off-peak batch</span>
          <div class="def-value">${_fmt(off_co2_kg)}<span style="font-size:13px;color:var(--muted);margin-left:4px;">kg CO₂</span></div>
          <div class="def-sub2">€${_fmt(off_cost)} · ${off_co2.toFixed(0)} g/kWh @ €${off_price.toFixed(0)}/MWh after ${DeferredState.discount_pct}% rebate</div>
        </div>
      </div>
      <div class="def-verdict">
        Batching ${_fmt(tokens_m, 0)}M output tokens off-peak saves
        <strong>${co2_saved_pct.toFixed(0)}% CO₂</strong> and
        <strong>${cost_saved_pct.toFixed(0)}% cost</strong> — that's
        <strong>${_fmt(co2_saved_kg)} kg CO₂</strong> and
        <strong>€${_fmt(cost_saved_eur)}</strong> avoided per batch.
        <em>Scale to a 24/7 agent fleet and the economics compound — exactly the kind of tier a neocloud or inference provider could productize.</em>
      </div>
    `;
  } catch (e) {
    host.innerHTML = `<div class="sim-loading" style="color:var(--orange)">Failed: ${e.message || e}</div>`;
    console.error(e);
  }
}

let _defRunTimer = null;
function _debouncedDef() {
  clearTimeout(_defRunTimer);
  _defRunTimer = setTimeout(renderDeferred, 180);
}

function _observeSimulatorCountry() {
  // Piggyback on the main country selector — when it changes, update our country too
  const sel = document.getElementById("country-select");
  if (sel) {
    DeferredState.country = sel.value;
    sel.addEventListener("change", () => {
      DeferredState.country = sel.value;
      renderDeferred();
    });
  }
  // Also follow the simulator's country state if user is mainly using that
  const simCountrySel = document.getElementById("sim-country");
  if (simCountrySel) {
    simCountrySel.addEventListener("change", () => {
      DeferredState.country = simCountrySel.value;
      renderDeferred();
    });
  }
}

function _wireDeferredInputs() {
  const tokens = document.getElementById("def-tokens");
  if (tokens) tokens.addEventListener("input", () => {
    DeferredState.tokens_m = Math.max(1, parseFloat(tokens.value) || 1);
    _debouncedDef();
  });
  const kwh = document.getElementById("def-kwh");
  if (kwh) kwh.addEventListener("input", () => {
    DeferredState.kwh_per_m = Math.max(0.01, parseFloat(kwh.value) || 0.01);
    _debouncedDef();
  });
  const discount = document.getElementById("def-discount");
  if (discount) discount.addEventListener("input", () => {
    DeferredState.discount_pct = Math.max(0, Math.min(70, parseFloat(discount.value) || 0));
    _debouncedDef();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  _observeSimulatorCountry();
  _wireDeferredInputs();
  renderDeferred();
});
