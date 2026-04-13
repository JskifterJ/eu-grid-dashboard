import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from entsoe import EntsoePandasClient

from app.models import GenerationData, PricePoint, PriceData, FlowItem, FlowData, CountryOverview

# ── Emission factors (g CO₂/kWh, IPCC 2014 median values) ───────────────────
EMISSION_FACTORS: dict[str, float] = {
    "Fossil Hard coal": 820.0,
    "Fossil Brown coal/Lignite": 1054.0,
    "Fossil Gas": 490.0,
    "Fossil Oil": 650.0,
    "Fossil Oil shale": 650.0,
    "Fossil Peat": 900.0,
    "Nuclear": 12.0,
    "Wind Onshore": 11.0,
    "Wind Offshore": 12.0,
    "Solar": 41.0,
    "Hydro Run-of-river and poundage": 24.0,
    "Hydro Water Reservoir": 24.0,
    "Hydro Pumped Storage": 24.0,
    "Biomass": 230.0,
    "Waste": 330.0,
    "Geothermal": 38.0,
    "Other renewable": 50.0,
    "Other": 300.0,
}

RENEWABLE_SOURCES = {
    "Wind Onshore", "Wind Offshore", "Solar",
    "Hydro Run-of-river and poundage", "Hydro Water Reservoir",
    "Hydro Pumped Storage", "Geothermal", "Other renewable",
}

DISPLAY_MAP: dict[str, str] = {
    "Fossil Hard coal": "Coal",
    "Fossil Brown coal/Lignite": "Lignite",
    "Fossil Gas": "Gas",
    "Fossil Oil": "Oil",
    "Fossil Oil shale": "Oil Shale",
    "Fossil Peat": "Peat",
    "Nuclear": "Nuclear",
    "Wind Onshore": "Wind",
    "Wind Offshore": "Wind",   # merge into Wind
    "Solar": "Solar",
    "Hydro Run-of-river and poundage": "Hydro",
    "Hydro Water Reservoir": "Hydro Reservoir",
    "Hydro Pumped Storage": "Pumped Storage",
    "Biomass": "Biomass",
    "Waste": "Waste",
    "Geothermal": "Geothermal",
    "Other renewable": "Other Renewable",
    "Other": "Other",
}

AREA_CODES: dict[str, str] = {
    "DE": "DE_LU",
    "FR": "FR",
    "GB": "GB",
    "NO": "NO_1",
    "SE": "SE_3",
    "DK": "DK_1",
    "FI": "FI",
    "CH": "CH",
    "AT": "AT",
    "NL": "NL",
    "BE": "BE",
    "PL": "PL",
    "ES": "ES",
    "IT": "IT_NORD",
    "CZ": "CZ",
    "PT": "PT",
    "RO": "RO",
    "GR": "GR",
    "IE": "IE_SEM",
    "HU": "HU",
}

COUNTRY_NAMES: dict[str, str] = {
    "DE": "Germany", "FR": "France", "GB": "United Kingdom", "NO": "Norway",
    "SE": "Sweden", "DK": "Denmark", "FI": "Finland", "CH": "Switzerland",
    "AT": "Austria", "NL": "Netherlands", "BE": "Belgium", "PL": "Poland",
    "ES": "Spain", "IT": "Italy", "CZ": "Czech Republic", "PT": "Portugal",
    "RO": "Romania", "GR": "Greece", "IE": "Ireland", "HU": "Hungary",
}


def calculate_co2_intensity(sources_gw: dict[str, float]) -> float:
    """Return weighted average CO₂ intensity in g/kWh given {raw_source_name: GW}."""
    total = sum(sources_gw.values())
    if total == 0:
        return 0.0
    weighted = sum(
        gw * EMISSION_FACTORS.get(src, 300.0)
        for src, gw in sources_gw.items()
    )
    return round(weighted / total, 1)


def map_generation_sources(raw: dict[str, float]) -> dict[str, float]:
    """Convert raw ENTSO-E source names to display names, merging where needed."""
    grouped: dict[str, float] = {}
    for raw_name, gw in raw.items():
        display = DISPLAY_MAP.get(raw_name, raw_name)
        grouped[display] = grouped.get(display, 0.0) + gw
    return dict(sorted(grouped.items(), key=lambda x: x[1], reverse=True))


class ENTSOClient:
    def __init__(self, api_key: str):
        self._client = EntsoePandasClient(api_key=api_key)

    def _now_window(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        end = pd.Timestamp.now(tz="UTC").floor("h")
        start = end - pd.Timedelta(hours=2)
        return start, end

    def _today_window(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        end = pd.Timestamp.now(tz="UTC").ceil("h")
        start = end.normalize()
        return start, end

    def get_generation(self, country: str) -> GenerationData:
        area = AREA_CODES[country]
        start, end = self._now_window()
        df = self._client.query_generation(area, start=start, end=end)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        latest = df.iloc[-1].dropna()
        raw: dict[str, float] = {
            col: float(latest[col]) / 1000.0
            for col in latest.index
            if isinstance(col, str) and latest[col] > 0
        }

        total_gw = sum(raw.values())
        renewable_gw = sum(v for k, v in raw.items() if k in RENEWABLE_SOURCES)
        renewable_pct = round((renewable_gw / total_gw * 100) if total_gw > 0 else 0.0, 1)
        co2 = calculate_co2_intensity(raw)
        sources = map_generation_sources(raw)

        return GenerationData(
            country=country,
            sources=sources,
            renewable_pct=renewable_pct,
            co2_intensity=co2,
            total_gw=round(total_gw, 2),
        )

    def get_prices(self, country: str) -> PriceData:
        area = AREA_CODES[country]
        start, end = self._today_window()
        series = self._client.query_day_ahead_prices(area, start=start, end=end)

        prices = [
            PricePoint(
                timestamp=ts.isoformat(),
                price_eur_mwh=round(float(val), 2),
            )
            for ts, val in series.items()
            if pd.notna(val)
        ]

        current = prices[-1].price_eur_mwh if prices else None

        yesterday_start = start - pd.Timedelta(days=1)
        try:
            y_series = self._client.query_day_ahead_prices(area, start=yesterday_start, end=start)
            yesterday_avg = float(y_series.mean())
            delta_pct = round(((current - yesterday_avg) / yesterday_avg) * 100, 1) if current and yesterday_avg else None
        except Exception:
            delta_pct = None

        return PriceData(country=country, prices=prices, current_eur_mwh=current, delta_pct=delta_pct)

    def get_flows(self, country: str) -> FlowData:
        area = AREA_CODES[country]
        start, end = self._now_window()
        neighbours = [c for c in AREA_CODES if c != country]
        flows: list[FlowItem] = []
        net_gw = 0.0

        for neighbour in neighbours:
            neighbour_area = AREA_CODES[neighbour]
            try:
                exp_series = self._client.query_crossborder_flows(area, neighbour_area, start=start, end=end)
                exp_gw = round(float(exp_series.iloc[-1]) / 1000.0, 2) if len(exp_series) else 0.0
                imp_series = self._client.query_crossborder_flows(neighbour_area, area, start=start, end=end)
                imp_gw = round(float(imp_series.iloc[-1]) / 1000.0, 2) if len(imp_series) else 0.0
                net = exp_gw - imp_gw
                if abs(net) > 0.05:
                    direction = "export" if net > 0 else "import"
                    flows.append(FlowItem(
                        partner=COUNTRY_NAMES.get(neighbour, neighbour),
                        flow_gw=round(abs(net), 2),
                        direction=direction,
                    ))
                    net_gw += net
            except Exception:
                continue

        flows.sort(key=lambda f: f.flow_gw, reverse=True)
        return FlowData(country=country, flows=flows[:6], net_gw=round(net_gw, 2))

    def get_overview(self) -> list[CountryOverview]:
        result: list[CountryOverview] = []
        for country in AREA_CODES:
            try:
                gen = self.get_generation(country)
                price_data = self.get_prices(country)
                result.append(CountryOverview(
                    country=country,
                    name=COUNTRY_NAMES.get(country, country),
                    co2_intensity=gen.co2_intensity,
                    renewable_pct=gen.renewable_pct,
                    price_eur_mwh=price_data.current_eur_mwh,
                ))
            except Exception:
                continue
        return result


def get_entso_client() -> ENTSOClient:
    api_key = os.environ.get("ENTSO_API_KEY", "")
    return ENTSOClient(api_key=api_key)
