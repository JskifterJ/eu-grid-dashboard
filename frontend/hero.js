async function renderHero() {
  const mw = 10, hours = 6;
  try {
    const ranking = await fetchRanking();
    const top = ranking.countries[0];
    const bottom = ranking.countries[ranking.countries.length - 1];

    document.getElementById("hero-time").textContent =
      new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " UTC";

    document.getElementById("hero-best-country").textContent = top.name;
    document.getElementById("hero-best-country2").textContent = top.name;
    document.getElementById("hero-worst-country").textContent = bottom.name;

    const topGen = await fetchGeneration(top.country);
    const bottomGen = await fetchGeneration(bottom.country);
    const topPrices = await fetchPrices(top.country);

    document.getElementById("hero-best-co2").textContent = Math.round(topGen.co2_intensity);
    document.getElementById("hero-best-price").textContent = Math.round(topPrices.current_eur_mwh || 0);

    const topEmit = (mw * hours * topGen.co2_intensity / 1000).toFixed(1);
    const bottomEmit = (mw * hours * bottomGen.co2_intensity / 1000).toFixed(1);
    document.getElementById("hero-best-emit").textContent = topEmit;
    document.getElementById("hero-worst-emit").textContent = bottomEmit;
  } catch (e) {
    console.error("hero render failed", e);
  }
}

document.addEventListener("DOMContentLoaded", renderHero);
