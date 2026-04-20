from app.models import (
    GenerationData, PricePoint, FlowItem, CountryOverview, GridSummary,
    ForecastPoint, ForecastSeries, CSSBreakdown, RankingEntry,
    SimulationResult, EvalResult, StructuredBriefing,
)


def test_generation_data_valid():
    g = GenerationData(
        country="DE",
        sources={"Wind": 34.0, "Solar": 24.0, "Gas": 18.0},
        renewable_pct=58.0,
        co2_intensity=218.0,
        total_gw=62.4,
    )
    assert g.country == "DE"
    assert g.renewable_pct == 58.0


def test_price_point_valid():
    p = PricePoint(timestamp="2026-04-13T14:00:00", price_eur_mwh=87.5)
    assert p.price_eur_mwh == 87.5


def test_flow_item_valid():
    f = FlowItem(partner="France", flow_gw=3.1, direction="export")
    assert f.direction == "export"


def test_country_overview_valid():
    o = CountryOverview(
        country="DE",
        name="Germany",
        co2_intensity=218.0,
        renewable_pct=58.0,
        price_eur_mwh=87.0,
    )
    assert o.name == "Germany"


def test_grid_summary_valid():
    s = GridSummary(country="DE", text="Germany is running 58% renewables today.")
    assert "58%" in s.text


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


def test_ranking_entry_valid():
    r = RankingEntry(
        country="FR", name="France", css=94.2,
        carbon_score=98.0, cost_score=88.0, renewable_score=95.0, stability_score=90.0,
    )
    assert r.name == "France"
    assert r.css == 94.2
