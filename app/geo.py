"""
Population-weighted country centroids and serving-region centroids for the
inference simulator latency penalty. Coordinates are approximate (±1°) and
only need to be accurate enough to separate near vs far on a continent scale.
"""
from math import radians, sin, cos, sqrt, asin

COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "DE": (51.16, 10.45),
    "FR": (46.23, 2.21),
    "GB": (55.38, -3.44),
    "NO": (60.47, 8.47),
    "SE": (60.13, 18.64),
    "DK": (55.68, 12.57),
    "FI": (61.92, 25.75),
    "CH": (46.82, 8.23),
    "AT": (47.52, 14.55),
    "NL": (52.13, 5.29),
    "BE": (50.50, 4.47),
    "PL": (51.92, 19.13),
    "ES": (40.46, -3.75),
    "IT": (41.87, 12.57),
    "CZ": (49.82, 15.47),
    "PT": (39.40, -8.22),
    "RO": (45.94, 24.97),
    "GR": (39.07, 21.82),
    "IE": (53.41, -8.24),
    "HU": (47.16, 19.50),
}

SERVING_REGIONS: dict[str, tuple[float, float]] = {
    "central":  (49.0, 13.0),
    "western":  (50.0,  2.0),
    "northern": (59.0, 16.0),
    "southern": (42.0, 15.0),
    "iberian":  (40.0, -4.0),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_r, lat2_r = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def latency_penalty(country: str, region: str) -> float:
    """Return latency penalty in [0, 0.4] given candidate country and serving region."""
    if country not in COUNTRY_CENTROIDS:
        raise KeyError(country)
    if region not in SERVING_REGIONS:
        raise KeyError(region)
    c_lat, c_lon = COUNTRY_CENTROIDS[country]
    r_lat, r_lon = SERVING_REGIONS[region]
    d = haversine_km(c_lat, c_lon, r_lat, r_lon)
    raw = max(0.0, (d - 500.0) / 2500.0)
    return round(min(0.4, raw), 4)
