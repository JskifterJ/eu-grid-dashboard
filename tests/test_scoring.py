import pytest

from app.scoring import (
    Weights, CountryMetrics, compute_css, rank_countries,
    DEFAULT_WEIGHTS, PRESET_GREEN, PRESET_COST,
)


def _metrics(c, co2, price, ren, sigma):
    return CountryMetrics(
        country=c, co2_g_per_kwh=co2, price_eur_mwh=price,
        renewable_pct=ren, price_sigma_eur_mwh=sigma,
    )


def test_default_weights_sum_to_100():
    assert sum(DEFAULT_WEIGHTS.values()) == 100


def test_all_presets_sum_to_100():
    assert sum(PRESET_GREEN.values()) == 100
    assert sum(PRESET_COST.values()) == 100


def test_invalid_weights_raises():
    with pytest.raises(ValueError):
        compute_css([_metrics("FR", 40, 70, 90, 5)], {"carbon": 50, "cost": 50, "renewable": 0, "stability": 10})


def test_single_country_all_dimensions_get_50():
    # with one country, min == max → normalized = 50 (midpoint)
    result = compute_css([_metrics("FR", 40, 70, 90, 5)], DEFAULT_WEIGHTS)
    assert result[0].css == pytest.approx(50.0, abs=0.01)


def test_two_countries_clean_wins():
    metrics = [
        _metrics("FR", 40, 70, 90, 5),   # cleaner, cheaper, more renewable, stabler
        _metrics("PL", 600, 120, 15, 30),
    ]
    result = compute_css(metrics, DEFAULT_WEIGHTS)
    fr = next(r for r in result if r.country == "FR")
    pl = next(r for r in result if r.country == "PL")
    assert fr.css == pytest.approx(100.0, abs=0.01)
    assert pl.css == pytest.approx(0.0, abs=0.01)


def test_cost_preset_orders_by_price():
    metrics = [
        _metrics("A", 100, 30, 50, 10),    # cheap but not clean
        _metrics("B", 50, 120, 50, 10),    # clean but expensive
    ]
    result = compute_css(metrics, PRESET_COST)
    a = next(r for r in result if r.country == "A")
    b = next(r for r in result if r.country == "B")
    assert a.css > b.css


def test_rank_countries_sorted_desc():
    entries = compute_css(
        [_metrics("X", 200, 90, 40, 15), _metrics("Y", 50, 60, 85, 5)],
        DEFAULT_WEIGHTS,
    )
    ranked = rank_countries(entries)
    assert ranked[0].css >= ranked[1].css


def test_compute_css_empty_returns_empty():
    assert compute_css([], DEFAULT_WEIGHTS) == []
