import pytest

from app.lca import (
    GPU_EMBODIED_KG_CO2, GPU_POWER_KW, DEFAULT_PUE_BY_COUNTRY, DEFAULT_PUE_FALLBACK,
    DC_EMBODIED_KG_PER_KW_YEAR, pue_for_country, lca_breakdown,
)


def test_embodied_constants_present():
    for gpu in ["A100", "H100", "H200", "B200", "MI300X"]:
        assert gpu in GPU_EMBODIED_KG_CO2
        assert gpu in GPU_POWER_KW


def test_gpu_embodied_ordering_newer_is_higher():
    # Newer, larger dies generally have higher embodied CO₂
    assert GPU_EMBODIED_KG_CO2["B200"] > GPU_EMBODIED_KG_CO2["H100"] > GPU_EMBODIED_KG_CO2["A100"]


def test_dc_embodied_in_reasonable_range():
    assert 3 < DC_EMBODIED_KG_PER_KW_YEAR < 15


def test_pue_for_country_nordic():
    assert pue_for_country("NO") <= 1.15
    assert pue_for_country("SE") <= 1.15
    assert pue_for_country("FI") <= 1.15
    assert pue_for_country("IS") <= 1.15


def test_pue_for_country_southern_higher():
    assert pue_for_country("IT") > pue_for_country("DE")
    assert pue_for_country("ES") > pue_for_country("DK")
    assert pue_for_country("CY") > pue_for_country("FR")


def test_pue_for_unknown_falls_back_default():
    assert pue_for_country("XX") == DEFAULT_PUE_FALLBACK


def test_lca_breakdown_operational_math():
    # 10 MW × 6h × 40 g/kWh × PUE 1.2 / 1000 = 2.88 kg (wait — gram math)
    # 10 MW = 10,000 kW × 6 h = 60,000 kWh × 40 g/kWh = 2,400,000 g = 2400 kg
    # × PUE 1.2 = 2880 kg
    result = lca_breakdown(
        mw=10.0, hours=6.0, co2_g_per_kwh=40.0,
        hardware="H100", pue=1.2, life_years=3, country=None,
    )
    assert result.operational_co2_kg == pytest.approx(2880.0, abs=1)


def test_lca_breakdown_cooling_overhead_is_subset_of_operational():
    # When PUE = 1.2, cooling overhead is 20% of base (non-overhead) operational
    # base = mw × h × co2/1000; overhead = base × (pue - 1); so overhead = (2400) × 0.2 = 480
    result = lca_breakdown(
        mw=10.0, hours=6.0, co2_g_per_kwh=40.0,
        hardware="H100", pue=1.2, life_years=3, country=None,
    )
    assert result.cooling_overhead_kg == pytest.approx(480.0, abs=1)
    # And operational = base + cooling = 2400 + 480 = 2880
    assert result.operational_co2_kg - result.cooling_overhead_kg == pytest.approx(2400.0, abs=1)


def test_lca_breakdown_embodied_hardware_scales_with_workload():
    small = lca_breakdown(
        mw=1.0, hours=1.0, co2_g_per_kwh=40.0, hardware="H100", pue=1.2, life_years=3, country=None,
    )
    big = lca_breakdown(
        mw=10.0, hours=10.0, co2_g_per_kwh=40.0, hardware="H100", pue=1.2, life_years=3, country=None,
    )
    assert big.embodied_hardware_kg == pytest.approx(100 * small.embodied_hardware_kg, rel=0.01)


def test_lca_breakdown_hardware_choice_changes_embodied():
    h100 = lca_breakdown(mw=10.0, hours=6.0, co2_g_per_kwh=40.0, hardware="H100", pue=1.2, life_years=3, country=None)
    b200 = lca_breakdown(mw=10.0, hours=6.0, co2_g_per_kwh=40.0, hardware="B200", pue=1.2, life_years=3, country=None)
    # B200 has higher embodied CO₂ but also higher per-chip power, so fewer chips per MW
    # Net effect: embodied_hw should differ between the two
    assert h100.embodied_hardware_kg != b200.embodied_hardware_kg


def test_lca_breakdown_total_is_sum_of_parts():
    result = lca_breakdown(mw=10.0, hours=6.0, co2_g_per_kwh=40.0, hardware="H100", pue=1.2, life_years=3, country=None)
    expected_total = result.operational_co2_kg + result.embodied_hardware_kg + result.embodied_datacenter_kg
    assert result.total_kg == pytest.approx(expected_total, rel=0.001)


def test_lca_breakdown_uses_country_pue_when_pue_none():
    # NO has PUE ~1.1; DE has ~1.2; so same workload in NO should have lower operational
    no = lca_breakdown(mw=10.0, hours=6.0, co2_g_per_kwh=40.0, hardware="H100", pue=None, life_years=3, country="NO")
    de = lca_breakdown(mw=10.0, hours=6.0, co2_g_per_kwh=40.0, hardware="H100", pue=None, life_years=3, country="DE")
    assert no.operational_co2_kg < de.operational_co2_kg
    assert no.pue < de.pue


def test_lca_breakdown_unknown_hardware_raises():
    with pytest.raises(KeyError):
        lca_breakdown(mw=10.0, hours=6.0, co2_g_per_kwh=40.0, hardware="FakeGPU", pue=1.2, life_years=3, country=None)


def test_operational_share_pct_in_range():
    r = lca_breakdown(mw=10.0, hours=6.0, co2_g_per_kwh=40.0, hardware="H100", pue=1.2, life_years=3, country=None)
    assert 0 < r.operational_share_pct < 100
