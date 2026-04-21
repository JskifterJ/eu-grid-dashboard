"""
Compute-siting simulator. Pure arithmetic over forecast × scoring.
See spec §7.
"""
from dataclasses import dataclass
from typing import Literal, Optional

from app.geo import latency_penalty
from app.models import ForecastSeries, SimulationResult
from app.scoring import CSSResult, CountryMetrics


Workload = Literal["training", "inference"]


@dataclass
class SimulatorInputs:
    workload: Workload
    country: str
    mw: float
    hours: float
    start: str
    hub_country: str
    serving_region: Optional[str]


def _metric(country: str, grid: list[CountryMetrics]) -> CountryMetrics:
    for m in grid:
        if m.country == country:
            return m
    raise KeyError(country)


def _css_for(country: str, results: list[CSSResult]) -> float:
    for r in results:
        if r.country == country:
            return r.css
    raise KeyError(country)


def _percentile(country: str, results: list[CSSResult], penalty: float) -> int:
    target = _css_for(country, results) * (1 - penalty)
    below = sum(1 for r in results if r.css * (1 - penalty) < target)
    return round(100 * below / len(results))


def simulate(
    inputs: SimulatorInputs,
    metrics_grid: list[CountryMetrics],
    forecast: ForecastSeries,
    css_results: list[CSSResult],
) -> SimulationResult:
    m = _metric(inputs.country, metrics_grid)
    hub = _metric(inputs.hub_country, metrics_grid)

    # Resolve current-hour intensity from forecast (if a matching point exists),
    # falling back to the static grid metric when the forecast doesn't cover start.
    current_point = next(
        (p for p in forecast.points if p.timestamp == inputs.start), None
    )
    current_co2 = current_point.co2_g_per_kwh if current_point else m.co2_g_per_kwh
    current_price = current_point.price_eur_mwh if current_point else m.price_eur_mwh

    # Current-hour
    current_t = round(inputs.mw * inputs.hours * current_co2 / 1000.0, 3)
    current_eur = round(inputs.mw * inputs.hours * current_price, 2)
    hub_t = round(inputs.mw * inputs.hours * hub.co2_g_per_kwh / 1000.0, 3)
    hub_eur = round(inputs.mw * inputs.hours * hub.price_eur_mwh, 2)

    # Best hour (training only; inference is continuous)
    best_t: Optional[float] = None
    best_eur: Optional[float] = None
    best_start: Optional[str] = None

    if inputs.workload == "training" and forecast.points:
        best = min(forecast.points, key=lambda p: p.co2_g_per_kwh)
        best_t = round(inputs.mw * inputs.hours * best.co2_g_per_kwh / 1000.0, 3)
        best_eur = round(inputs.mw * inputs.hours * best.price_eur_mwh, 2)
        best_start = best.timestamp

    # Latency penalty (inference only)
    penalty = 0.0
    if inputs.workload == "inference" and inputs.serving_region:
        penalty = latency_penalty(inputs.country, inputs.serving_region)

    percentile = _percentile(inputs.country, css_results, penalty)

    return SimulationResult(
        workload=inputs.workload,
        country=inputs.country,
        mw=inputs.mw,
        hours=inputs.hours,
        start=inputs.start,
        current_hour_t_co2=current_t,
        current_hour_cost_eur=current_eur,
        best_hour_t_co2=best_t,
        best_hour_cost_eur=best_eur,
        best_hour_start=best_start,
        hub_country=inputs.hub_country,
        hub_t_co2=hub_t,
        hub_cost_eur=hub_eur,
        css_percentile=percentile,
        latency_penalty=penalty,
    )
