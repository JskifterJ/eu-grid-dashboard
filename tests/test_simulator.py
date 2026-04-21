import pytest
from app.simulator import simulate, SimulatorInputs
from app.models import ForecastPoint, ForecastSeries
from app.scoring import CountryMetrics, compute_css, DEFAULT_WEIGHTS


def _metrics_grid():
    # Two countries, clean/cheap FR vs dirty/expensive PL
    return [
        CountryMetrics("FR", 40, 70, 90, 5),
        CountryMetrics("PL", 600, 120, 15, 30),
    ]


def _forecast_fr():
    return ForecastSeries(
        country="FR",
        points=[
            ForecastPoint(timestamp=f"2026-04-20T{h:02d}:00:00Z", co2_g_per_kwh=40.0 + h, price_eur_mwh=70.0 + h)
            for h in range(24)
        ],
        source="market",
    )


def test_training_emissions_math():
    result = simulate(SimulatorInputs(
        workload="training", country="FR", mw=10.0, hours=6.0,
        start="2026-04-20T14:00:00Z", hub_country="PL", serving_region=None,
    ), metrics_grid=_metrics_grid(), forecast=_forecast_fr(), css_results=compute_css(_metrics_grid(), DEFAULT_WEIGHTS))

    # current emissions use forecast value at start (T14 → co2=54, price=84)
    # 10 MW × 6 h × 54 g/kWh / 1000 = 3.24 t
    assert result.current_hour_t_co2 == pytest.approx(3.24, abs=0.01)
    assert result.current_hour_cost_eur == pytest.approx(10 * 6 * 84.0, abs=0.01)
    # hub (PL) should be much worse
    assert result.hub_t_co2 > result.current_hour_t_co2


def test_training_best_hour_picked():
    result = simulate(SimulatorInputs(
        workload="training", country="FR", mw=10.0, hours=6.0,
        start="2026-04-20T14:00:00Z", hub_country="PL", serving_region=None,
    ), metrics_grid=_metrics_grid(), forecast=_forecast_fr(), css_results=compute_css(_metrics_grid(), DEFAULT_WEIGHTS))

    # forecast CO₂ ascends with hour → best hour is hour 0
    assert result.best_hour_start == "2026-04-20T00:00:00Z"
    assert result.best_hour_t_co2 < result.current_hour_t_co2


def test_inference_mode_has_no_best_hour():
    result = simulate(SimulatorInputs(
        workload="inference", country="FR", mw=1.0, hours=24.0,
        start="2026-04-20T14:00:00Z", hub_country="PL", serving_region="western",
    ), metrics_grid=_metrics_grid(), forecast=_forecast_fr(), css_results=compute_css(_metrics_grid(), DEFAULT_WEIGHTS))

    assert result.best_hour_t_co2 is None
    assert result.best_hour_cost_eur is None


def test_inference_latency_penalty_applied():
    r_close = simulate(SimulatorInputs(
        workload="inference", country="FR", mw=1.0, hours=24.0,
        start="2026-04-20T14:00:00Z", hub_country="PL", serving_region="western",
    ), metrics_grid=_metrics_grid(), forecast=_forecast_fr(), css_results=compute_css(_metrics_grid(), DEFAULT_WEIGHTS))

    r_far = simulate(SimulatorInputs(
        workload="inference", country="FR", mw=1.0, hours=24.0,
        start="2026-04-20T14:00:00Z", hub_country="PL", serving_region="northern",
    ), metrics_grid=_metrics_grid(), forecast=_forecast_fr(), css_results=compute_css(_metrics_grid(), DEFAULT_WEIGHTS))

    assert r_far.latency_penalty > r_close.latency_penalty
