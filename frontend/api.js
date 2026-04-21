// All functions exposed as globals — no ES module syntax needed
const API_BASE = '';

window.fetchGeneration = async function(country) {
  const res = await fetch(`${API_BASE}/api/generation?country=${country}`);
  if (!res.ok) throw new Error(`generation fetch failed: ${res.status}`);
  return res.json();
};

window.fetchPrices = async function(country) {
  const res = await fetch(`${API_BASE}/api/prices?country=${country}`);
  if (!res.ok) throw new Error(`prices fetch failed: ${res.status}`);
  return res.json();
};

window.fetchFlows = async function(country) {
  const res = await fetch(`${API_BASE}/api/flows?country=${country}`);
  if (!res.ok) throw new Error(`flows fetch failed: ${res.status}`);
  return res.json();
};

window.fetchOverview = async function() {
  const res = await fetch(`${API_BASE}/api/overview`);
  if (!res.ok) throw new Error(`overview fetch failed: ${res.status}`);
  return res.json();
};

window.fetchSummary = async function(country) {
  const res = await fetch(`${API_BASE}/api/summary?country=${country}`);
  if (!res.ok) throw new Error(`summary fetch failed: ${res.status}`);
  return res.json();
};

async function fetchJson(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`fetch failed: ${res.status} ${path}`);
  return res.json();
}

window.fetchRanking = async function(weights) {
  const q = weights ? `?weights=${encodeURIComponent(weights)}` : "";
  return fetchJson(`/api/ranking${q}`);
};

window.fetchCss = async function(country, weights) {
  const params = new URLSearchParams({ country });
  if (weights) params.set("weights", weights);
  return fetchJson(`/api/css?${params}`);
};

window.fetchForecast = async function(country) {
  return fetchJson(`/api/forecast?country=${country}`);
};

window.fetchSimulate = async function({ country, mw, hours, workload, region, hub, weights }) {
  const params = new URLSearchParams({ country, mw, hours, workload });
  if (region) params.set("region", region);
  if (hub) params.set("hub", hub);
  if (weights) params.set("weights", weights);
  return fetchJson(`/api/simulate?${params}`);
};

async function fetchAllFlows(countryCodes) {
  const results = await Promise.allSettled(
    countryCodes.map(c => fetchJson(`/api/flows?country=${c}`).then(d => ({country: c, ...d})))
  );
  return results.filter(r => r.status === 'fulfilled').map(r => r.value);
}
window.fetchAllFlows = fetchAllFlows;
