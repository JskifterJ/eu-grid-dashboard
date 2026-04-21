"""
Pure-function Compute Siting Score. No I/O. See spec §5.

CSS(c) = Σ w_d × normalized_d(c)  where Σ w = 100, each score ∈ [0, 100].
Dimensions where lower is better are flipped during normalization.
"""
from dataclasses import dataclass
from typing import Optional


Weights = dict[str, int]

DEFAULT_WEIGHTS: Weights = {"carbon": 40, "cost": 30, "renewable": 20, "stability": 10}

# EU ETS spot ~€75/tCO2 as of 2026-04. Configurable per-request.
DEFAULT_CARBON_PRICE_EUR_PER_TCO2 = 75.0


def carbon_internalized_price(market_price_eur_mwh: float, co2_g_per_kwh: float, carbon_price_eur_per_tco2: float) -> float:
    """
    Add the social cost of carbon to the market electricity price.

    €/MWh added = (g/kWh) × (€/t) × (1 t / 1_000_000 g) × (1000 kWh / MWh)
                = (g/kWh) × (€/t) / 1000

    Returns the effective €/MWh.
    """
    return market_price_eur_mwh + co2_g_per_kwh * carbon_price_eur_per_tco2 / 1000.0
PRESET_GREEN: Weights = {"carbon": 60, "cost": 15, "renewable": 20, "stability": 5}
PRESET_COST: Weights = {"carbon": 10, "cost": 60, "renewable": 15, "stability": 15}

# Workload presets — distinct from user-facing weight presets. These baseline
# weights reflect how siting concerns differ per workload type.
WORKLOAD_PRESETS: dict[str, Weights] = {
    "training":    {"carbon": 40, "cost": 30, "renewable": 20, "stability": 10},
    "fine-tuning": {"carbon": 30, "cost": 40, "renewable": 20, "stability": 10},
    "inference":   {"carbon": 20, "cost": 45, "renewable": 15, "stability": 20},
}


def weights_for_workload(workload: str) -> Weights:
    if workload not in WORKLOAD_PRESETS:
        raise KeyError(f"unknown workload {workload!r}; expected one of {set(WORKLOAD_PRESETS)}")
    return dict(WORKLOAD_PRESETS[workload])


@dataclass
class CountryMetrics:
    country: str
    co2_g_per_kwh: float
    price_eur_mwh: float
    renewable_pct: float
    price_sigma_eur_mwh: float


@dataclass
class CSSResult:
    country: str
    css: float
    carbon_score: float
    cost_score: float
    renewable_score: float
    stability_score: float


def _validate_weights(w: Weights) -> None:
    expected = {"carbon", "cost", "renewable", "stability"}
    if set(w.keys()) != expected:
        raise ValueError(f"weights must have exactly keys {expected}, got {set(w.keys())}")
    if sum(w.values()) != 100:
        raise ValueError(f"weights must sum to 100, got {sum(w.values())}")


def _normalize(values: list[float], lower_is_better: bool) -> list[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [50.0] * len(values)
    if lower_is_better:
        return [100.0 * (hi - v) / (hi - lo) for v in values]
    return [100.0 * (v - lo) / (hi - lo) for v in values]


def compute_css(metrics: list[CountryMetrics], weights: Weights) -> list[CSSResult]:
    _validate_weights(weights)
    if not metrics:
        return []
    carbon = _normalize([m.co2_g_per_kwh for m in metrics], lower_is_better=True)
    cost = _normalize([m.price_eur_mwh for m in metrics], lower_is_better=True)
    renew = _normalize([m.renewable_pct for m in metrics], lower_is_better=False)
    stab = _normalize([m.price_sigma_eur_mwh for m in metrics], lower_is_better=True)

    out: list[CSSResult] = []
    for i, m in enumerate(metrics):
        css = (
            weights["carbon"] / 100 * carbon[i]
            + weights["cost"] / 100 * cost[i]
            + weights["renewable"] / 100 * renew[i]
            + weights["stability"] / 100 * stab[i]
        )
        out.append(CSSResult(
            country=m.country,
            css=round(css, 2),
            carbon_score=round(carbon[i], 2),
            cost_score=round(cost[i], 2),
            renewable_score=round(renew[i], 2),
            stability_score=round(stab[i], 2),
        ))
    return out


def rank_countries(results: list[CSSResult]) -> list[CSSResult]:
    return sorted(results, key=lambda r: r.css, reverse=True)


def apply_per_country_latency_penalty(
    results: list[CSSResult],
    region: Optional[str],
) -> list[CSSResult]:
    """For each country, multiply its CSS by (1 - latency_penalty(country, region))."""
    if region is None:
        return results
    from app.geo import latency_penalty  # lazy to avoid any cyclic-import risk
    out: list[CSSResult] = []
    for r in results:
        try:
            penalty = latency_penalty(r.country, region)
        except KeyError:
            penalty = 0.0
        out.append(CSSResult(
            country=r.country,
            css=round(r.css * (1 - penalty), 2),
            carbon_score=r.carbon_score,
            cost_score=r.cost_score,
            renewable_score=r.renewable_score,
            stability_score=r.stability_score,
        ))
    return out
