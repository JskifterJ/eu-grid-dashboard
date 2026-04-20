"""
Pure-function Compute Siting Score. No I/O. See spec §5.

CSS(c) = Σ w_d × normalized_d(c)  where Σ w = 100, each score ∈ [0, 100].
Dimensions where lower is better are flipped during normalization.
"""
from dataclasses import dataclass


Weights = dict[str, int]

DEFAULT_WEIGHTS: Weights = {"carbon": 40, "cost": 30, "renewable": 20, "stability": 10}
PRESET_GREEN: Weights = {"carbon": 60, "cost": 15, "renewable": 20, "stability": 5}
PRESET_COST: Weights = {"carbon": 10, "cost": 60, "renewable": 15, "stability": 15}


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
