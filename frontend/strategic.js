async function renderStrategicCards() {
  const host = document.getElementById("strategic-cards");
  if (!host) return;
  try {
    const r = await fetch("/strategic_quotes.json");
    const data = await r.json();
    const cards = data.cards || [];
    if (cards.length === 0) { host.textContent = "No cards available."; return; }

    host.innerHTML = cards.map(c => `
      <a class="strat-card" href="${c.href}" target="_blank" rel="noreferrer" style="${c.accent ? `border-left-color:${c.accent}` : ''}">
        <div class="strat-subtitle">${c.subtitle || ''}</div>
        <div class="strat-title">${c.title}</div>
        <div class="strat-stat" ${c.accent ? `style="color:${c.accent}"` : ''}>${c.stat}</div>
        <div class="strat-stat-sub">${c.stat_sub || ''}</div>
        <div class="strat-quote">${c.quote}</div>
        <div class="strat-source">${c.source}</div>
      </a>
    `).join("");
  } catch (e) {
    host.textContent = "Failed to load strategic cards.";
    console.error(e);
  }
}

document.addEventListener("DOMContentLoaded", renderStrategicCards);
