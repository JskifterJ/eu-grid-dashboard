"""
Life-cycle assessment for AI workloads.

Computes operational + embodied CO₂ for a given workload scenario.
All factors are defensible published / widely-cited estimates. See
docs/methodology.md for full citations.
"""
from typing import Optional

from app.models import LCABreakdown

# Embodied CO₂ per GPU unit (manufacturing only: die, packaging, HBM, board).
# Sources: NVIDIA ESG reports 2023-2024, academic estimates
# (Patterson et al. 2021, Strubell et al. 2019), industry LCA studies.
# Values are medians with ±20% uncertainty band.
GPU_EMBODIED_KG_CO2: dict[str, float] = {
    "A100":     900.0,
    "H100":    1300.0,
    "H200":    1400.0,
    "B200":    1900.0,
    "MI300X":  1500.0,
    "Gaudi3":  1100.0,
    "Groq-LPU": 600.0,
}

# IT power draw per GPU chip (kW) — excludes server overhead.
GPU_POWER_KW: dict[str, float] = {
    "A100":     0.40,
    "H100":     0.70,
    "H200":     0.70,
    "B200":     1.00,
    "MI300X":   0.75,
    "Gaudi3":   0.60,
    "Groq-LPU": 0.35,
}

# Datacenter building + HVAC + power infrastructure embodied carbon,
# amortized per kW of IT capacity per year. Median from LBNL + industry
# LCA studies: 5–10 kg CO₂/kW/yr range; we use 7.
DC_EMBODIED_KG_PER_KW_YEAR: float = 7.0

# Regional defaults for PUE (Power Usage Effectiveness).
# Lower = more efficient. Nordic benefits from free cooling.
DEFAULT_PUE_BY_COUNTRY: dict[str, float] = {
    # Nordic / cold climate — free cooling
    "NO": 1.10, "SE": 1.10, "FI": 1.10, "IS": 1.08, "DK": 1.15,
    # Northern & western EU
    "GB": 1.20, "IE": 1.20, "DE": 1.22, "BE": 1.20, "NL": 1.20,
    "PL": 1.25, "LU": 1.22, "EE": 1.18, "LV": 1.18, "LT": 1.20,
    # Central EU
    "FR": 1.25, "CH": 1.22, "AT": 1.25, "CZ": 1.27, "SK": 1.28,
    "SI": 1.30, "HU": 1.30,
    # Southern / hot climate
    "IT": 1.40, "ES": 1.40, "PT": 1.38, "GR": 1.45, "HR": 1.38,
    "BG": 1.40, "RO": 1.40, "RS": 1.40, "ME": 1.40, "MK": 1.42,
    "AL": 1.42, "BA": 1.40,
    # Island
    "CY": 1.45,
}
DEFAULT_PUE_FALLBACK: float = 1.30


def pue_for_country(country: str) -> float:
    """Return the region-default PUE for a country, or the global fallback."""
    return DEFAULT_PUE_BY_COUNTRY.get(country, DEFAULT_PUE_FALLBACK)


def lca_breakdown(
    mw: float,
    hours: float,
    co2_g_per_kwh: float,
    hardware: str = "H100",
    pue: Optional[float] = None,
    life_years: int = 3,
    country: Optional[str] = None,
) -> LCABreakdown:
    """Full lifecycle CO₂ breakdown for a workload scenario.

    Args:
        mw: IT power draw in MW (not total facility power — multiply by PUE for that).
        hours: workload duration in hours.
        co2_g_per_kwh: grid emission intensity at the run location.
        hardware: GPU generation — key into GPU_EMBODIED_KG_CO2 and GPU_POWER_KW.
        pue: datacenter PUE. If None, derived from country or DEFAULT_PUE_FALLBACK.
        life_years: GPU expected service life for amortization (default 3).
        country: ISO alpha-2 country code (used to pick default PUE if pue is None).
    """
    if hardware not in GPU_EMBODIED_KG_CO2:
        raise KeyError(f"unknown hardware {hardware!r}; expected one of {sorted(GPU_EMBODIED_KG_CO2)}")
    if pue is None:
        pue = pue_for_country(country) if country else DEFAULT_PUE_FALLBACK

    # Operational: MW × 1000 kW/MW × h (kWh) × g/kWh / 1000 g/kg = MW × h × g/kWh (kg).
    # PUE captures cooling + power-loss overhead.
    base_operational_kg = mw * 1000.0 * hours * co2_g_per_kwh / 1000.0  # = mw * hours * co2_g_per_kwh
    cooling_overhead_kg = base_operational_kg * (pue - 1.0)
    operational_co2_kg = base_operational_kg * pue

    # Embodied hardware: amortize manufacturing CO₂ of all GPUs drawing this MW over life.
    gpus_per_mw = 1000.0 / GPU_POWER_KW[hardware]  # e.g. 1000/0.7 ≈ 1429 for H100
    gpus_equivalent = mw * gpus_per_mw
    embodied_per_gpu_hour = GPU_EMBODIED_KG_CO2[hardware] / (life_years * 8760)
    embodied_hardware_kg = gpus_equivalent * embodied_per_gpu_hour * hours

    # Embodied datacenter: building + HVAC + power distribution, amortized.
    # mw × 1000 = kW of IT capacity; × hours / 8760 = fractional year of use.
    embodied_datacenter_kg = DC_EMBODIED_KG_PER_KW_YEAR * mw * 1000.0 * (hours / 8760.0)

    total_kg = operational_co2_kg + embodied_hardware_kg + embodied_datacenter_kg
    operational_share_pct = 100.0 * operational_co2_kg / total_kg if total_kg > 0 else 0.0

    return LCABreakdown(
        workload_mw=mw,
        workload_hours=hours,
        hardware=hardware,
        pue=round(pue, 3),
        life_years=life_years,
        operational_co2_kg=round(operational_co2_kg, 2),
        cooling_overhead_kg=round(cooling_overhead_kg, 2),
        embodied_hardware_kg=round(embodied_hardware_kg, 2),
        embodied_datacenter_kg=round(embodied_datacenter_kg, 2),
        total_kg=round(total_kg, 2),
        operational_share_pct=round(operational_share_pct, 2),
    )
