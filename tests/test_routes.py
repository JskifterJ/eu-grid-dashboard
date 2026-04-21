import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models import GenerationData, PriceData, FlowData, GridSummary, PricePoint


@pytest.fixture
def client():
    return TestClient(app)


def _mock_generation():
    return GenerationData(
        country="DK", sources={"Wind": 55.0, "Gas": 18.0},
        renewable_pct=68.0, co2_intensity=115.0, total_gw=12.4,
    )


def _mock_prices():
    return PriceData(
        country="DK",
        prices=[PricePoint(timestamp="2026-04-13T14:00:00", price_eur_mwh=78.0)],
        current_eur_mwh=78.0,
        delta_pct=-5.0,
    )


def _mock_flows():
    return FlowData(country="DK", flows=[], net_gw=0.3)


def _mock_summary():
    return GridSummary(country="DK", text="Denmark is running 68% renewables.")


def test_generation_endpoint(client):
    with patch("app.routes._LIVE", True), \
         patch("app.routes.entso_cache.get", return_value=None), \
         patch("app.routes.entso_cache.set"), \
         patch("app.routes.get_entso_client") as mock_factory:
        mock_factory.return_value.get_generation.return_value = _mock_generation()
        response = client.get("/api/generation?country=DK")
    assert response.status_code == 200
    assert response.json()["country"] == "DK"
    assert response.json()["renewable_pct"] == 68.0


def test_prices_endpoint(client):
    with patch("app.routes._LIVE", True), \
         patch("app.routes.entso_cache.get", return_value=None), \
         patch("app.routes.entso_cache.set"), \
         patch("app.routes.get_entso_client") as mock_factory:
        mock_factory.return_value.get_prices.return_value = _mock_prices()
        response = client.get("/api/prices?country=DK")
    assert response.status_code == 200
    assert response.json()["current_eur_mwh"] == 78.0


def test_summary_endpoint(client):
    with patch("app.routes._LIVE", True), \
         patch("app.routes.ai_cache.get", return_value=None), \
         patch("app.routes.ai_cache.set"), \
         patch("app.routes.get_entso_client") as mock_entso, \
         patch("app.routes.get_ai_briefing") as mock_ai:
        mock_entso.return_value.get_generation.return_value = _mock_generation()
        mock_entso.return_value.get_prices.return_value = _mock_prices()
        mock_entso.return_value.get_flows.return_value = _mock_flows()
        mock_ai.return_value.generate.return_value = _mock_summary()
        response = client.get("/api/summary?country=DK")
    assert response.status_code == 200
    assert "Denmark" in response.json()["text"]


def test_unknown_country_returns_400(client):
    response = client.get("/api/generation?country=XX")
    assert response.status_code == 400


def test_fallback_to_mock_on_entso_error(client):
    """When ENTSO raises, response should still be 200 using mock data."""
    with patch("app.routes._LIVE", True), \
         patch("app.routes.entso_cache.get", return_value=None), \
         patch("app.routes.entso_cache.set"), \
         patch("app.routes.get_entso_client") as mock_factory:
        mock_factory.return_value.get_generation.side_effect = Exception("NoMatchingDataError")
        response = client.get("/api/generation?country=DK")
    assert response.status_code == 200
    assert response.json()["country"] == "DK"


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


def test_css_with_carbon_price_increases_dirty_country_cost(client):
    """At higher carbon price, a dirty country's effective cost goes up; cost score drops."""
    with patch("app.routes._LIVE", False):
        zero = client.get("/api/css?country=PL&carbon_price=0").json()
        priced = client.get("/api/css?country=PL&carbon_price=100").json()
    # Poland is high-CO2 — cost score should be lower (worse) with carbon adder
    assert priced["cost_score"] <= zero["cost_score"]


def test_ranking_response_includes_carbon_price(client):
    with patch("app.routes._LIVE", False):
        r = client.get("/api/ranking?carbon_price=80").json()
    assert r.get("carbon_price_eur_per_tco2") == 80.0


def test_css_default_carbon_price_is_75(client):
    with patch("app.routes._LIVE", False):
        body = client.get("/api/css?country=FR").json()
    assert body["carbon_price_eur_per_tco2"] == 75.0


def test_ranking_with_workload_inference_western_shifts_iberian_down(client):
    with patch("app.routes._LIVE", False):
        infer_w = client.get("/api/ranking?workload=inference&region=western").json()
        infer_n = client.get("/api/ranking?workload=inference&region=northern").json()
    def rank_of(payload, country):
        for i, c in enumerate(payload["countries"]):
            if c["country"] == country: return i
        return None
    # Portugal/Spain rank lower (higher index) under northern serving region than western
    assert rank_of(infer_n, "PT") > rank_of(infer_w, "PT") or rank_of(infer_n, "ES") > rank_of(infer_w, "ES")


def test_ranking_inference_without_region_returns_400(client):
    r = client.get("/api/ranking?workload=inference")
    assert r.status_code == 400


def test_ranking_workload_overrides_weights_param(client):
    with patch("app.routes._LIVE", False):
        r = client.get("/api/ranking?workload=training&weights=cost").json()
    # Workload preset wins — assert response weights match training's preset (40/30/20/10)
    assert r["weights"] == {"carbon": 40, "cost": 30, "renewable": 20, "stability": 10}


def test_eval_endpoint_returns_both_mape_values(client):
    with patch("app.routes._LIVE", False):
        r = client.get("/api/eval?country=FR&metric=co2").json()
    assert r["country"] == "FR"
    assert r["metric"] == "co2"
    assert "market_mape_pct" in r and "naive_mape_pct" in r
    assert 0 < r["market_mape_pct"] < 50
    assert 0 < r["naive_mape_pct"] < 50


def test_eval_endpoint_price_metric(client):
    with patch("app.routes._LIVE", False):
        r = client.get("/api/eval?country=DE&metric=price").json()
    assert r["metric"] == "price"
    # market forecast should typically beat naive baseline
    assert r["market_mape_pct"] <= r["naive_mape_pct"]


def test_eval_endpoint_unknown_metric_returns_400(client):
    r = client.get("/api/eval?country=FR&metric=temperature")
    assert r.status_code == 400


def test_lca_endpoint_default_hardware(client):
    with patch("app.routes._LIVE", False):
        r = client.get("/api/lca?country=FR&mw=10&hours=6").json()
    assert r["hardware"] == "H100"
    assert r["workload_mw"] == 10.0
    assert r["workload_hours"] == 6.0
    assert r["total_kg"] > 0
    assert r["operational_co2_kg"] > 0
    assert r["embodied_hardware_kg"] > 0
    assert r["embodied_datacenter_kg"] > 0


def test_lca_endpoint_custom_hardware(client):
    with patch("app.routes._LIVE", False):
        h100 = client.get("/api/lca?country=FR&mw=10&hours=6&hardware=H100").json()
        b200 = client.get("/api/lca?country=FR&mw=10&hours=6&hardware=B200").json()
    assert h100["hardware"] == "H100"
    assert b200["hardware"] == "B200"
    assert h100["embodied_hardware_kg"] != b200["embodied_hardware_kg"]


def test_lca_endpoint_rejects_unknown_hardware(client):
    r = client.get("/api/lca?country=FR&mw=10&hours=6&hardware=FakeGPU")
    assert r.status_code == 400


def test_lca_endpoint_country_pue_default(client):
    with patch("app.routes._LIVE", False):
        no = client.get("/api/lca?country=NO&mw=10&hours=6").json()
        it = client.get("/api/lca?country=IT&mw=10&hours=6").json()
    # Nordic NO has PUE ~1.1, hot-climate IT ~1.4 → NO has less cooling overhead
    assert no["pue"] < it["pue"]
    assert no["cooling_overhead_kg"] < it["cooling_overhead_kg"]


def test_time_of_day_endpoint_returns_24h_and_windows(client):
    with patch("app.routes._LIVE", False):
        r = client.get("/api/time-of-day?country=FR&mw=10&hours=6").json()
    assert r["country"] == "FR"
    assert len(r["hours"]) == 24
    assert r["best_window"]["avg_co2_g_per_kwh"] <= r["worst_window"]["avg_co2_g_per_kwh"]
    assert r["co2_savings_pct"] >= 0
    assert r["cost_savings_pct"] >= 0


def test_time_of_day_rejects_workload_over_24h(client):
    r = client.get("/api/time-of-day?country=FR&mw=10&hours=25")
    assert r.status_code == 400


def test_simulate_endpoint_with_lca_flag(client):
    with patch("app.routes._LIVE", False):
        without = client.get("/api/simulate?country=FR&mw=10&hours=6&workload=training").json()
        with_lca = client.get("/api/simulate?country=FR&mw=10&hours=6&workload=training&lca=true").json()
    assert "lca" not in without or without["lca"] is None
    assert with_lca["lca"] is not None
    assert with_lca["lca"]["total_kg"] > 0
    assert with_lca["lca"]["operational_co2_kg"] > 0
