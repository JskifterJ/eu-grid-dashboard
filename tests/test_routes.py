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
    with patch("app.routes.entso_cache.get", return_value=None), \
         patch("app.routes.entso_cache.set"), \
         patch("app.routes.get_entso_client") as mock_factory:
        mock_factory.return_value.get_generation.return_value = _mock_generation()
        response = client.get("/api/generation?country=DK")
    assert response.status_code == 200
    assert response.json()["country"] == "DK"
    assert response.json()["renewable_pct"] == 68.0


def test_prices_endpoint(client):
    with patch("app.routes.entso_cache.get", return_value=None), \
         patch("app.routes.entso_cache.set"), \
         patch("app.routes.get_entso_client") as mock_factory:
        mock_factory.return_value.get_prices.return_value = _mock_prices()
        response = client.get("/api/prices?country=DK")
    assert response.status_code == 200
    assert response.json()["current_eur_mwh"] == 78.0


def test_summary_endpoint(client):
    with patch("app.routes.ai_cache.get", return_value=None), \
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
