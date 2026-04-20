from app.primary_energy import PRIMARY_ENERGY_FACTORS, apply_pef


def test_renewables_have_pef_one():
    for s in ["Wind", "Solar", "Hydro", "Hydro Reservoir", "Pumped Storage"]:
        assert PRIMARY_ENERGY_FACTORS[s] == 1.0


def test_fossils_have_pef_greater_than_one():
    assert PRIMARY_ENERGY_FACTORS["Coal"] > 2.0
    assert PRIMARY_ENERGY_FACTORS["Lignite"] > PRIMARY_ENERGY_FACTORS["Coal"]
    assert PRIMARY_ENERGY_FACTORS["Gas"] >= 2.0
    assert PRIMARY_ENERGY_FACTORS["Nuclear"] >= 2.8


def test_apply_pef_inflates_fossils():
    raw = {"Wind": 10.0, "Coal": 10.0}
    inflated = apply_pef(raw)
    assert inflated["Wind"] == 10.0
    assert inflated["Coal"] == 27.0


def test_apply_pef_unknown_source_defaults_to_one():
    raw = {"Exotic Thing": 5.0}
    inflated = apply_pef(raw)
    assert inflated["Exotic Thing"] == 5.0
