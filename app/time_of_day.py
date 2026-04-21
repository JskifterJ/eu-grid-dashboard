"""
Time-of-day optimization for workload scheduling.

Given a 24h ForecastSeries and a workload duration, find the optimal
contiguous window to run to minimize CO₂ (or cost).
"""
import math
from typing import Literal

from app.models import (
    ForecastSeries, ForecastPoint,
    TimeOfDayHour, TimeOfDayWindow, TimeOfDayResult,
)


Mode = Literal["min", "max"]


def best_contiguous_window(
    points: list[ForecastPoint],
    window_hours: float,
    mode: Mode = "min",
) -> tuple[int, float, float]:
    """Return (start_index, avg_co2, avg_price) of the best window.

    window_hours is rounded up to the nearest integer hour. mode='min' for
    lowest average CO₂ (best for carbon); 'max' for highest (worst case).
    """
    if not points:
        raise ValueError("empty forecast")
    w = max(1, math.ceil(window_hours))
    if w > len(points):
        raise ValueError(f"workload window {w}h exceeds forecast length {len(points)}h")

    best_idx = 0
    best_avg_co2 = None
    best_avg_price = 0.0

    for i in range(len(points) - w + 1):
        window = points[i:i + w]
        avg_co2 = sum(p.co2_g_per_kwh for p in window) / w
        avg_price = sum(p.price_eur_mwh for p in window) / w
        if best_avg_co2 is None or (mode == "min" and avg_co2 < best_avg_co2) or (mode == "max" and avg_co2 > best_avg_co2):
            best_avg_co2 = avg_co2
            best_avg_price = avg_price
            best_idx = i

    return best_idx, float(best_avg_co2), best_avg_price


def build_schedule(
    forecast: ForecastSeries,
    mw: float,
    workload_hours: float,
) -> TimeOfDayResult:
    """Full schedule analysis: timeline + best/worst windows + savings delta."""
    if not forecast.points:
        raise ValueError("empty forecast")
    if workload_hours > len(forecast.points):
        raise ValueError(f"workload {workload_hours}h exceeds forecast length {len(forecast.points)}h")

    w = max(1, math.ceil(workload_hours))

    best_idx, best_avg_co2, best_avg_price = best_contiguous_window(forecast.points, workload_hours, mode="min")
    worst_idx, worst_avg_co2, worst_avg_price = best_contiguous_window(forecast.points, workload_hours, mode="max")

    def _window(start_idx: int, avg_co2: float, avg_price: float) -> TimeOfDayWindow:
        end_idx = min(len(forecast.points) - 1, start_idx + w - 1)
        total_co2_kg = mw * workload_hours * avg_co2       # kg CO₂ (see unit notes in lca.py)
        total_cost_eur = mw * workload_hours * avg_price
        return TimeOfDayWindow(
            start=forecast.points[start_idx].timestamp,
            end=forecast.points[end_idx].timestamp,
            avg_co2_g_per_kwh=round(avg_co2, 2),
            avg_price_eur_mwh=round(avg_price, 2),
            total_co2_kg=round(total_co2_kg, 2),
            total_cost_eur=round(total_cost_eur, 2),
        )

    best = _window(best_idx, best_avg_co2, best_avg_price)
    worst = _window(worst_idx, worst_avg_co2, worst_avg_price)

    # Savings % relative to worst case (so: "worst − best" is the gain from scheduling)
    co2_savings_pct = ((worst.avg_co2_g_per_kwh - best.avg_co2_g_per_kwh) / worst.avg_co2_g_per_kwh * 100) if worst.avg_co2_g_per_kwh > 0 else 0.0
    cost_savings_pct = ((worst.avg_price_eur_mwh - best.avg_price_eur_mwh) / worst.avg_price_eur_mwh * 100) if worst.avg_price_eur_mwh > 0 else 0.0
    co2_savings_kg = worst.total_co2_kg - best.total_co2_kg
    cost_savings_eur = worst.total_cost_eur - best.total_cost_eur

    return TimeOfDayResult(
        country=forecast.country,
        workload_mw=mw,
        workload_hours=workload_hours,
        hours=[TimeOfDayHour(timestamp=p.timestamp, co2_g_per_kwh=p.co2_g_per_kwh, price_eur_mwh=p.price_eur_mwh) for p in forecast.points],
        best_window=best,
        worst_window=worst,
        co2_savings_pct=round(co2_savings_pct, 2),
        cost_savings_pct=round(cost_savings_pct, 2),
        co2_savings_kg=round(co2_savings_kg, 2),
        cost_savings_eur=round(cost_savings_eur, 2),
    )
