from pydantic import BaseModel
from typing import Optional


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
