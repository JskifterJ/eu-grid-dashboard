from app.models import GenerationData, PricePoint, FlowItem, CountryOverview, GridSummary


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
