import pytest
from app.forecast import mape, seasonal_baseline_values


def test_mape_perfect():
    assert mape([100, 200, 300], [100, 200, 300]) == pytest.approx(0.0)


def test_mape_ten_percent_off():
    actual = [100.0] * 5
    pred = [110.0] * 5
    assert mape(actual, pred) == pytest.approx(10.0, abs=0.001)


def test_mape_raises_on_length_mismatch():
    with pytest.raises(ValueError):
        mape([1, 2], [1, 2, 3])


def test_mape_raises_on_empty():
    with pytest.raises(ValueError):
        mape([], [])


def test_mape_skips_zero_actuals():
    # standard MAPE drops zero-actual points to avoid /0
    result = mape([0.0, 100.0], [10.0, 110.0])
    assert result == pytest.approx(10.0, abs=0.001)


def test_seasonal_baseline_averages_prior_weeks():
    # 4 weeks × 7 days × 24 hours history; baseline for same-hour-same-weekday
    # just returns the mean of the 4 prior-week same-hour values
    history = {
        # (weekday, hour) → list of prior same-slot values, newest first
        (1, 14): [50.0, 55.0, 45.0, 50.0],
    }
    out = seasonal_baseline_values(history)
    assert out[(1, 14)] == pytest.approx(50.0)
