"""
Forecasting for CO₂ intensity and prices. Two production sources:
  1. Market forecast — ENTSO-E publishes day-ahead prices and generation-by-source forecasts.
  2. Seasonal baseline — same-hour-same-weekday mean over last 4 weeks (eval benchmark only).

See spec §6. Production market_forecast/seasonal_baseline queries are thin
wrappers around entsoe-py; see forecast.py:market_forecast below. This module
keeps the pure math (MAPE, seasonal averaging) testable in isolation.
"""
import os
from typing import Optional

import pandas as pd
from entsoe import EntsoePandasClient

from app.entso import (
    zones_for, EMISSION_FACTORS, calculate_co2_intensity, RENEWABLE_SOURCES,
)
from app.models import ForecastPoint, ForecastSeries


def mape(actual: list[float], predicted: list[float]) -> float:
    """Mean absolute percentage error. Skips points where actual == 0."""
    if len(actual) != len(predicted):
        raise ValueError(f"length mismatch: {len(actual)} vs {len(predicted)}")
    pairs = [(a, p) for a, p in zip(actual, predicted) if a != 0]
    if not pairs:
        raise ValueError("no non-zero actual values for MAPE")
    errors = [abs(p - a) / abs(a) for a, p in pairs]
    return round(100.0 * sum(errors) / len(errors), 3)


def seasonal_baseline_values(history: dict[tuple[int, int], list[float]]) -> dict[tuple[int, int], float]:
    """Given {(weekday, hour): [prior_values]} return {(weekday, hour): mean}."""
    return {
        key: round(sum(vals) / len(vals), 3) if vals else 0.0
        for key, vals in history.items()
    }


class ForecastClient:
    def __init__(self, api_key: str):
        self._client = EntsoePandasClient(api_key=api_key)

    def _tomorrow_window(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        now = pd.Timestamp.now(tz="UTC").ceil("h")
        end = now + pd.Timedelta(hours=24)
        return now, end

    def market_forecast(self, country: str) -> ForecastSeries:
        """
        Returns 24h-ahead hourly CO₂ + price forecast.
        Price = ENTSO day-ahead auction.
        CO₂ = ENTSO day-ahead generation-forecast-by-source × emission factors.
        Falls back silently where the forecast query is empty for a zone.
        """
        zones = zones_for(country)
        start, end = self._tomorrow_window()

        # Prices (average across zones per hour)
        price_by_ts: dict[str, list[float]] = {}
        for z in zones:
            try:
                s = self._client.query_day_ahead_prices(z, start=start, end=end)
                for ts, val in s.items():
                    if pd.notna(val):
                        price_by_ts.setdefault(ts.isoformat(), []).append(float(val))
            except Exception:
                continue

        # Generation forecast → CO₂ intensity per hour
        co2_by_ts: dict[str, float] = {}
        for ts_iso in price_by_ts:
            co2_by_ts[ts_iso] = 0.0  # filled below if data available

        agg_gen_by_ts: dict[str, dict[str, float]] = {}
        for z in zones:
            try:
                df = self._client.query_generation_forecast(z, start=start, end=end)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                for ts, row in df.iterrows():
                    ts_iso = ts.isoformat()
                    bucket = agg_gen_by_ts.setdefault(ts_iso, {})
                    for col, val in row.items():
                        if isinstance(col, str) and pd.notna(val) and val > 0:
                            bucket[col] = bucket.get(col, 0.0) + float(val) / 1000.0
            except Exception:
                continue

        for ts_iso, sources in agg_gen_by_ts.items():
            co2_by_ts[ts_iso] = calculate_co2_intensity(sources)

        points: list[ForecastPoint] = []
        for ts_iso in sorted(set(list(price_by_ts.keys()) + list(co2_by_ts.keys()))):
            prices = price_by_ts.get(ts_iso, [])
            price = round(sum(prices) / len(prices), 2) if prices else 0.0
            co2 = co2_by_ts.get(ts_iso, 0.0)
            points.append(ForecastPoint(timestamp=ts_iso, co2_g_per_kwh=co2, price_eur_mwh=price))

        return ForecastSeries(country=country, points=points, source="market")


def get_forecast_client() -> Optional[ForecastClient]:
    key = os.environ.get("ENTSO_API_KEY", "").strip()
    return ForecastClient(api_key=key) if key else None
