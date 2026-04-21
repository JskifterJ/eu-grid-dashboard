from pydantic import BaseModel
from typing import Optional, Literal


class GenerationData(BaseModel):
    country: str
    sources: dict[str, float]          # display name → GW
    renewable_pct: float
    co2_intensity: float               # g/kWh
    total_gw: float


class PricePoint(BaseModel):
    timestamp: str                     # ISO 8601
    price_eur_mwh: float


class FlowItem(BaseModel):
    partner: str
    flow_gw: float                     # magnitude
    direction: str                     # "import" | "export"


class FlowData(BaseModel):
    country: str
    flows: list[FlowItem]
    net_gw: float


class PriceData(BaseModel):
    country: str
    prices: list[PricePoint]
    current_eur_mwh: Optional[float]
    delta_pct: Optional[float]         # vs yesterday's average


class CountryOverview(BaseModel):
    country: str
    name: str
    co2_intensity: float
    renewable_pct: float
    price_eur_mwh: Optional[float]


class OverviewData(BaseModel):
    countries: list[CountryOverview]


class GridSummary(BaseModel):
    country: str
    text: str
    generated_at: Optional[str] = None


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
    carbon_price_eur_per_tco2: float = 0.0


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


class LCABreakdown(BaseModel):
    workload_mw: float
    workload_hours: float
    hardware: str
    pue: float
    life_years: int
    operational_co2_kg: float        # grid CO₂ × MW × h (PUE-adjusted)
    cooling_overhead_kg: float       # portion of operational due to PUE > 1 (subset of operational)
    embodied_hardware_kg: float      # GPU manufacturing, amortized
    embodied_datacenter_kg: float    # building+cooling+power infra, amortized
    total_kg: float                  # operational + embodied_hardware + embodied_datacenter
    operational_share_pct: float     # operational / total × 100


class TimeOfDayHour(BaseModel):
    timestamp: str
    co2_g_per_kwh: float
    price_eur_mwh: float


class TimeOfDayWindow(BaseModel):
    start: str
    end: str
    avg_co2_g_per_kwh: float
    avg_price_eur_mwh: float
    total_co2_kg: float          # for the workload (mw × hours × co2)
    total_cost_eur: float         # for the workload


class TimeOfDayResult(BaseModel):
    country: str
    workload_mw: float
    workload_hours: float
    hours: list[TimeOfDayHour]   # full 24h timeline
    best_window: TimeOfDayWindow
    worst_window: TimeOfDayWindow
    co2_savings_pct: float       # (worst - best) / worst × 100
    cost_savings_pct: float
    co2_savings_kg: float        # worst - best, in kg
    cost_savings_eur: float
