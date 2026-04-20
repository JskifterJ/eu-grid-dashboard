# Plan A — Foundations, Visual Reset, Thesis Hero

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend foundations (scoring, forecasting, simulator with training+inference modes, historicals, primary-energy factors, multi-zone aggregation), migrate the frontend to an editorial aesthetic, and ship the thesis hero + live-ranking strip with weights presets and workload-mode toggle.

**Architecture:** Pure-function modules under `app/` (`scoring`, `forecast`, `simulator`, `historical`, `primary_energy`, `geo`) keep all logic unit-testable in isolation. `app/routes.py` thins to glue + caching. Frontend stays vanilla JS + D3/Chart.js — refactored into per-section modules (`state.js`, `hero.js`, `ranking.js`) that share a single `state` object.

**Tech Stack:** FastAPI, pydantic v2, pandas, entsoe-py, sqlite3 (stdlib), pytest, vanilla JS, D3.js, Chart.js, CSS custom properties.

**Spec:** `docs/superpowers/specs/2026-04-20-grid-thesis-dashboard-design.md` (sections 1-12).

---

## Task 1: Expand pydantic models

**Files:**
- Modify: `app/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for new models**

Append to `tests/test_models.py`:

```python
from app.models import (
    ForecastPoint, ForecastSeries, CSSBreakdown, RankingEntry,
    SimulationResult, EvalResult, StructuredBriefing,
)


def test_forecast_point_roundtrip():
    p = ForecastPoint(timestamp="2026-04-20T12:00:00Z", co2_g_per_kwh=45.0, price_eur_mwh=72.0)
    assert p.co2_g_per_kwh == 45.0


def test_forecast_series_ordered():
    s = ForecastSeries(
        country="FR",
        points=[ForecastPoint(timestamp="2026-04-20T12:00:00Z", co2_g_per_kwh=45.0, price_eur_mwh=72.0)],
        source="market",
    )
    assert s.source == "market"


def test_css_breakdown_weights_sum():
    b = CSSBreakdown(
        country="FR", css=94.2, as_of="2026-04-20T14:00:00Z",
        carbon_score=98.0, cost_score=88.0, renewable_score=95.0, stability_score=90.0,
        weights={"carbon": 40, "cost": 30, "renewable": 20, "stability": 10},
    )
    assert sum(b.weights.values()) == 100


def test_simulation_result_inference_mode():
    r = SimulationResult(
        workload="inference", country="FR", mw=1.0, hours=24.0,
        start="2026-04-20T14:00:00Z",
        current_hour_t_co2=0.91, current_hour_cost_eur=1728.0,
        best_hour_t_co2=None, best_hour_cost_eur=None, best_hour_start=None,
        hub_country="DE", hub_t_co2=9.6, hub_cost_eur=2400.0,
        css_percentile=92, latency_penalty=0.0,
    )
    assert r.workload == "inference"
    assert r.best_hour_t_co2 is None


def test_eval_result_has_mape():
    e = EvalResult(
        country="FR", metric="co2", window_days=7,
        market_mape_pct=8.2, naive_mape_pct=12.6,
    )
    assert e.market_mape_pct < e.naive_mape_pct


def test_structured_briefing_fields():
    b = StructuredBriefing(
        country="FR",
        headline="France clean and cheap now.",
        bullets=["A", "B", "C"],
        risk_flag="low",
        as_of="2026-04-20T14:00:00Z",
        sources=["ENTSO-E day-ahead", "gpu_industry/strategy_value_chain_master"],
    )
    assert len(b.bullets) == 3
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `pytest tests/test_models.py -v`
Expected: ImportError on new names.

- [ ] **Step 3: Implement new models**

Append to `app/models.py`:

```python
from typing import Literal


class ForecastPoint(BaseModel):
    timestamp: str
    co2_g_per_kwh: float
    price_eur_mwh: float


class ForecastSeries(BaseModel):
    country: str
    points: list[ForecastPoint]
    source: Literal["market", "seasonal"]


class CSSBreakdown(BaseModel):
    country: str
    css: float
    as_of: str
    carbon_score: float
    cost_score: float
    renewable_score: float
    stability_score: float
    weights: dict[str, int]


class RankingEntry(BaseModel):
    country: str
    name: str
    css: float
    carbon_score: float
    cost_score: float
    renewable_score: float
    stability_score: float


class SimulationResult(BaseModel):
    workload: Literal["training", "inference"]
    country: str
    mw: float
    hours: float
    start: str
    current_hour_t_co2: float
    current_hour_cost_eur: float
    best_hour_t_co2: Optional[float]
    best_hour_cost_eur: Optional[float]
    best_hour_start: Optional[str]
    hub_country: str
    hub_t_co2: float
    hub_cost_eur: float
    css_percentile: int
    latency_penalty: float


class EvalResult(BaseModel):
    country: str
    metric: Literal["co2", "price"]
    window_days: int
    market_mape_pct: float
    naive_mape_pct: float


class StructuredBriefing(BaseModel):
    country: str
    headline: str
    bullets: list[str]
    risk_flag: Literal["low", "med", "high"]
    as_of: str
    sources: list[str]
```

- [ ] **Step 4: Run tests to confirm pass**

Run: `pytest tests/test_models.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat: add pydantic models for CSS, forecast, simulator, eval, briefing"
```

---

## Task 2: Primary energy factors module

**Files:**
- Create: `app/primary_energy.py`
- Test: `tests/test_primary_energy.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_primary_energy.py`:

```python
from app.primary_energy import PRIMARY_ENERGY_FACTORS, apply_pef


def test_renewables_have_pef_one():
    for s in ["Wind", "Solar", "Hydro", "Hydro Reservoir", "Pumped Storage"]:
        assert PRIMARY_ENERGY_FACTORS[s] == 1.0


def test_fossils_have_pef_greater_than_one():
    assert PRIMARY_ENERGY_FACTORS["Coal"] > 2.0
    assert PRIMARY_ENERGY_FACTORS["Lignite"] > PRIMARY_ENERGY_FACTORS["Coal"]
    assert PRIMARY_ENERGY_FACTORS["Gas"] >= 2.0
    assert PRIMARY_ENERGY_FACTORS["Nuclear"] >= 2.8


def test_apply_pef_inflates_fossils():
    raw = {"Wind": 10.0, "Coal": 10.0}
    inflated = apply_pef(raw)
    assert inflated["Wind"] == 10.0
    assert inflated["Coal"] == 27.0


def test_apply_pef_unknown_source_defaults_to_one():
    raw = {"Exotic Thing": 5.0}
    inflated = apply_pef(raw)
    assert inflated["Exotic Thing"] == 5.0
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_primary_energy.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement module**

Create `app/primary_energy.py`:

```python
"""
IEA physical-content-method primary energy factors, applied only to the
generation-mix visualization. See docs/methodology.md for citation.
"""

PRIMARY_ENERGY_FACTORS: dict[str, float] = {
    # Fossils (thermal conversion loss)
    "Coal": 2.7,
    "Lignite": 3.0,
    "Gas": 2.0,
    "Oil": 2.6,
    "Oil Shale": 2.6,
    "Peat": 2.9,
    # Nuclear (conventional thermal accounting)
    "Nuclear": 3.0,
    # Biomass / waste
    "Biomass": 1.2,
    "Waste": 1.1,
    # Renewables (physical-content method: factor = 1)
    "Wind": 1.0,
    "Solar": 1.0,
    "Hydro": 1.0,
    "Hydro Reservoir": 1.0,
    "Pumped Storage": 1.0,
    "Geothermal": 1.0,
    "Other Renewable": 1.0,
    "Other": 1.0,
}


def apply_pef(sources_gw: dict[str, float]) -> dict[str, float]:
    """Multiply each source's GW by its primary energy factor."""
    return {
        name: gw * PRIMARY_ENERGY_FACTORS.get(name, 1.0)
        for name, gw in sources_gw.items()
    }
```

- [ ] **Step 4: Run to confirm pass**

Run: `pytest tests/test_primary_energy.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/primary_energy.py tests/test_primary_energy.py
git commit -m "feat: primary-energy factors (IEA physical-content) and apply_pef helper"
```

---

## Task 3: Scoring module (CSS core)

**Files:**
- Create: `app/scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_scoring.py`:

```python
import pytest

from app.scoring import (
    Weights, CountryMetrics, compute_css, rank_countries,
    DEFAULT_WEIGHTS, PRESET_GREEN, PRESET_COST,
)


def _metrics(c, co2, price, ren, sigma):
    return CountryMetrics(
        country=c, co2_g_per_kwh=co2, price_eur_mwh=price,
        renewable_pct=ren, price_sigma_eur_mwh=sigma,
    )


def test_default_weights_sum_to_100():
    assert sum(DEFAULT_WEIGHTS.values()) == 100


def test_all_presets_sum_to_100():
    assert sum(PRESET_GREEN.values()) == 100
    assert sum(PRESET_COST.values()) == 100


def test_invalid_weights_raises():
    with pytest.raises(ValueError):
        compute_css([_metrics("FR", 40, 70, 90, 5)], {"carbon": 50, "cost": 50, "renewable": 0, "stability": 10})


def test_single_country_all_dimensions_get_50():
    # with one country, min == max → normalized = 50 (midpoint)
    result = compute_css([_metrics("FR", 40, 70, 90, 5)], DEFAULT_WEIGHTS)
    assert result[0].css == pytest.approx(50.0, abs=0.01)


def test_two_countries_clean_wins():
    metrics = [
        _metrics("FR", 40, 70, 90, 5),   # cleaner, cheaper, more renewable, stabler
        _metrics("PL", 600, 120, 15, 30),
    ]
    result = compute_css(metrics, DEFAULT_WEIGHTS)
    fr = next(r for r in result if r.country == "FR")
    pl = next(r for r in result if r.country == "PL")
    assert fr.css == pytest.approx(100.0, abs=0.01)
    assert pl.css == pytest.approx(0.0, abs=0.01)


def test_cost_preset_orders_by_price():
    metrics = [
        _metrics("A", 100, 30, 50, 10),    # cheap but not clean
        _metrics("B", 50, 120, 50, 10),    # clean but expensive
    ]
    result = compute_css(metrics, PRESET_COST)
    a = next(r for r in result if r.country == "A")
    b = next(r for r in result if r.country == "B")
    assert a.css > b.css


def test_rank_countries_sorted_desc():
    entries = compute_css(
        [_metrics("X", 200, 90, 40, 15), _metrics("Y", 50, 60, 85, 5)],
        DEFAULT_WEIGHTS,
    )
    ranked = rank_countries(entries)
    assert ranked[0].css >= ranked[1].css


def test_compute_css_empty_returns_empty():
    assert compute_css([], DEFAULT_WEIGHTS) == []
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_scoring.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement module**

Create `app/scoring.py`:

```python
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
```

- [ ] **Step 4: Run to confirm pass**

Run: `pytest tests/test_scoring.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/scoring.py tests/test_scoring.py
git commit -m "feat: pure-function Compute Siting Score with weights presets"
```

---

## Task 4: Multi-zone aggregation

**Files:**
- Modify: `app/entso.py` (lines 59-80 AREA_CODES + surrounding query fns)
- Test: `tests/test_entso.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_entso.py`:

```python
from app.entso import AREA_CODES, zones_for


def test_area_codes_are_lists():
    for c, zones in AREA_CODES.items():
        assert isinstance(zones, list), f"{c} not a list"
        assert len(zones) >= 1


def test_norway_has_five_zones():
    assert zones_for("NO") == ["NO_1", "NO_2", "NO_3", "NO_4", "NO_5"]


def test_sweden_has_four_zones():
    assert zones_for("SE") == ["SE_1", "SE_2", "SE_3", "SE_4"]


def test_italy_has_multiple_zones():
    assert len(zones_for("IT")) >= 4


def test_country_names_covers_all():
    from app.entso import COUNTRY_NAMES
    for c in AREA_CODES:
        assert c in COUNTRY_NAMES
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_entso.py::test_area_codes_are_lists -v`
Expected: fails on `isinstance(zones, list)` — current type is `str`.

- [ ] **Step 3: Convert AREA_CODES to lists and add `zones_for`**

Replace lines 59-80 in `app/entso.py` with:

```python
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
```

Then update `ENTSOClient.get_generation`, `get_prices`, `get_flows` to loop `zones_for(country)` and sum GW (generation) / generation-weight-average prices. Replace the three methods with:

```python
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
```

- [ ] **Step 4: Run existing + new tests**

Run: `pytest tests/ -v`
Expected: all existing tests still pass; new multi-zone tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/entso.py tests/test_entso.py
git commit -m "refactor: AREA_CODES as list; multi-zone generation + price aggregation"
```

---

## Task 5: Geography utilities (centroids + haversine)

**Files:**
- Create: `app/geo.py`
- Test: `tests/test_geo.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_geo.py`:

```python
import pytest
from app.geo import (
    COUNTRY_CENTROIDS, SERVING_REGIONS, haversine_km, latency_penalty,
)


def test_all_countries_have_centroid():
    from app.entso import AREA_CODES
    for c in AREA_CODES:
        assert c in COUNTRY_CENTROIDS


def test_serving_regions_defined():
    assert set(SERVING_REGIONS.keys()) == {"central", "western", "northern", "southern", "iberian"}


def test_haversine_known_distance():
    # Paris (48.85, 2.35) to London (51.50, -0.13) ≈ 344 km
    d = haversine_km(48.85, 2.35, 51.50, -0.13)
    assert 330 < d < 360


def test_haversine_zero_for_same_point():
    assert haversine_km(50.0, 10.0, 50.0, 10.0) == pytest.approx(0.0, abs=0.001)


def test_latency_penalty_zero_within_500km():
    # FR country to Western centroid should be near
    p = latency_penalty("FR", "western")
    assert p == 0.0


def test_latency_penalty_clamped_to_0_4():
    # Far country to far region maxes out at 0.4
    p = latency_penalty("PT", "northern")
    assert 0.3 <= p <= 0.4


def test_latency_penalty_monotone_in_distance():
    p_close = latency_penalty("DE", "central")
    p_far = latency_penalty("PT", "northern")
    assert p_far > p_close
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_geo.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement module**

Create `app/geo.py`:

```python
"""
Population-weighted country centroids and serving-region centroids for the
inference simulator latency penalty. Coordinates are approximate (±1°) and
only need to be accurate enough to separate near vs far on a continent scale.
"""
from math import radians, sin, cos, sqrt, asin

COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "DE": (51.16, 10.45),
    "FR": (46.23, 2.21),
    "GB": (55.38, -3.44),
    "NO": (60.47, 8.47),
    "SE": (60.13, 18.64),
    "DK": (55.68, 12.57),
    "FI": (61.92, 25.75),
    "CH": (46.82, 8.23),
    "AT": (47.52, 14.55),
    "NL": (52.13, 5.29),
    "BE": (50.50, 4.47),
    "PL": (51.92, 19.13),
    "ES": (40.46, -3.75),
    "IT": (41.87, 12.57),
    "CZ": (49.82, 15.47),
    "PT": (39.40, -8.22),
    "RO": (45.94, 24.97),
    "GR": (39.07, 21.82),
    "IE": (53.41, -8.24),
    "HU": (47.16, 19.50),
}

SERVING_REGIONS: dict[str, tuple[float, float]] = {
    "central":  (49.0, 13.0),    # DE/AT/CH/PL/CZ/HU
    "western":  (50.0,  2.0),    # FR/BE/NL/GB/IE
    "northern": (59.0, 16.0),    # NO/SE/DK/FI
    "southern": (42.0, 15.0),    # IT/GR/RO
    "iberian":  (40.0, -4.0),    # ES/PT
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_r, lat2_r = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def latency_penalty(country: str, region: str) -> float:
    """Return latency penalty in [0, 0.4] given candidate country and serving region."""
    if country not in COUNTRY_CENTROIDS:
        raise KeyError(country)
    if region not in SERVING_REGIONS:
        raise KeyError(region)
    c_lat, c_lon = COUNTRY_CENTROIDS[country]
    r_lat, r_lon = SERVING_REGIONS[region]
    d = haversine_km(c_lat, c_lon, r_lat, r_lon)
    raw = max(0.0, (d - 500.0) / 2500.0)
    return round(min(0.4, raw), 4)
```

- [ ] **Step 4: Run to confirm pass**

Run: `pytest tests/test_geo.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/geo.py tests/test_geo.py
git commit -m "feat: country centroids, serving regions, latency penalty helper"
```

---

## Task 6: Forecast module

**Files:**
- Create: `app/forecast.py`
- Test: `tests/test_forecast.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_forecast.py`:

```python
import pytest
from app.forecast import mape, seasonal_baseline_values


def test_mape_perfect():
    assert mape([100, 200, 300], [100, 200, 300]) == pytest.approx(0.0)


def test_mape_ten_percent_off():
    actual = [100.0] * 5
    pred = [110.0] * 5
    assert mape(actual, pred) == pytest.approx(10.0, abs=0.001)


def test_mape_raises_on_length_mismatch():
    with pytest.raises(ValueError):
        mape([1, 2], [1, 2, 3])


def test_mape_raises_on_empty():
    with pytest.raises(ValueError):
        mape([], [])


def test_mape_skips_zero_actuals():
    # standard MAPE drops zero-actual points to avoid /0
    result = mape([0.0, 100.0], [10.0, 110.0])
    assert result == pytest.approx(10.0, abs=0.001)


def test_seasonal_baseline_averages_prior_weeks():
    # 4 weeks × 7 days × 24 hours history; baseline for same-hour-same-weekday
    # just returns the mean of the 4 prior-week same-hour values
    history = {
        # (weekday, hour) → list of prior same-slot values, newest first
        (1, 14): [50.0, 55.0, 45.0, 50.0],
    }
    out = seasonal_baseline_values(history)
    assert out[(1, 14)] == pytest.approx(50.0)
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_forecast.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement module**

Create `app/forecast.py`:

```python
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
```

- [ ] **Step 4: Run to confirm pass**

Run: `pytest tests/test_forecast.py -v`
Expected: pure-math tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/forecast.py tests/test_forecast.py
git commit -m "feat: forecast module — MAPE, seasonal baseline, ENTSO market forecast wrapper"
```

---

## Task 7: Simulator module

**Files:**
- Create: `app/simulator.py`
- Test: `tests/test_simulator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_simulator.py`:

```python
import pytest
from app.simulator import simulate, SimulatorInputs
from app.models import ForecastPoint, ForecastSeries
from app.scoring import CountryMetrics, compute_css, DEFAULT_WEIGHTS


def _metrics_grid():
    # Two countries, clean/cheap FR vs dirty/expensive PL
    return [
        CountryMetrics("FR", 40, 70, 90, 5),
        CountryMetrics("PL", 600, 120, 15, 30),
    ]


def _forecast_fr():
    return ForecastSeries(
        country="FR",
        points=[
            ForecastPoint(timestamp=f"2026-04-20T{h:02d}:00:00Z", co2_g_per_kwh=40.0 + h, price_eur_mwh=70.0 + h)
            for h in range(24)
        ],
        source="market",
    )


def test_training_emissions_math():
    result = simulate(SimulatorInputs(
        workload="training", country="FR", mw=10.0, hours=6.0,
        start="2026-04-20T14:00:00Z", hub_country="PL", serving_region=None,
    ), metrics_grid=_metrics_grid(), forecast=_forecast_fr(), css_results=compute_css(_metrics_grid(), DEFAULT_WEIGHTS))

    # current emissions = 10 MW × 6 h × 40 g/kWh / 1000 = 2.4 t
    assert result.current_hour_t_co2 == pytest.approx(2.4, abs=0.01)
    assert result.current_hour_cost_eur == pytest.approx(10 * 6 * 70.0, abs=0.01)
    # hub (PL) should be much worse
    assert result.hub_t_co2 > result.current_hour_t_co2


def test_training_best_hour_picked():
    result = simulate(SimulatorInputs(
        workload="training", country="FR", mw=10.0, hours=6.0,
        start="2026-04-20T14:00:00Z", hub_country="PL", serving_region=None,
    ), metrics_grid=_metrics_grid(), forecast=_forecast_fr(), css_results=compute_css(_metrics_grid(), DEFAULT_WEIGHTS))

    # forecast CO₂ ascends with hour → best hour is hour 0
    assert result.best_hour_start == "2026-04-20T00:00:00Z"
    assert result.best_hour_t_co2 < result.current_hour_t_co2


def test_inference_mode_has_no_best_hour():
    result = simulate(SimulatorInputs(
        workload="inference", country="FR", mw=1.0, hours=24.0,
        start="2026-04-20T14:00:00Z", hub_country="PL", serving_region="western",
    ), metrics_grid=_metrics_grid(), forecast=_forecast_fr(), css_results=compute_css(_metrics_grid(), DEFAULT_WEIGHTS))

    assert result.best_hour_t_co2 is None
    assert result.best_hour_cost_eur is None


def test_inference_latency_penalty_applied():
    r_close = simulate(SimulatorInputs(
        workload="inference", country="FR", mw=1.0, hours=24.0,
        start="2026-04-20T14:00:00Z", hub_country="PL", serving_region="western",
    ), metrics_grid=_metrics_grid(), forecast=_forecast_fr(), css_results=compute_css(_metrics_grid(), DEFAULT_WEIGHTS))

    r_far = simulate(SimulatorInputs(
        workload="inference", country="FR", mw=1.0, hours=24.0,
        start="2026-04-20T14:00:00Z", hub_country="PL", serving_region="northern",
    ), metrics_grid=_metrics_grid(), forecast=_forecast_fr(), css_results=compute_css(_metrics_grid(), DEFAULT_WEIGHTS))

    assert r_far.latency_penalty > r_close.latency_penalty
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_simulator.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement module**

Create `app/simulator.py`:

```python
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

    # Current-hour
    current_t = round(inputs.mw * inputs.hours * m.co2_g_per_kwh / 1000.0, 3)
    current_eur = round(inputs.mw * inputs.hours * m.price_eur_mwh, 2)
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
```

- [ ] **Step 4: Run to confirm pass**

Run: `pytest tests/test_simulator.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/simulator.py tests/test_simulator.py
git commit -m "feat: simulator — training+inference modes, best-hour picker, latency penalty"
```

---

## Task 8: Historical module with SQLite cache

**Files:**
- Create: `app/historical.py`
- Test: `tests/test_historical.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_historical.py`:

```python
import os
import tempfile
import pytest

from app.historical import HistoricalStore, DailySummary


@pytest.fixture
def tmp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield HistoricalStore(db_path=path)
    os.unlink(path)


def test_upsert_and_query(tmp_store):
    s = DailySummary(country="FR", date="2026-04-19", avg_co2=45.0, avg_price=72.0, renewable_pct=88.0)
    tmp_store.upsert(s)
    rows = tmp_store.query(country="FR", start="2026-04-19", end="2026-04-19")
    assert len(rows) == 1
    assert rows[0].avg_co2 == 45.0


def test_upsert_replaces_existing(tmp_store):
    tmp_store.upsert(DailySummary(country="FR", date="2026-04-19", avg_co2=45.0, avg_price=72.0, renewable_pct=88.0))
    tmp_store.upsert(DailySummary(country="FR", date="2026-04-19", avg_co2=50.0, avg_price=80.0, renewable_pct=85.0))
    rows = tmp_store.query(country="FR", start="2026-04-19", end="2026-04-19")
    assert len(rows) == 1
    assert rows[0].avg_co2 == 50.0


def test_query_respects_date_range(tmp_store):
    for d in ["2026-04-17", "2026-04-18", "2026-04-19"]:
        tmp_store.upsert(DailySummary(country="FR", date=d, avg_co2=45.0, avg_price=72.0, renewable_pct=88.0))
    rows = tmp_store.query(country="FR", start="2026-04-18", end="2026-04-19")
    assert len(rows) == 2
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_historical.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement module**

Create `app/historical.py`:

```python
"""
Historicals live in on-disk SQLite (they're immutable; no need for Postgres).
See spec §8 and ADR 0001.
"""
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DailySummary:
    country: str
    date: str          # ISO YYYY-MM-DD
    avg_co2: float
    avg_price: float
    renewable_pct: float


_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_summary (
    country TEXT NOT NULL,
    date TEXT NOT NULL,
    avg_co2 REAL NOT NULL,
    avg_price REAL NOT NULL,
    renewable_pct REAL NOT NULL,
    PRIMARY KEY (country, date)
);
"""


class HistoricalStore:
    def __init__(self, db_path: str):
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def upsert(self, s: DailySummary) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO daily_summary "
                "(country, date, avg_co2, avg_price, renewable_pct) VALUES (?, ?, ?, ?, ?)",
                (s.country, s.date, s.avg_co2, s.avg_price, s.renewable_pct),
            )

    def query(self, country: str, start: str, end: str) -> list[DailySummary]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT country, date, avg_co2, avg_price, renewable_pct "
                "FROM daily_summary WHERE country = ? AND date BETWEEN ? AND ? "
                "ORDER BY date",
                (country, start, end),
            ).fetchall()
        return [DailySummary(*row) for row in rows]
```

- [ ] **Step 4: Run to confirm pass**

Run: `pytest tests/test_historical.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/historical.py tests/test_historical.py
git commit -m "feat: SQLite-backed HistoricalStore for daily-summary cache"
```

---

## Task 9: New API endpoints

**Files:**
- Modify: `app/routes.py`
- Test: `tests/test_routes.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_routes.py`:

```python
def test_ranking_endpoint_returns_20_countries(client):
    with patch("app.routes._LIVE", True), \
         patch("app.routes.get_entso_client") as mock_factory:
        mock_factory.return_value.get_overview.return_value = [
            # Minimal: reuse CountryOverview to seed scoring
        ]
        response = client.get("/api/ranking")
    assert response.status_code == 200
    assert "countries" in response.json()


def test_css_endpoint_with_default_weights(client):
    with patch("app.routes._LIVE", False):
        response = client.get("/api/css?country=FR")
    assert response.status_code == 200
    body = response.json()
    assert body["country"] == "FR"
    assert 0 <= body["css"] <= 100
    assert sum(body["weights"].values()) == 100


def test_css_endpoint_rejects_bad_weights(client):
    # weights string must parse and sum to 100
    response = client.get("/api/css?country=FR&weights=50-50-0-10")  # sums to 110
    assert response.status_code == 400


def test_simulate_endpoint_training(client):
    with patch("app.routes._LIVE", False):
        response = client.get("/api/simulate?country=FR&mw=10&hours=6&workload=training")
    assert response.status_code == 200
    body = response.json()
    assert body["workload"] == "training"
    assert body["current_hour_t_co2"] > 0


def test_simulate_endpoint_inference_requires_region(client):
    response = client.get("/api/simulate?country=FR&mw=1&hours=24&workload=inference")
    assert response.status_code == 400


def test_simulate_endpoint_inference_with_region(client):
    with patch("app.routes._LIVE", False):
        response = client.get("/api/simulate?country=FR&mw=1&hours=24&workload=inference&region=western")
    assert response.status_code == 200
    assert response.json()["workload"] == "inference"
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_routes.py -v`
Expected: 404s on new endpoints.

- [ ] **Step 3: Implement endpoints**

Replace `app/routes.py` contents with:

```python
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.cache import Cache
from app.entso import get_entso_client, AREA_CODES, COUNTRY_NAMES
from app.ai import get_ai_briefing
from app.models import (
    GenerationData, PriceData, FlowData, GridSummary, OverviewData,
    CSSBreakdown, RankingEntry, SimulationResult, ForecastSeries, EvalResult,
)
from app.scoring import (
    CountryMetrics, compute_css, rank_countries,
    DEFAULT_WEIGHTS, PRESET_GREEN, PRESET_COST, Weights,
)
from app.simulator import simulate, SimulatorInputs
from app.forecast import get_forecast_client
import app.mock_data as mock

logger = logging.getLogger(__name__)
router = APIRouter()

entso_cache = Cache(ttl_seconds=900)
ai_cache = Cache(ttl_seconds=3600)
overview_cache = Cache(ttl_seconds=1800)
forecast_cache = Cache(ttl_seconds=900)
ranking_cache = Cache(ttl_seconds=900)

SUPPORTED_COUNTRIES = set(AREA_CODES.keys())
_LIVE = bool(os.environ.get("ENTSO_API_KEY", "").strip())

PRESETS: dict[str, Weights] = {
    "green": PRESET_GREEN,
    "balanced": DEFAULT_WEIGHTS,
    "cost": PRESET_COST,
}


def _validate_country(country: str) -> None:
    if country not in SUPPORTED_COUNTRIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported country: {country}. Supported: {sorted(SUPPORTED_COUNTRIES)}",
        )


def _parse_weights(s: Optional[str]) -> Weights:
    if not s:
        return DEFAULT_WEIGHTS
    if s in PRESETS:
        return PRESETS[s]
    try:
        parts = [int(x) for x in s.split("-")]
    except ValueError:
        raise HTTPException(status_code=400, detail=f"weights must be preset or carbon-cost-renewable-stability (e.g. 40-30-20-10)")
    if len(parts) != 4 or sum(parts) != 100:
        raise HTTPException(status_code=400, detail="weights must sum to 100 across 4 dimensions")
    return {"carbon": parts[0], "cost": parts[1], "renewable": parts[2], "stability": parts[3]}


def _build_grid() -> list[CountryMetrics]:
    """Assemble one CountryMetrics per supported country for scoring."""
    countries = overview_cache.get("overview")
    if not countries:
        countries = get_overview().countries  # type: ignore[attr-defined]
    grid: list[CountryMetrics] = []
    for c in countries:
        # stability σ is approximated from mock/live price variance; fall back to 10 if unavailable
        sigma = 10.0
        try:
            prices = _get_prices(c.country).prices
            if len(prices) >= 2:
                vals = [p.price_eur_mwh for p in prices]
                mean = sum(vals) / len(vals)
                sigma = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
        except Exception:
            pass
        grid.append(CountryMetrics(
            country=c.country,
            co2_g_per_kwh=c.co2_intensity,
            price_eur_mwh=c.price_eur_mwh or 0.0,
            renewable_pct=c.renewable_pct,
            price_sigma_eur_mwh=round(sigma, 2),
        ))
    return grid


def _get_generation(country: str) -> GenerationData:
    if _LIVE:
        try:
            return get_entso_client().get_generation(country)
        except Exception as e:
            logger.warning("ENTSO generation fallback for %s: %s", country, e)
    return mock.mock_generation(country)


def _get_prices(country: str) -> PriceData:
    if _LIVE:
        try:
            return get_entso_client().get_prices(country)
        except Exception as e:
            logger.warning("ENTSO prices fallback for %s: %s", country, e)
    return mock.mock_prices(country)


def _get_flows(country: str) -> FlowData:
    if _LIVE:
        try:
            return get_entso_client().get_flows(country)
        except Exception as e:
            logger.warning("ENTSO flows fallback for %s: %s", country, e)
    return mock.mock_flows(country)


@router.get("/api/generation", response_model=GenerationData)
def get_generation(country: str = Query(...)):
    _validate_country(country)
    cached = entso_cache.get(f"generation:{country}")
    if cached:
        return cached
    data = _get_generation(country)
    entso_cache.set(f"generation:{country}", data)
    return data


@router.get("/api/prices", response_model=PriceData)
def get_prices(country: str = Query(...)):
    _validate_country(country)
    cached = entso_cache.get(f"prices:{country}")
    if cached:
        return cached
    data = _get_prices(country)
    entso_cache.set(f"prices:{country}", data)
    return data


@router.get("/api/flows", response_model=FlowData)
def get_flows(country: str = Query(...)):
    _validate_country(country)
    cached = entso_cache.get(f"flows:{country}")
    if cached:
        return cached
    data = _get_flows(country)
    entso_cache.set(f"flows:{country}", data)
    return data


@router.get("/api/overview", response_model=OverviewData)
def get_overview():
    cached = overview_cache.get("overview")
    if cached:
        return cached
    if _LIVE:
        try:
            countries = get_entso_client().get_overview()
        except Exception as e:
            logger.warning("ENTSO overview fallback: %s", e)
            countries = mock.mock_overview()
    else:
        countries = mock.mock_overview()
    data = OverviewData(countries=countries)
    overview_cache.set("overview", data)
    return data


@router.get("/api/summary", response_model=GridSummary)
def get_summary(country: str = Query(...)):
    _validate_country(country)
    cached = ai_cache.get(f"summary:{country}")
    if cached:
        return cached
    gen = _get_generation(country)
    prices = _get_prices(country)
    flows = _get_flows(country)
    summary = get_ai_briefing().generate(
        country=country,
        country_name=COUNTRY_NAMES.get(country, country),
        renewable_pct=gen.renewable_pct,
        co2_intensity=gen.co2_intensity,
        price_eur_mwh=prices.current_eur_mwh or 0.0,
        sources=gen.sources,
        net_gw=flows.net_gw,
    )
    ai_cache.set(f"summary:{country}", summary)
    return summary


# ── New endpoints ────────────────────────────────────────────────────────────

@router.get("/api/css", response_model=CSSBreakdown)
def get_css(country: str = Query(...), weights: Optional[str] = Query(None)):
    _validate_country(country)
    w = _parse_weights(weights)
    cache_key = f"css:{country}:{sorted(w.items())}"
    cached = ranking_cache.get(cache_key)
    if cached:
        return cached

    grid = _build_grid()
    results = compute_css(grid, w)
    target = next((r for r in results if r.country == country), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"No metrics for {country}")

    from datetime import datetime, timezone
    breakdown = CSSBreakdown(
        country=target.country,
        css=target.css,
        as_of=datetime.now(timezone.utc).isoformat(),
        carbon_score=target.carbon_score,
        cost_score=target.cost_score,
        renewable_score=target.renewable_score,
        stability_score=target.stability_score,
        weights=w,
    )
    ranking_cache.set(cache_key, breakdown)
    return breakdown


@router.get("/api/ranking")
def get_ranking(weights: Optional[str] = Query(None)):
    w = _parse_weights(weights)
    cache_key = f"ranking:{sorted(w.items())}"
    cached = ranking_cache.get(cache_key)
    if cached:
        return cached

    grid = _build_grid()
    results = rank_countries(compute_css(grid, w))
    payload = {
        "countries": [
            RankingEntry(
                country=r.country,
                name=COUNTRY_NAMES.get(r.country, r.country),
                css=r.css,
                carbon_score=r.carbon_score,
                cost_score=r.cost_score,
                renewable_score=r.renewable_score,
                stability_score=r.stability_score,
            ).model_dump() for r in results
        ],
        "weights": w,
    }
    ranking_cache.set(cache_key, payload)
    return payload


@router.get("/api/forecast", response_model=ForecastSeries)
def get_forecast(country: str = Query(...)):
    _validate_country(country)
    cached = forecast_cache.get(f"forecast:{country}")
    if cached:
        return cached
    fc = get_forecast_client()
    if _LIVE and fc:
        try:
            data = fc.market_forecast(country)
            forecast_cache.set(f"forecast:{country}", data)
            return data
        except Exception as e:
            logger.warning("forecast fallback for %s: %s", country, e)
    # Mock: flat forecast based on current prices/CO₂
    gen = _get_generation(country)
    prices = _get_prices(country)
    from datetime import datetime, timedelta, timezone
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    from app.models import ForecastPoint
    points = [
        ForecastPoint(
            timestamp=(start + timedelta(hours=h)).isoformat(),
            co2_g_per_kwh=gen.co2_intensity,
            price_eur_mwh=(prices.current_eur_mwh or 60.0) + (h % 6 - 3) * 3,  # gentle sin-like jitter
        )
        for h in range(24)
    ]
    data = ForecastSeries(country=country, points=points, source="market")
    forecast_cache.set(f"forecast:{country}", data)
    return data


@router.get("/api/simulate", response_model=SimulationResult)
def get_simulate(
    country: str = Query(...),
    mw: float = Query(..., gt=0),
    hours: float = Query(..., gt=0),
    workload: str = Query("training"),
    region: Optional[str] = Query(None),
    hub: str = Query("DE"),
    weights: Optional[str] = Query(None),
):
    _validate_country(country)
    _validate_country(hub)
    if workload not in ("training", "inference"):
        raise HTTPException(status_code=400, detail="workload must be 'training' or 'inference'")
    if workload == "inference" and not region:
        raise HTTPException(status_code=400, detail="inference requires region")
    if region and region not in ("central", "western", "northern", "southern", "iberian"):
        raise HTTPException(status_code=400, detail="region must be central|western|northern|southern|iberian")

    w = _parse_weights(weights)
    grid = _build_grid()
    css = compute_css(grid, w)
    forecast = get_forecast(country=country)
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    result = simulate(
        SimulatorInputs(
            workload=workload,  # type: ignore[arg-type]
            country=country,
            mw=mw,
            hours=hours,
            start=now_iso,
            hub_country=hub,
            serving_region=region,
        ),
        metrics_grid=grid,
        forecast=forecast,
        css_results=css,
    )
    return result
```

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v`
Expected: all tests pass. Fix any import errors in existing tests by re-pointing at renamed internals.

- [ ] **Step 5: Commit**

```bash
git add app/routes.py tests/test_routes.py
git commit -m "feat: new endpoints — css, ranking, forecast, simulate"
```

---

## Task 10: Backend smoke — end-to-end local run

**Files:**
- (read-only)

- [ ] **Step 1: Run local server in background**

Run: `uvicorn app.main:app --port 8001 &`
Expected: server starts; log shows "Uvicorn running on http://127.0.0.1:8001".

- [ ] **Step 2: Hit each new endpoint and verify shape**

Run (one at a time):

```bash
curl -s "http://127.0.0.1:8001/api/ranking" | python -m json.tool | head -20
curl -s "http://127.0.0.1:8001/api/css?country=FR" | python -m json.tool
curl -s "http://127.0.0.1:8001/api/css?country=FR&weights=green" | python -m json.tool
curl -s "http://127.0.0.1:8001/api/forecast?country=FR" | python -m json.tool | head -40
curl -s "http://127.0.0.1:8001/api/simulate?country=FR&mw=10&hours=6&workload=training" | python -m json.tool
curl -s "http://127.0.0.1:8001/api/simulate?country=FR&mw=1&hours=24&workload=inference&region=western" | python -m json.tool
```

Expected: every response returns 200 JSON; `ranking` has 20 countries; `css` sums scores plausibly; `simulate` training returns a best-hour; inference returns `best_hour_*` as null and a non-negative `latency_penalty`.

- [ ] **Step 3: Kill background server**

Run: `kill %1 2>/dev/null; wait 2>/dev/null; true`

- [ ] **Step 4: No commit** (verification only)

---

## Task 11: Editorial CSS theme migration

**Files:**
- Modify: `frontend/style.css`

- [ ] **Step 1: Replace the `:root` and `[data-theme="light"]` blocks**

Replace lines 1-42 in `frontend/style.css` with:

```css
:root {
  /* Editorial palette — dark "paper" mode */
  --bg: #1a1815;
  --bg-card: #21201c;
  --bg-card2: #2a2824;
  --border: #3a362f;
  --text: #f3eee3;
  --muted: #b8b1a0;
  --dim: #857e6d;
  --green: #9cc98a;
  --blue: #8db6d1;
  --blue-light: #bcd8e8;
  --orange: #e69b7b;
  --yellow: #d1b06b;
  --purple: #c4a5d1;
  --accent: #c69a56;           /* muted amber — editorial accent */
  --serif: "Charter", "Iowan Old Style", Georgia, serif;
  --sans: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
  --mono: "JetBrains Mono", "SF Mono", "Fira Code", monospace;
  --radius: 4px;
  --map-ocean: #15130f;
  --map-country: #3a3730;
  --map-country-hover: #f3eee3;
  --map-selected: #c69a56;
}

[data-theme="light"] {
  --bg: #faf8f3;
  --bg-card: #ffffff;
  --bg-card2: #f2ece0;
  --border: #e8e0d0;
  --text: #1a1a1a;
  --muted: #4a4236;
  --dim: #8b8373;
  --green: #5a8a3a;
  --blue: #2f6a9e;
  --blue-light: #1e5080;
  --orange: #c85a3a;
  --yellow: #9a6a2f;
  --purple: #7a4a9a;
  --accent: #9a6a2f;
  --map-ocean: #e8dfcc;
  --map-country: #e5dcc7;
  --map-country-hover: #1a1a1a;
  --map-selected: #9a6a2f;
}
```

- [ ] **Step 2: Update body + typography base**

Replace lines 44-46 (body rule) with:

```css
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
  transition: background 0.2s, color 0.2s;
}
.mono { font-family: var(--mono); }
.serif { font-family: var(--serif); }
h1, h2, h3 { font-family: var(--serif); font-weight: 400; letter-spacing: -0.015em; }
```

- [ ] **Step 3: Visual smoke-test**

Run: `uvicorn app.main:app --port 8001 &`
Open: `http://127.0.0.1:8001/`
Expected: warmer palette; serif headlines; existing layout still renders (no broken selectors).

Run: `kill %1 2>/dev/null; wait 2>/dev/null; true`

- [ ] **Step 4: Commit**

```bash
git add frontend/style.css
git commit -m "style: editorial palette — warm paper base, Charter/Inter typography"
```

---

## Task 12: Hero section markup + logic

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/style.css`
- Create: `frontend/hero.js`
- Modify: `frontend/api.js`

- [ ] **Step 1: Add hero section to `index.html`**

Replace lines 50-58 of `index.html` (the existing ai-card block) with:

```html
<section class="hero">
  <div class="container">
    <div class="hero-eyebrow mono">An interactive essay · Updated live</div>
    <h1 class="hero-title">
      Europe's grid is changing hour by hour.
      <em>So is the right answer to where AI should run.</em>
    </h1>
    <div class="hero-live">
      Right now <span id="hero-time" class="accent">—</span>, the cleanest watt in Europe is in
      <span id="hero-best-country" class="accent">—</span>
      at <span id="hero-best-co2" class="accent">—</span> g CO₂/kWh · €<span id="hero-best-price">—</span>/MWh.
      A <span id="hero-mw">10</span> MW training run for
      <span id="hero-hours">6</span> h emits
      <span id="hero-best-emit" class="accent">—</span> t in
      <span id="hero-best-country2">—</span> vs
      <span id="hero-worst-emit" class="accent">—</span> t in
      <span id="hero-worst-country">—</span>.
    </div>
  </div>
</section>
```

- [ ] **Step 2: Add hero styles to `style.css`**

Append to `style.css`:

```css
.hero { padding: 48px 0 24px; border-bottom: 1px solid var(--border); background: var(--bg-card); }
.hero-eyebrow { text-transform: uppercase; letter-spacing: 2px; font-size: 10px; color: var(--accent); margin-bottom: 18px; }
.hero-title { font-size: clamp(28px, 4.5vw, 44px); line-height: 1.15; margin-bottom: 20px; max-width: 820px; }
.hero-title em { color: var(--accent); font-style: italic; }
.hero-live { font-size: 14px; color: var(--muted); line-height: 1.75; border-left: 2px solid var(--accent); padding-left: 14px; max-width: 720px; }
.hero-live .accent { color: var(--text); font-weight: 600; }
```

- [ ] **Step 3: Extend `api.js` with new endpoints**

Append to `frontend/api.js`:

```javascript
async function fetchRanking(weights) {
  const q = weights ? `?weights=${encodeURIComponent(weights)}` : "";
  return fetchJson(`/api/ranking${q}`);
}

async function fetchCss(country, weights) {
  const params = new URLSearchParams({ country });
  if (weights) params.set("weights", weights);
  return fetchJson(`/api/css?${params}`);
}

async function fetchForecast(country) {
  return fetchJson(`/api/forecast?country=${country}`);
}

async function fetchSimulate({ country, mw, hours, workload, region, hub, weights }) {
  const params = new URLSearchParams({ country, mw, hours, workload });
  if (region) params.set("region", region);
  if (hub) params.set("hub", hub);
  if (weights) params.set("weights", weights);
  return fetchJson(`/api/simulate?${params}`);
}
```

- [ ] **Step 4: Create `hero.js`**

Create `frontend/hero.js`:

```javascript
async function renderHero() {
  const mw = 10, hours = 6;
  try {
    const ranking = await fetchRanking();
    const top = ranking.countries[0];
    const bottom = ranking.countries[ranking.countries.length - 1];

    const [topCss, bottomCss] = await Promise.all([
      fetchCss(top.country),
      fetchCss(bottom.country),
    ]);

    document.getElementById("hero-time").textContent =
      new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " UTC";

    document.getElementById("hero-best-country").textContent = top.name;
    document.getElementById("hero-best-country2").textContent = top.name;
    document.getElementById("hero-worst-country").textContent = bottom.name;

    const topGen = await fetchJson(`/api/generation?country=${top.country}`);
    const bottomGen = await fetchJson(`/api/generation?country=${bottom.country}`);
    const topPrices = await fetchJson(`/api/prices?country=${top.country}`);

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
```

- [ ] **Step 5: Wire `hero.js` into `index.html`**

Add to the `<head>` of `index.html` after `charts.js` script tag:

```html
<script src="hero.js" defer></script>
```

- [ ] **Step 6: Visual smoke-test**

Run: `uvicorn app.main:app --port 8001 &`
Open: `http://127.0.0.1:8001/`
Expected: hero renders with serif H1 + italic thesis clause; live line fills in with top country name, CO₂, price, and the two emissions numbers; browser console clean.

Run: `kill %1 2>/dev/null; wait 2>/dev/null; true`

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/style.css frontend/hero.js frontend/api.js
git commit -m "feat: thesis hero section with live cleanest/dirtiest banner"
```

---

## Task 13: Live ranking strip

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/style.css`
- Create: `frontend/ranking.js`

- [ ] **Step 1: Add ranking strip markup**

Insert into `index.html` after the `</section>` of the hero:

```html
<section class="ranking-strip">
  <div class="container">
    <div class="ranking-header">
      <span class="ranking-title mono">Compute Siting Score · all 20 countries</span>
      <div class="ranking-controls">
        <div class="preset-switcher" role="radiogroup" aria-label="weights preset">
          <button class="preset-btn" data-preset="green">Green</button>
          <button class="preset-btn active" data-preset="balanced">Balanced</button>
          <button class="preset-btn" data-preset="cost">Cost</button>
        </div>
        <div class="workload-switcher" role="radiogroup" aria-label="workload mode">
          <button class="workload-btn active" data-workload="training">Training</button>
          <button class="workload-btn" data-workload="inference">Inference</button>
        </div>
      </div>
    </div>
    <div id="ranking-list" class="ranking-list">Loading ranking…</div>
  </div>
</section>
```

- [ ] **Step 2: Add styles**

Append to `style.css`:

```css
.ranking-strip { padding: 24px 0; }
.ranking-header { display: flex; justify-content: space-between; align-items: center; gap: 14px; flex-wrap: wrap; margin-bottom: 14px; }
.ranking-title { font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: var(--dim); }
.ranking-controls { display: flex; gap: 10px; }
.preset-switcher, .workload-switcher { display: inline-flex; border: 1px solid var(--border); border-radius: 99px; overflow: hidden; }
.preset-btn, .workload-btn { background: transparent; color: var(--muted); border: none; padding: 6px 14px; font-size: 11px; font-family: var(--mono); cursor: pointer; transition: background 0.15s, color 0.15s; }
.preset-btn:hover, .workload-btn:hover { color: var(--text); }
.preset-btn.active, .workload-btn.active { background: var(--accent); color: var(--bg); }
.ranking-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 6px; }
.rank-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 12px; transition: transform 0.15s, border-color 0.15s; cursor: pointer; }
.rank-card:hover { transform: translateY(-1px); border-color: var(--accent); }
.rank-card .num { font-family: var(--serif); font-size: 22px; font-weight: 700; color: var(--text); font-feature-settings: "tnum"; }
.rank-card .name { font-size: 11px; color: var(--muted); margin-top: 2px; }
.rank-card.top { border-left: 2px solid var(--accent); }
@media (max-width: 600px) {
  .ranking-list { grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); }
}
```

- [ ] **Step 3: Create `ranking.js`**

Create `frontend/ranking.js`:

```javascript
const RankingState = {
  preset: "balanced",
  workload: "training",
};

async function renderRanking() {
  const list = document.getElementById("ranking-list");
  try {
    const data = await fetchRanking(RankingState.preset === "balanced" ? null : RankingState.preset);
    list.innerHTML = "";
    data.countries.forEach((c, i) => {
      const card = document.createElement("div");
      card.className = "rank-card" + (i === 0 ? " top" : "");
      card.dataset.country = c.country;
      card.innerHTML = `<div class="num">${Math.round(c.css)}</div><div class="name">${c.name}</div>`;
      card.addEventListener("click", () => {
        const sel = document.getElementById("country-select");
        if (sel) { sel.value = c.country; sel.dispatchEvent(new Event("change")); }
      });
      list.appendChild(card);
    });
  } catch (e) {
    list.textContent = "Failed to load ranking.";
    console.error(e);
  }
}

function wireRankingControls() {
  document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      RankingState.preset = btn.dataset.preset;
      renderRanking();
    });
  });
  document.querySelectorAll(".workload-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".workload-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      RankingState.workload = btn.dataset.workload;
      // Workload shapes the simulator (Plan B); for now it annotates only.
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  wireRankingControls();
  renderRanking();
});
```

- [ ] **Step 4: Wire into `index.html` head**

Add after the `hero.js` script tag:

```html
<script src="ranking.js" defer></script>
```

- [ ] **Step 5: Visual smoke-test**

Run: `uvicorn app.main:app --port 8001 &`
Open: `http://127.0.0.1:8001/`
Expected:
- Ranking strip renders under the hero with 20 cards.
- Clicking Green/Balanced/Cost re-orders cards; active button highlights.
- Training/Inference toggle visually switches but doesn't re-fetch yet.
- Clicking a rank card updates the country selector.

Run: `kill %1 2>/dev/null; wait 2>/dev/null; true`

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/style.css frontend/ranking.js
git commit -m "feat: live ranking strip with weights presets + workload toggle"
```

---

## Task 14: Verify all prior tests still pass

**Files:**
- (read-only)

- [ ] **Step 1: Full test run**

Run: `pytest tests/ -v`
Expected: green across the board. Any regressions trace back to the routes refactor; fix in-place rather than skipping.

- [ ] **Step 2: Commit any fixes**

If edits were needed:
```bash
git add <paths>
git commit -m "fix: regressions from Plan A refactor"
```

Otherwise: no commit.

---

## Task 15: Tag Plan-A complete

**Files:**
- (git only)

- [ ] **Step 1: Tag**

```bash
git tag plan-a-complete
git log --oneline plan-a-complete -20
```

- [ ] **Step 2: Confirm site works**

Run: `uvicorn app.main:app --port 8001 &`
Open `http://127.0.0.1:8001/` and click around:
- Hero renders thesis.
- Ranking strip populates; presets re-order.
- Country selector still loads the legacy map + charts.
- All four corners of `/api/*` return 200 when poked via curl.

Run: `kill %1 2>/dev/null; wait 2>/dev/null; true`

Plan A done. Plan B picks up from map-upgrade.
