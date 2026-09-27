"""Master city table for VayuSetu.

This is the single source of truth for which cities the product covers: their
coordinates and the parameters used to synthesise their historical AQI series.
`app.config` derives its lookup dicts from here, and the seed data generator at
the repository root imports this module directly.

ORDER IS LOAD-BEARING: seed_data_generator draws its random noise sequentially
from one global `np.random.seed(42)`, so a city's series only stays reproducible
if every city before it keeps its position. Delhi, Kanpur and Pune must remain
the first three entries, and new cities are appended at the end.

The AQI parameters are demo-scale approximations of each city's reported
pollution level (base), the strength of its morning/evening traffic cycle (amp),
its weekday/weekend swing (weekly) and day-to-day variability (noise). They are
not measurements.
"""

# key, label, latitude, longitude, base AQI, diurnal amplitude, weekly swing, noise
CITY_TABLE: list[dict] = [
    # --- federated training cohort (must stay first, see module docstring) ---
    {"key": "delhi", "label": "Delhi", "lat": 28.6139, "lon": 77.2090, "base": 190.0, "amp": 55.0, "weekly": 18.0, "noise": 14.0},
    {"key": "kanpur", "label": "Kanpur", "lat": 26.4499, "lon": 80.3319, "base": 155.0, "amp": 45.0, "weekly": 15.0, "noise": 12.0},
    {"key": "pune", "label": "Pune", "lat": 18.5204, "lon": 73.8567, "base": 90.0, "amp": 30.0, "weekly": 10.0, "noise": 9.0},
    # --- metros and largest urban centres ---
    {"key": "mumbai", "label": "Mumbai", "lat": 19.0760, "lon": 72.8777, "base": 110.0, "amp": 32.0, "weekly": 12.0, "noise": 10.0},
    {"key": "bengaluru", "label": "Bengaluru", "lat": 12.9716, "lon": 77.5946, "base": 80.0, "amp": 26.0, "weekly": 9.0, "noise": 8.0},
    {"key": "hyderabad", "label": "Hyderabad", "lat": 17.3850, "lon": 78.4867, "base": 105.0, "amp": 30.0, "weekly": 11.0, "noise": 9.0},
    {"key": "ahmedabad", "label": "Ahmedabad", "lat": 23.0225, "lon": 72.5714, "base": 140.0, "amp": 40.0, "weekly": 14.0, "noise": 11.0},
    {"key": "chennai", "label": "Chennai", "lat": 13.0827, "lon": 80.2707, "base": 95.0, "amp": 28.0, "weekly": 10.0, "noise": 9.0},
    {"key": "kolkata", "label": "Kolkata", "lat": 22.5726, "lon": 88.3639, "base": 150.0, "amp": 44.0, "weekly": 15.0, "noise": 12.0},
    {"key": "surat", "label": "Surat", "lat": 21.1702, "lon": 72.8311, "base": 120.0, "amp": 34.0, "weekly": 12.0, "noise": 10.0},
    {"key": "jaipur", "label": "Jaipur", "lat": 26.9124, "lon": 75.7873, "base": 182.0, "amp": 52.0, "weekly": 15.0, "noise": 12.0},
    {"key": "lucknow", "label": "Lucknow", "lat": 26.8467, "lon": 80.9462, "base": 192.0, "amp": 55.0, "weekly": 16.0, "noise": 13.0},
    {"key": "nagpur", "label": "Nagpur", "lat": 21.1458, "lon": 79.0882, "base": 125.0, "amp": 36.0, "weekly": 12.0, "noise": 10.0},
    {"key": "indore", "label": "Indore", "lat": 22.7196, "lon": 75.8573, "base": 130.0, "amp": 37.0, "weekly": 13.0, "noise": 11.0},
    # --- state capitals and major tier-2 cities ---
    # The Gangetic-plain cities below carry the highest bases in the table, which
    # is both true to life and what makes the GRAP threshold checker demonstrably
    # fire: their forecast peaks cross AQI 200 inside the next-24h window.
    {"key": "bhopal", "label": "Bhopal", "lat": 23.2599, "lon": 77.4126, "base": 128.0, "amp": 36.0, "weekly": 12.0, "noise": 10.0},
    {"key": "patna", "label": "Patna", "lat": 25.5941, "lon": 85.1376, "base": 200.0, "amp": 58.0, "weekly": 17.0, "noise": 13.0},
    {"key": "ludhiana", "label": "Ludhiana", "lat": 30.9009, "lon": 75.8573, "base": 205.0, "amp": 60.0, "weekly": 18.0, "noise": 14.0},
    {"key": "chandigarh", "label": "Chandigarh", "lat": 30.7333, "lon": 76.7794, "base": 150.0, "amp": 44.0, "weekly": 15.0, "noise": 12.0},
    {"key": "agra", "label": "Agra", "lat": 27.1767, "lon": 78.0081, "base": 195.0, "amp": 56.0, "weekly": 16.0, "noise": 13.0},
    {"key": "varanasi", "label": "Varanasi", "lat": 25.3176, "lon": 82.9739, "base": 188.0, "amp": 54.0, "weekly": 16.0, "noise": 12.0},
    {"key": "nashik", "label": "Nashik", "lat": 19.9975, "lon": 73.7898, "base": 100.0, "amp": 30.0, "weekly": 10.0, "noise": 9.0},
    {"key": "vadodara", "label": "Vadodara", "lat": 22.3072, "lon": 73.1812, "base": 122.0, "amp": 34.0, "weekly": 12.0, "noise": 10.0},
    {"key": "jodhpur", "label": "Jodhpur", "lat": 26.2389, "lon": 73.0243, "base": 152.0, "amp": 44.0, "weekly": 14.0, "noise": 12.0},
    {"key": "ranchi", "label": "Ranchi", "lat": 23.3441, "lon": 85.3096, "base": 115.0, "amp": 32.0, "weekly": 11.0, "noise": 10.0},
    {"key": "bhubaneswar", "label": "Bhubaneswar", "lat": 20.2961, "lon": 85.8245, "base": 112.0, "amp": 32.0, "weekly": 11.0, "noise": 10.0},
    {"key": "raipur", "label": "Raipur", "lat": 21.2514, "lon": 81.6296, "base": 126.0, "amp": 36.0, "weekly": 12.0, "noise": 10.0},
    {"key": "guwahati", "label": "Guwahati", "lat": 26.1445, "lon": 91.7362, "base": 105.0, "amp": 30.0, "weekly": 10.0, "noise": 9.0},
    {"key": "coimbatore", "label": "Coimbatore", "lat": 11.0168, "lon": 76.9558, "base": 78.0, "amp": 24.0, "weekly": 8.0, "noise": 8.0},
    {"key": "thiruvananthapuram", "label": "Thiruvananthapuram", "lat": 8.5241, "lon": 76.9366, "base": 70.0, "amp": 22.0, "weekly": 8.0, "noise": 7.0},
    {"key": "vijayawada", "label": "Vijayawada", "lat": 16.5062, "lon": 80.6480, "base": 98.0, "amp": 28.0, "weekly": 10.0, "noise": 9.0},
    {"key": "dehradun", "label": "Dehradun", "lat": 30.3165, "lon": 78.0322, "base": 140.0, "amp": 42.0, "weekly": 13.0, "noise": 11.0},
    {"key": "srinagar", "label": "Srinagar", "lat": 34.0837, "lon": 74.7973, "base": 132.0, "amp": 44.0, "weekly": 13.0, "noise": 11.0},
    {"key": "shimla", "label": "Shimla", "lat": 31.1048, "lon": 77.1734, "base": 85.0, "amp": 26.0, "weekly": 9.0, "noise": 8.0},
    {"key": "panaji", "label": "Panaji", "lat": 15.4909, "lon": 73.8278, "base": 72.0, "amp": 22.0, "weekly": 8.0, "noise": 7.0},
    {"key": "puducherry", "label": "Puducherry", "lat": 11.9416, "lon": 79.8083, "base": 88.0, "amp": 26.0, "weekly": 9.0, "noise": 8.0},
    {"key": "imphal", "label": "Imphal", "lat": 24.8170, "lon": 93.9368, "base": 92.0, "amp": 28.0, "weekly": 10.0, "noise": 9.0},
    {"key": "shillong", "label": "Shillong", "lat": 25.5788, "lon": 91.8933, "base": 76.0, "amp": 24.0, "weekly": 8.0, "noise": 7.0},
    {"key": "agartala", "label": "Agartala", "lat": 23.8315, "lon": 91.2868, "base": 84.0, "amp": 26.0, "weekly": 9.0, "noise": 8.0},
    {"key": "aizawl", "label": "Aizawl", "lat": 23.7271, "lon": 92.7176, "base": 80.0, "amp": 24.0, "weekly": 8.0, "noise": 8.0},
    {"key": "kohima", "label": "Kohima", "lat": 25.6751, "lon": 94.1083, "base": 82.0, "amp": 24.0, "weekly": 8.0, "noise": 8.0},
    {"key": "itanagar", "label": "Itanagar", "lat": 27.0840, "lon": 93.6050, "base": 90.0, "amp": 26.0, "weekly": 9.0, "noise": 9.0},
    {"key": "gangtok", "label": "Gangtok", "lat": 27.3389, "lon": 88.6065, "base": 78.0, "amp": 24.0, "weekly": 8.0, "noise": 7.0},
    {"key": "leh", "label": "Leh", "lat": 34.1526, "lon": 77.5771, "base": 62.0, "amp": 28.0, "weekly": 8.0, "noise": 6.0},
    {"key": "port_blair", "label": "Port Blair", "lat": 11.6234, "lon": 92.7265, "base": 55.0, "amp": 18.0, "weekly": 6.0, "noise": 5.0},
]

CITY_KEYS: list[str] = [c["key"] for c in CITY_TABLE]

CITY_LABELS: dict[str, str] = {c["key"]: c["label"] for c in CITY_TABLE}

# The federated cohort stays at three cities on purpose: a Flower/Ray simulation
# scales linearly in clients, and a convergence chart with forty local loss lines
# is unreadable. Every other city still reports, forecasts and alerts.
FEDERATED_CITIES: tuple[str, ...] = ("delhi", "kanpur", "pune")


def city_params(key: str) -> dict | None:
    for c in CITY_TABLE:
        if c["key"] == key:
            return c
    return None
