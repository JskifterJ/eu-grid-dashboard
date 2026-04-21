import hashlib
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.cache import Cache
from app.entso import get_entso_client, AREA_CODES, COUNTRY_NAMES
from app.ai import get_ai_briefing
from app.briefing import get_structured_briefing
from app.models import (
    GenerationData, PriceData, FlowData, GridSummary, OverviewData,
    CSSBreakdown, RankingEntry, SimulationResult, ForecastSeries, EvalResult,
    StructuredBriefing,
)
from app.scoring import (
    CountryMetrics, compute_css, rank_countries,
    DEFAULT_WEIGHTS, PRESET_GREEN, PRESET_COST, Weights,
    DEFAULT_CARBON_PRICE_EUR_PER_TCO2, carbon_internalized_price,
    WORKLOAD_PRESETS, weights_for_workload, apply_per_country_latency_penalty,
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
briefing_cache = Cache(ttl_seconds=3600)
eval_cache = Cache(ttl_seconds=21600)  # 6 hours

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
        raise HTTPException(status_code=400, detail="weights must be preset or carbon-cost-renewable-stability (e.g. 40-30-20-10)")
    if len(parts) != 4 or sum(parts) != 100:
        raise HTTPException(status_code=400, detail="weights must sum to 100 across 4 dimensions")
    return {"carbon": parts[0], "cost": parts[1], "renewable": parts[2], "stability": parts[3]}


VALID_REGIONS = {"central", "western", "northern", "southern", "iberian"}


def _resolve_weights(workload: Optional[str], weights: Optional[str]) -> Weights:
    if workload:
        if workload not in WORKLOAD_PRESETS:
            raise HTTPException(400, f"workload must be one of {sorted(WORKLOAD_PRESETS)}")
        return weights_for_workload(workload)
    return _parse_weights(weights)


def _validate_region(region: Optional[str]) -> None:
    if region is not None and region not in VALID_REGIONS:
        raise HTTPException(400, f"region must be one of {sorted(VALID_REGIONS)}")


def _build_grid(carbon_price: float = DEFAULT_CARBON_PRICE_EUR_PER_TCO2) -> list[CountryMetrics]:
    """Assemble one CountryMetrics per supported country for scoring."""
    cached_overview = overview_cache.get("overview")
    if cached_overview:
        countries = cached_overview.countries
    else:
        countries = get_overview().countries
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
            price_eur_mwh=carbon_internalized_price(c.price_eur_mwh or 0.0, c.co2_intensity, carbon_price),
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
def get_css(
    country: str = Query(...),
    weights: Optional[str] = Query(None),
    workload: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    carbon_price: Optional[float] = Query(DEFAULT_CARBON_PRICE_EUR_PER_TCO2),
):
    _validate_country(country)
    if workload == "inference" and not region:
        raise HTTPException(400, "inference workload requires region")
    _validate_region(region)
    w = _resolve_weights(workload, weights)
    effective_carbon_price = carbon_price if carbon_price is not None else DEFAULT_CARBON_PRICE_EUR_PER_TCO2
    cache_key = f"css:{country}:{sorted(w.items())}:{workload}:{region}:{effective_carbon_price}"
    cached = ranking_cache.get(cache_key)
    if cached:
        return cached

    grid = _build_grid(effective_carbon_price)
    results = compute_css(grid, w)
    if workload == "inference":
        results = apply_per_country_latency_penalty(results, region)
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
        carbon_price_eur_per_tco2=effective_carbon_price,
    )
    ranking_cache.set(cache_key, breakdown)
    return breakdown


@router.get("/api/ranking")
def get_ranking(
    weights: Optional[str] = Query(None),
    workload: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    carbon_price: Optional[float] = Query(DEFAULT_CARBON_PRICE_EUR_PER_TCO2),
):
    if workload == "inference" and not region:
        raise HTTPException(400, "inference workload requires region")
    _validate_region(region)
    w = _resolve_weights(workload, weights)
    effective_carbon_price = carbon_price if carbon_price is not None else DEFAULT_CARBON_PRICE_EUR_PER_TCO2
    cache_key = f"ranking:{sorted(w.items())}:{workload}:{region}:{effective_carbon_price}"
    cached = ranking_cache.get(cache_key)
    if cached:
        return cached

    grid = _build_grid(effective_carbon_price)
    results = compute_css(grid, w)
    if workload == "inference":
        results = apply_per_country_latency_penalty(results, region)
    results = rank_countries(results)
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
        "workload": workload,
        "region": region,
        "carbon_price_eur_per_tco2": effective_carbon_price,
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
    # Mock: flat forecast based on current prices/CO2
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
    carbon_price: Optional[float] = Query(DEFAULT_CARBON_PRICE_EUR_PER_TCO2),
):
    _validate_country(country)
    _validate_country(hub)
    if workload not in ("training", "inference"):
        raise HTTPException(status_code=400, detail="workload must be 'training' or 'inference'")
    if workload == "inference" and not region:
        raise HTTPException(status_code=400, detail="inference requires region")
    if region and region not in ("central", "western", "northern", "southern", "iberian"):
        raise HTTPException(status_code=400, detail="region must be central|western|northern|southern|iberian")

    effective_carbon_price = carbon_price if carbon_price is not None else DEFAULT_CARBON_PRICE_EUR_PER_TCO2
    w = _resolve_weights(workload, weights)
    grid = _build_grid(effective_carbon_price)
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


@router.get("/api/briefing", response_model=StructuredBriefing)
def get_briefing(
    country: str = Query(...),
    workload: str = Query("training"),
    carbon_price: Optional[float] = Query(DEFAULT_CARBON_PRICE_EUR_PER_TCO2),
):
    _validate_country(country)
    if workload not in ("training", "fine-tuning", "inference"):
        raise HTTPException(400, "workload must be one of training|fine-tuning|inference")

    cache_key = f"briefing:{country}:{workload}:{carbon_price}"
    cached = briefing_cache.get(cache_key)
    if cached:
        return cached

    gen = _get_generation(country)
    prices = _get_prices(country)
    # Use current CSS for context
    grid = _build_grid(carbon_price)
    w = weights_for_workload(workload)
    results = compute_css(grid, w)
    target = next((r for r in results if r.country == country), None)
    css_val = target.css if target else 50.0

    briefing = get_structured_briefing(
        country=country,
        country_name=COUNTRY_NAMES.get(country, country),
        co2_g_per_kwh=gen.co2_intensity,
        price_eur_mwh=prices.current_eur_mwh or 0.0,
        renewable_pct=gen.renewable_pct,
        css=css_val,
        workload=workload,
    )
    briefing_cache.set(cache_key, briefing)
    return briefing


@router.get("/api/eval", response_model=EvalResult)
def get_eval(country: str = Query(...), metric: str = Query("co2")):
    _validate_country(country)
    if metric not in ("co2", "price"):
        raise HTTPException(400, "metric must be co2 or price")
    key = f"eval:{country}:{metric}"
    cached = eval_cache.get(key)
    if cached:
        return cached
    if _LIVE:
        # TODO: when HistoricalStore has data, compute real MAPE here
        pass
    # Deterministic mock MAPE seeded from country + metric
    seed = int(hashlib.md5(f"{country}:{metric}".encode()).hexdigest()[:8], 16)
    if metric == "price":
        market = 6 + (seed % 50) / 10.0         # 6.0 – 11.0
        naive  = 12 + (seed % 80) / 10.0        # 12.0 – 20.0
    else:  # co2
        market = 10 + (seed % 50) / 10.0        # 10.0 – 15.0
        naive  = 18 + (seed % 80) / 10.0        # 18.0 – 26.0
    result = EvalResult(
        country=country, metric=metric,  # type: ignore[arg-type]
        window_days=7, market_mape_pct=round(market, 2), naive_mape_pct=round(naive, 2),
    )
    eval_cache.set(key, result)
    return result
