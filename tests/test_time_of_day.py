import pytest
from app.models import ForecastSeries, ForecastPoint
from app.time_of_day import best_contiguous_window, build_schedule


def _forecast(values):
    """Helper: build a ForecastSeries from a list of (co2, price) tuples."""
    return ForecastSeries(
        country="FR",
        points=[
            ForecastPoint(timestamp=f"2026-04-21T{h:02d}:00:00Z", co2_g_per_kwh=c, price_eur_mwh=p)
            for h, (c, p) in enumerate(values)
        ],
        source="market",
    )


def test_best_window_lowest_avg_co2():
    # Flat 40 except hours 2-4 are 20 (cheap) → best 3h window starts at hour 2
    values = [(40, 70) for _ in range(24)]
    values[2] = (20, 50); values[3] = (20, 50); values[4] = (20, 50)
    fc = _forecast(values)
    start, avg_co2, avg_price = best_contiguous_window(fc.points, window_hours=3, mode="min")
    assert start == 2
    assert avg_co2 == pytest.approx(20.0, abs=0.01)


def test_best_window_rounds_up_fractional_hours():
    # 2.5 hours rounds up to 3 for windowing
    values = [(40, 70) for _ in range(24)]
    values[0] = (10, 30); values[1] = (10, 30); values[2] = (10, 30)
    fc = _forecast(values)
    start, _, _ = best_contiguous_window(fc.points, window_hours=2.5, mode="min")
    assert start == 0


def test_worst_window_is_highest_avg():
    values = [(40, 70) for _ in range(24)]
    values[10] = (200, 250); values[11] = (200, 250); values[12] = (200, 250)
    fc = _forecast(values)
    start, avg_co2, _ = best_contiguous_window(fc.points, window_hours=3, mode="max")
    assert start == 10
    assert avg_co2 == pytest.approx(200.0, abs=0.01)


def test_build_schedule_full_shape():
    values = [(40, 70) for _ in range(24)]
    values[2] = (10, 40); values[3] = (10, 40); values[4] = (10, 40)
    values[14] = (300, 200); values[15] = (300, 200); values[16] = (300, 200)
    fc = _forecast(values)
    result = build_schedule(fc, mw=10.0, workload_hours=3.0)
    assert result.country == "FR"
    assert len(result.hours) == 24
    # Best should be the 3h cheapest window (hours 2-4, avg 10 g/kWh)
    assert result.best_window.avg_co2_g_per_kwh == pytest.approx(10.0, abs=0.01)
    # Worst should be the 3h dirtiest window (hours 14-16, avg 300 g/kWh)
    assert result.worst_window.avg_co2_g_per_kwh == pytest.approx(300.0, abs=0.01)
    # Savings: (300 - 10) / 300 × 100 = 96.67%
    assert result.co2_savings_pct == pytest.approx(96.67, abs=0.1)
    # 10 MW × 3 h × 10 g/kWh / 1000 × 1000 = 300 kg (best workload co2)
    # but note: mw × hours × g/kWh gives kg (see Plan C Task 1)
    assert result.best_window.total_co2_kg == pytest.approx(10 * 3 * 10, abs=0.1)


def test_build_schedule_savings_are_positive():
    # Even with identical hours, savings should be 0 and valid
    values = [(40, 70) for _ in range(24)]
    fc = _forecast(values)
    result = build_schedule(fc, mw=10.0, workload_hours=3.0)
    assert result.co2_savings_pct == pytest.approx(0.0, abs=0.01)
    assert result.co2_savings_kg == pytest.approx(0.0, abs=0.01)


def test_build_schedule_rejects_workload_too_long():
    values = [(40, 70) for _ in range(24)]
    fc = _forecast(values)
    with pytest.raises(ValueError):
        build_schedule(fc, mw=10.0, workload_hours=25.0)


def test_build_schedule_rejects_empty_forecast():
    fc = ForecastSeries(country="FR", points=[], source="market")
    with pytest.raises(ValueError):
        build_schedule(fc, mw=10.0, workload_hours=3.0)
