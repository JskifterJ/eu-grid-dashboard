"""
IEA physical-content-method primary energy factors, applied only to the
generation-mix visualization. See docs/methodology.md for citation.
"""

PRIMARY_ENERGY_FACTORS: dict[str, float] = {
    # Fossils (thermal conversion loss)
    "Coal": 2.7,
    "Lignite": 3.0,
    "Gas": 2.0,
    "Oil": 2.6,
    "Oil Shale": 2.6,
    "Peat": 2.9,
    # Nuclear (conventional thermal accounting)
    "Nuclear": 3.0,
    # Biomass / waste
    "Biomass": 1.2,
    "Waste": 1.1,
    # Renewables (physical-content method: factor = 1)
    "Wind": 1.0,
    "Solar": 1.0,
    "Hydro": 1.0,
    "Hydro Reservoir": 1.0,
    "Pumped Storage": 1.0,
    "Geothermal": 1.0,
    "Other Renewable": 1.0,
    "Other": 1.0,
}


def apply_pef(sources_gw: dict[str, float]) -> dict[str, float]:
    """Multiply each source's GW by its primary energy factor."""
    return {
        name: gw * PRIMARY_ENERGY_FACTORS.get(name, 1.0)
        for name, gw in sources_gw.items()
    }
