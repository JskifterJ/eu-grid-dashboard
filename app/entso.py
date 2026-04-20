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

AREA_CODES: dict[str, list[str]] = {
    "DE": ["DE_LU"],
    "FR": ["FR"],
    "GB": ["GB"],
    "NO": ["NO_1", "NO_2", "NO_3", "NO_4", "NO_5"],
    "SE": ["SE_1", "SE_2", "SE_3", "SE_4"],
    "DK": ["DK_1", "DK_2"],
    "FI": ["FI"],
    "CH": ["CH"],
    "AT": ["AT"],
    "NL": ["NL"],
    "BE": ["BE"],
    "PL": ["PL"],
    "ES": ["ES"],
    "IT": ["IT_NORD", "IT_CNOR", "IT_CSUD", "IT_SUD", "IT_SICI", "IT_SARD"],
    "CZ": ["CZ"],
    "PT": ["PT"],
    "RO": ["RO"],
    "GR": ["GR"],
    "IE": ["IE_SEM"],
    "HU": ["HU"],
}


def zones_for(country: str) -> list[str]:
    return AREA_CODES[country]

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
        zones = zones_for(country)
        start, end = self._now_window()
        combined_raw: dict[str, float] = {}
        for z in zones:
            try:
                df = self._client.query_generation(z, start=start, end=end)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                latest = df.iloc[-1].dropna()
                for col in latest.index:
                    if isinstance(col, str) and latest[col] > 0:
                        combined_raw[col] = combined_raw.get(col, 0.0) + float(latest[col]) / 1000.0
            except Exception:
                continue

        total_gw = sum(combined_raw.values())
        renewable_gw = sum(v for k, v in combined_raw.items() if k in RENEWABLE_SOURCES)
        renewable_pct = round((renewable_gw / total_gw * 100) if total_gw > 0 else 0.0, 1)
        co2 = calculate_co2_intensity(combined_raw)
        sources = map_generation_sources(combined_raw)

        return GenerationData(
            country=country,
            sources=sources,
            renewable_pct=renewable_pct,
            co2_intensity=co2,
            total_gw=round(total_gw, 2),
        )

    def get_prices(self, country: str) -> PriceData:
        zones = zones_for(country)
        start, end = self._today_window()

        prices_by_ts: dict[str, list[float]] = {}
        for z in zones:
            try:
                series = self._client.query_day_ahead_prices(z, start=start, end=end)
                for ts, val in series.items():
                    if pd.notna(val):
                        prices_by_ts.setdefault(ts.isoformat(), []).append(float(val))
            except Exception:
                continue

        prices = [
            PricePoint(timestamp=ts, price_eur_mwh=round(sum(vals) / len(vals), 2))
            for ts, vals in sorted(prices_by_ts.items())
        ]
        current = prices[-1].price_eur_mwh if prices else None

        yesterday_start = start - pd.Timedelta(days=1)
        yest_vals: list[float] = []
        for z in zones:
            try:
                y_series = self._client.query_day_ahead_prices(z, start=yesterday_start, end=start)
                yest_vals.extend(float(v) for v in y_series if pd.notna(v))
            except Exception:
                continue
        yesterday_avg = sum(yest_vals) / len(yest_vals) if yest_vals else None
        delta_pct = (
            round(((current - yesterday_avg) / yesterday_avg) * 100, 1)
            if current is not None and yesterday_avg else None
        )

        return PriceData(country=country, prices=prices, current_eur_mwh=current, delta_pct=delta_pct)

    def get_flows(self, country: str) -> FlowData:
        # Multi-zone flow aggregation is lossy — for the scope of this step we
        # query only the primary zone (first in the list) and footnote this
        # caveat in the methodology. Upgrading to proper per-zone aggregation
        # is tracked in Plan B step 4.
        area = zones_for(country)[0]
        start, end = self._now_window()
        other_countries = [c for c in AREA_CODES if c != country]
        flows: list[FlowItem] = []
        net_gw = 0.0
        for neighbour in other_countries:
            n_area = zones_for(neighbour)[0]
            try:
                exp_series = self._client.query_crossborder_flows(area, n_area, start=start, end=end)
                exp_gw = round(float(exp_series.iloc[-1]) / 1000.0, 2) if len(exp_series) else 0.0
                imp_series = self._client.query_crossborder_flows(n_area, area, start=start, end=end)
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
