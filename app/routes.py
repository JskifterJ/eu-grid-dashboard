from fastapi import APIRouter, HTTPException, Query

from app.cache import Cache
from app.entso import get_entso_client, AREA_CODES, COUNTRY_NAMES
from app.ai import get_ai_briefing
from app.models import GenerationData, PriceData, FlowData, GridSummary, OverviewData

router = APIRouter()

entso_cache = Cache(ttl_seconds=900)
ai_cache = Cache(ttl_seconds=900)
overview_cache = Cache(ttl_seconds=900)

SUPPORTED_COUNTRIES = set(AREA_CODES.keys())


def _validate_country(country: str) -> None:
    if country not in SUPPORTED_COUNTRIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported country: {country}. Supported: {sorted(SUPPORTED_COUNTRIES)}",
        )


@router.get("/api/generation", response_model=GenerationData)
def get_generation(country: str = Query(...)):
    _validate_country(country)
    cached = entso_cache.get(f"generation:{country}")
    if cached:
        return cached
    data = get_entso_client().get_generation(country)
    entso_cache.set(f"generation:{country}", data)
    return data


@router.get("/api/prices", response_model=PriceData)
def get_prices(country: str = Query(...)):
    _validate_country(country)
    cached = entso_cache.get(f"prices:{country}")
    if cached:
        return cached
    data = get_entso_client().get_prices(country)
    entso_cache.set(f"prices:{country}", data)
    return data


@router.get("/api/flows", response_model=FlowData)
def get_flows(country: str = Query(...)):
    _validate_country(country)
    cached = entso_cache.get(f"flows:{country}")
    if cached:
        return cached
    data = get_entso_client().get_flows(country)
    entso_cache.set(f"flows:{country}", data)
    return data


@router.get("/api/overview", response_model=OverviewData)
def get_overview():
    cached = overview_cache.get("overview")
    if cached:
        return cached
    countries = get_entso_client().get_overview()
    data = OverviewData(countries=countries)
    overview_cache.set("overview", data)
    return data


@router.get("/api/summary", response_model=GridSummary)
def get_summary(country: str = Query(...)):
    _validate_country(country)
    cached = ai_cache.get(f"summary:{country}")
    if cached:
        return cached

    client = get_entso_client()
    gen = client.get_generation(country)
    prices = client.get_prices(country)
    flows = client.get_flows(country)

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
