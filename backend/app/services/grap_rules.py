"""Static AQI threshold -> GRAP action mapping.

Severity bands follow CPCB; action text summarises the real GRAP (Graded
Response Action Plan) stage measures for the demo.
"""

GRAP_ACTIONS = {
    "Moderate": (
        "No GRAP stage invoked. Maintain enhanced monitoring, mechanized road "
        "sweeping and water sprinkling at identified dust hotspots; advise "
        "residents to reduce prolonged outdoor exertion."
    ),
    "Poor": (
        "GRAP Stage-I: intensified enforcement against open burning of waste "
        "and biomass; increased mechanized road cleaning and water sprinkling; "
        "strict pollution checks at border entry points; regulated entry of "
        "commercial diesel vehicles; advisory for mask use outdoors."
    ),
    "Very Poor": (
        "GRAP Stage-II: all Stage-I measures plus ban on diesel generator sets "
        "(except essential services); halt of construction and demolition in "
        "linear public projects; work-from-home advisory for up to 50% of "
        "government and private office staff; enhanced public transport service."
    ),
    "Severe": (
        "GRAP Stage-III/IV: all Stage-II measures plus halt of all construction "
        "and demolition activity; restriction on BS-III petrol and BS-IV diesel "
        "vehicles in the NCR; no-entry for trucks except essential commodities; "
        "closure advisory for schools and institutions; stoppage of industrial "
        "activity using fossil fuels in hotspots."
    ),
}


def severity_for_aqi(aqi: float) -> str:
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"


def grap_action_for_aqi(aqi: float) -> tuple[str, str]:
    """Returns (severity, grap_action) for an AQI value."""
    severity = severity_for_aqi(aqi)
    return severity, GRAP_ACTIONS[severity]
