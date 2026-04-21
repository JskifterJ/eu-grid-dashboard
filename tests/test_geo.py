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


def test_expanded_countries_have_centroids():
    expected_new = {"EE", "LV", "LT", "SK", "SI", "HR", "BG", "RS", "BA",
                    "ME", "MK", "AL", "IS", "CY", "LU"}
    for c in expected_new:
        assert c in COUNTRY_CENTROIDS, f"missing centroid for {c}"
