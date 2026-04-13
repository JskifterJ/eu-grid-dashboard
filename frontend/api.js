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
