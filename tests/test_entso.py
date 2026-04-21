import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
from app.entso import calculate_co2_intensity, map_generation_sources, ENTSOClient


def test_co2_intensity_all_wind():
    sources = {"Wind Onshore": 100.0}
    assert calculate_co2_intensity(sources) == pytest.approx(11.0)


def test_co2_intensity_mixed():
    sources = {"Wind Onshore": 50.0, "Fossil Gas": 50.0}
    result = calculate_co2_intensity(sources)
    assert result == pytest.approx((11.0 * 50 + 490.0 * 50) / 100, rel=1e-3)


def test_co2_intensity_empty():
    assert calculate_co2_intensity({}) == 0.0


def test_map_generation_sources_groups_wind():
    raw = {"Wind Onshore": 20.0, "Wind Offshore": 5.0, "Solar": 10.0}
    result = map_generation_sources(raw)
    assert result["Wind"] == pytest.approx(25.0)
    assert result["Solar"] == pytest.approx(10.0)


def test_entso_client_get_generation_returns_generation_data():
    with patch("app.entso.EntsoePandasClient") as MockClient:
        idx = pd.date_range("2026-04-13 12:00", periods=1, freq="h", tz="UTC")
        df = pd.DataFrame(
            {"Wind Onshore": [22000.0], "Fossil Gas": [8000.0], "Solar": [5000.0]},
            index=idx,
        )
        MockClient.return_value.query_generation.return_value = df

        client = ENTSOClient(api_key="test-key")
        result = client.get_generation("DE")

    assert result.country == "DE"
    assert result.total_gw > 0
    assert len(result.sources) > 0


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


def test_expanded_country_set_includes_balkans_and_baltics():
    from app.entso import COUNTRY_NAMES
    expected_new = {"EE", "LV", "LT", "SK", "SI", "HR", "BG", "RS", "BA",
                    "ME", "MK", "AL", "IS", "CY", "LU"}
    for c in expected_new:
        assert c in AREA_CODES, f"missing country {c}"
        assert c in COUNTRY_NAMES, f"missing name for {c}"


def test_total_country_count_around_35():
    assert 33 <= len(AREA_CODES) <= 38
