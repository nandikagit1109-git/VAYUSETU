# Summarised paraphrase for demonstration. Verify against the latest CAQM GRAP notification before any real-world use.

"""Static action table (section 9.3).

NCR cities (ncr=1 in the registry) use the GRAP framework with stages; all
other cities get a generic advisory. Action strings are short paraphrases —
see the notice at the top of this file.
"""

# GRAP stages by predicted AQI (NCR cities).
GRAP_STAGES = [
    (201, 300, "Stage I"),
    (301, 400, "Stage II"),
    (401, 450, "Stage III"),
    (451, 10_000, "Stage IV"),
]

ADVISORY = "ADVISORY"
GRAP = "GRAP"

_STAGE_ACTIONS: dict[str, str] = {
    "Stage I": (
        "Enforce dust control at construction sites and on roads; ban open burning "
        "of waste and biomass; increase mechanised sweeping and water sprinkling; "
        "tighten vehicle emission checks"
    ),
    "Stage II": (
        "All Stage I actions, plus restrict diesel generator use to essential "
        "services, raise parking fees to discourage private vehicles, and increase "
        "metro and bus frequency"
    ),
    "Stage III": (
        "All Stage II actions, plus halt non-essential construction and demolition "
        "and restrict polluting commercial vehicles"
    ),
    "Stage IV": (
        "All Stage III actions, plus stop entry of non-essential trucks and consider "
        "restrictions on private vehicles and work-from-home for offices"
    ),
}

_ADVISORY_ACTIONS: dict[str, str] = {
    "moderate": (
        "Public health advisory for sensitive groups; intensify dust suppression; "
        "enforce the ban on open waste burning"
    ),
    "high": (
        "All of the above, plus notify the state pollution control board to inspect "
        "nearby industrial and burning hotspots; increase public transport frequency"
    ),
    "extreme": (
        "Emergency health advisory; pause dust-generating construction; deploy "
        "inspection teams to hotspots"
    ),
}


def action_for(predicted_aqi: float, ncr: bool) -> tuple[str, str | None, str]:
    """Returns (action_framework, grap_stage_or_None, action_text)."""
    if ncr:
        for lo, hi, stage in GRAP_STAGES:
            if lo <= predicted_aqi <= hi:
                return GRAP, stage, _STAGE_ACTIONS[stage]
        # Below 201 should never reach here (alerts only fire above 200).
        return GRAP, "Stage I", _STAGE_ACTIONS["Stage I"]
    if predicted_aqi <= 300:
        return ADVISORY, None, _ADVISORY_ACTIONS["moderate"]
    if predicted_aqi <= 400:
        return ADVISORY, None, _ADVISORY_ACTIONS["high"]
    return ADVISORY, None, _ADVISORY_ACTIONS["extreme"]


def channels_for(severity: str) -> list[str]:
    """Dashboard always; simulated SMS added for Very Poor and Severe.
    No real SMS is sent in v2 — the UI labels these as simulated."""
    chans = ["dashboard"]
    if severity in ("Very Poor", "Severe"):
        chans.append("sms_simulated")
    return chans
