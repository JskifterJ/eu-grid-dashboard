"""Realistic mock data for all supported countries — used when ENTSO_API_KEY is not set."""
from datetime import datetime, timezone, timedelta

from app.models import GenerationData, PriceData, PricePoint, FlowData, FlowItem, CountryOverview

# Per-country generation profiles (display names, GW)
MOCK_GENERATION: dict[str, dict[str, float]] = {
    "DK": {"Wind": 3.8, "Solar": 0.6, "Gas": 0.9, "Biomass": 0.5, "Other": 0.2},
    "DE": {"Wind": 28.0, "Solar": 8.0, "Gas": 18.0, "Coal": 10.0, "Nuclear": 4.0, "Biomass": 5.0},
    "FR": {"Nuclear": 42.0, "Hydro": 8.0, "Wind": 7.0, "Solar": 3.0, "Gas": 5.0},
    "NO": {"Hydro": 28.0, "Wind": 3.5, "Gas": 0.3},
    "SE": {"Nuclear": 7.0, "Hydro": 9.0, "Wind": 4.5, "Solar": 0.3, "Biomass": 1.2},
    "GB": {"Gas": 15.0, "Wind": 12.0, "Nuclear": 5.5, "Solar": 2.5, "Hydro": 0.8, "Biomass": 2.0},
    "FI": {"Nuclear": 2.8, "Hydro": 3.2, "Wind": 2.1, "Biomass": 2.5, "Gas": 0.6},
    "CH": {"Hydro": 5.5, "Nuclear": 3.2, "Solar": 0.8, "Wind": 0.1},
    "AT": {"Hydro": 8.0, "Wind": 2.8, "Solar": 1.2, "Gas": 1.5, "Biomass": 0.5},
    "NL": {"Gas": 8.0, "Wind": 5.0, "Solar": 2.5, "Nuclear": 0.5, "Biomass": 0.8},
    "BE": {"Nuclear": 4.0, "Gas": 3.5, "Wind": 2.2, "Solar": 1.0, "Biomass": 0.6},
    "PL": {"Coal": 18.0, "Gas": 3.5, "Wind": 4.0, "Solar": 2.0, "Biomass": 1.0},
    "ES": {"Wind": 12.0, "Solar": 8.0, "Nuclear": 7.0, "Hydro": 5.0, "Gas": 6.0},
    "IT": {"Gas": 18.0, "Solar": 9.0, "Wind": 4.0, "Hydro": 6.0, "Biomass": 1.5},
    "CZ": {"Nuclear": 4.0, "Coal": 5.5, "Gas": 1.0, "Wind": 0.3, "Solar": 0.5},
    "PT": {"Wind": 3.5, "Hydro": 3.0, "Solar": 1.2, "Gas": 1.8, "Biomass": 0.5},
    "RO": {"Hydro": 5.0, "Nuclear": 1.4, "Wind": 2.5, "Coal": 3.0, "Solar": 0.8},
    "GR": {"Gas": 3.5, "Wind": 2.5, "Solar": 2.0, "Hydro": 1.2, "Lignite": 1.0},
    "IE": {"Wind": 2.8, "Gas": 1.5, "Biomass": 0.2, "Hydro": 0.2},
    "HU": {"Gas": 2.5, "Nuclear": 2.0, "Solar": 0.8, "Wind": 0.3, "Biomass": 0.3},
}

RENEWABLE_DISPLAY = {"Wind", "Solar", "Hydro", "Hydro Reservoir", "Pumped Storage", "Biomass", "Other Renewable", "Geothermal"}

MOCK_EMISSION: dict[str, float] = {
    "Wind": 11.0, "Solar": 41.0, "Nuclear": 12.0, "Hydro": 24.0,
    "Hydro Reservoir": 24.0, "Pumped Storage": 24.0, "Gas": 490.0,
    "Coal": 820.0, "Lignite": 1054.0, "Oil": 650.0, "Biomass": 230.0,
    "Other Renewable": 50.0, "Other": 300.0, "Geothermal": 38.0, "Waste": 330.0,
}

MOCK_PRICES: dict[str, float] = {
    "DK": 82.0, "DE": 78.0, "FR": 65.0, "NO": 35.0, "SE": 42.0,
    "GB": 95.0, "FI": 55.0, "CH": 70.0, "AT": 74.0, "NL": 80.0,
    "BE": 76.0, "PL": 68.0, "ES": 58.0, "IT": 88.0, "CZ": 72.0,
    "PT": 55.0, "RO": 62.0, "GR": 85.0, "IE": 90.0, "HU": 70.0,
}

MOCK_FLOWS: dict[str, list[tuple[str, float, str]]] = {
    "DK": [("Germany", 0.8, "export"), ("Norway", 0.3, "import"), ("Sweden", 0.5, "import")],
    "DE": [("France", 1.2, "import"), ("Austria", 0.9, "export"), ("Netherlands", 1.5, "export"), ("Poland", 0.6, "export")],
    "FR": [("Germany", 1.2, "export"), ("Spain", 2.1, "export"), ("Italy", 1.8, "export"), ("United Kingdom", 0.9, "export")],
    "NO": [("Sweden", 1.4, "export"), ("Denmark", 0.3, "export"), ("Netherlands", 0.7, "export")],
    "SE": [("Finland", 0.8, "export"), ("Denmark", 0.5, "export"), ("Norway", 1.4, "import")],
    "GB": [("France", 0.9, "import"), ("Netherlands", 0.5, "import"), ("Belgium", 0.4, "import")],
    "FI": [("Sweden", 0.8, "import"), ("Estonia", 0.3, "export")],
    "CH": [("France", 1.1, "import"), ("Germany", 0.8, "import"), ("Italy", 2.0, "export"), ("Austria", 0.5, "export")],
    "AT": [("Germany", 0.9, "import"), ("Italy", 0.7, "export"), ("Switzerland", 0.5, "import")],
    "NL": [("Germany", 1.5, "import"), ("Belgium", 0.6, "export"), ("Norway", 0.7, "import")],
    "BE": [("France", 0.8, "import"), ("Netherlands", 0.6, "import"), ("United Kingdom", 0.4, "export")],
    "PL": [("Germany", 0.6, "import"), ("Czech Republic", 0.4, "export"), ("Sweden", 0.2, "import")],
    "ES": [("France", 2.1, "import"), ("Portugal", 1.0, "export")],
    "IT": [("France", 1.8, "import"), ("Switzerland", 2.0, "import"), ("Austria", 0.7, "import")],
    "CZ": [("Germany", 0.8, "export"), ("Poland", 0.4, "import"), ("Austria", 0.3, "export")],
    "PT": [("Spain", 1.0, "import")],
    "RO": [("Hungary", 0.5, "export"), ("Bulgaria", 0.7, "export")],
    "GR": [("Bulgaria", 0.4, "import"), ("Italy", 0.3, "export")],
    "IE": [("United Kingdom", 0.4, "import")],
    "HU": [("Romania", 0.5, "import"), ("Austria", 0.3, "import"), ("Slovakia", 0.4, "export")],
}

COUNTRY_NAMES: dict[str, str] = {
    "DE": "Germany", "FR": "France", "GB": "United Kingdom", "NO": "Norway",
    "SE": "Sweden", "DK": "Denmark", "FI": "Finland", "CH": "Switzerland",
    "AT": "Austria", "NL": "Netherlands", "BE": "Belgium", "PL": "Poland",
    "ES": "Spain", "IT": "Italy", "CZ": "Czech Republic", "PT": "Portugal",
    "RO": "Romania", "GR": "Greece", "IE": "Ireland", "HU": "Hungary",
}


def _co2(sources: dict[str, float]) -> float:
    total = sum(sources.values())
    if total == 0:
        return 0.0
    return round(sum(gw * MOCK_EMISSION.get(src, 300.0) for src, gw in sources.items()) / total, 1)


def mock_generation(country: str) -> GenerationData:
    sources = MOCK_GENERATION.get(country, {"Gas": 5.0, "Wind": 2.0})
    total = sum(sources.values())
    renewable_gw = sum(v for k, v in sources.items() if k in RENEWABLE_DISPLAY)
    renewable_pct = round((renewable_gw / total * 100) if total > 0 else 0.0, 1)
    return GenerationData(
        country=country,
        sources=sources,
        renewable_pct=renewable_pct,
        co2_intensity=_co2(sources),
        total_gw=round(total, 2),
    )


def mock_prices(country: str) -> PriceData:
    base = MOCK_PRICES.get(country, 75.0)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    import random, hashlib
    seed = int(hashlib.md5(f"{country}{now.date()}".encode()).hexdigest(), 16) % (2**32)
    random.seed(seed)
    prices = []
    for h in range(24):
        ts = (now.replace(hour=0) + timedelta(hours=h)).isoformat()
        # deterministic daily curve: low at night, peak at 8-9am and 6-7pm
        curve = 1.0 + 0.15 * (abs(h - 8.5) < 1.5 or abs(h - 18.5) < 1.5) - 0.1 * (h < 5)
        price = round(base * curve * (0.95 + random.random() * 0.10), 2)
        prices.append(PricePoint(timestamp=ts, price_eur_mwh=price))
    current = prices[min(now.hour, 23)].price_eur_mwh
    delta_pct = round((random.random() - 0.5) * 20, 1)
    return PriceData(country=country, prices=prices, current_eur_mwh=current, delta_pct=delta_pct)


def mock_flows(country: str) -> FlowData:
    raw = MOCK_FLOWS.get(country, [])
    flows = [FlowItem(partner=p, flow_gw=gw, direction=d) for p, gw, d in raw]
    net = sum(f.flow_gw if f.direction == "export" else -f.flow_gw for f in flows)
    return FlowData(country=country, flows=flows, net_gw=round(net, 2))


def mock_overview() -> list[CountryOverview]:
    result = []
    for code, name in COUNTRY_NAMES.items():
        gen = mock_generation(code)
        prices = mock_prices(code)
        result.append(CountryOverview(
            country=code,
            name=name,
            co2_intensity=gen.co2_intensity,
            renewable_pct=gen.renewable_pct,
            price_eur_mwh=prices.current_eur_mwh,
        ))
    return result
