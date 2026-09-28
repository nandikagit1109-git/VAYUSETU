"""CPCB AQI breakpoints and categories (section 9.1).

Sub-index by linear interpolation within each band:
I = (Ihi-Ilo)/(BPhi-BPlo)*(C-BPlo)+Ilo. Values above the top band clamp to 500.
Overall AQI = max of the available sub-indices.
"""
from typing import Optional

# (concentration_low, concentration_high, index_low, index_high)
PM25_BANDS = [
    (0, 30, 0, 50),
    (30, 60, 51, 100),
    (60, 90, 101, 200),
    (90, 120, 201, 300),
    (120, 250, 301, 400),
    (250, float("inf"), 401, 500),
]
PM10_BANDS = [
    (0, 50, 0, 50),
    (50, 100, 51, 100),
    (100, 250, 101, 200),
    (250, 350, 201, 300),
    (350, 430, 301, 400),
    (430, float("inf"), 401, 500),
]


def sub_index(concentration: float, bands) -> float:
    if concentration is None:
        return float("nan")
    c = float(concentration)
    for lo, hi, ilo, ihi in bands:
        if hi == float("inf"):
            # Value above the top band clamps to 500 (section 9.1).
            return 500.0 if c >= lo else float(ilo)
        if c <= hi:
            if c < lo:
                # Below the first band lower edge (shouldn't happen with c >= 0).
                return float(ilo)
            return (ihi - ilo) / (hi - lo) * (c - lo) + ilo
    return 500.0


def pm25_sub_index(pm25: float) -> float:
    return min(500.0, sub_index(pm25, PM25_BANDS))


def pm10_sub_index(pm10: float) -> float:
    return min(500.0, sub_index(pm10, PM10_BANDS))


def compute_aqi(pm25: Optional[float], pm10: Optional[float]) -> Optional[float]:
    """Overall AQI = max of the available sub-indices, capped at 500."""
    import math

    values = []
    if pm25 is not None and not math.isnan(pm25):
        values.append(pm25_sub_index(pm25))
    if pm10 is not None and not math.isnan(pm10):
        values.append(pm10_sub_index(pm10))
    if not values:
        return None
    return float(min(500.0, max(values)))


def category(aqi: float) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"
