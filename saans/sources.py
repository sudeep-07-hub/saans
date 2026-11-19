"""
Source apportionment: what is actually in the air where you are.

Delhi-NCR numbers come from the TERI/ARAI 2018 study for the Ministry of Heavy
Industries (winter PM2.5 shares: transport 17-28%, industry 22-30%, biomass
14-15%, dust 17-38%, other 8-11%). Everywhere else uses a regional archetype,
explicitly labelled as such rather than pretending to street-level source
knowledge we do not have.
"""

from __future__ import annotations

from typing import Any

# Dominant contributors in winter. Ranges, not points, because the two modelling
# approaches in the study disagree by design and the honest answer is a range.
PROFILES: dict[str, dict[str, Any]] = {
    "delhi_ncr": {
        "label": "Delhi-NCR winter aerosol",
        "basis": "TERI/ARAI 2018 source apportionment (measured, 2016-17)",
        "winter": {
            "Traffic": (17, 28),
            "Industry": (22, 30),
            "Residential biomass": (14, 15),
            "Dust (road, soil, construction)": (17, 38),
            "Open burning & other": (8, 11),
        },
        "notes": [
            "Traffic is the largest single source in the city and the one a household can shift fastest.",
            "The biomass fraction is not mostly your neighbours' cooking: it includes rural kitchens and agricultural residue across the whole airshed.",
            "Dust balloons in summer; this winter profile is what you are breathing now.",
        ],
        "actions": [
            ("Shift one week of short car trips to metro or bus", "traffic", 0.4),
            ("Stop burning leaves, waste or wood in the open", "open burning", 0.5),
            ("Put a chimney or exhaust on a biomass stove, or switch fuel", "residential biomass", 0.5),
        ],
    },
    "indo_gangetic": {
        "label": "Indo-Gangetic plain city",
        "basis": "regional archetype (not city-measured)",
        "winter": {
            "Traffic": (15, 25),
            "Industry & brick kilns": (20, 30),
            "Residential biomass": (15, 25),
            "Dust": (15, 30),
            "Open burning & other": (5, 15),
        },
        "notes": [
            "Residential solid fuel runs higher here than in Delhi because more households cook on wood or dung.",
            "Brick kilns and small industry sit close to town and peak at night.",
        ],
        "actions": [
            ("Move the household off wood or dung cooking, or add a chimney today", "residential biomass", 0.5),
            ("Report a kiln or factory running without visible controls", "industry", 0.3),
        ],
    },
    "coastal_megacity": {
        "label": "Coastal megacity",
        "basis": "regional archetype (not city-measured)",
        "winter": {
            "Traffic": (30, 45),
            "Industry & ports": (15, 25),
            "Dust (construction)": (20, 30),
            "Waste & diesel gensets": (5, 15),
            "Marine & long-range": (5, 15),
        },
        "notes": [
            "Sea breeze scrubs the air most afternoons, so the evening peak matters more than the morning one.",
            "Construction dust is a bigger share than in inland cities.",
        ],
        "actions": [
            ("Take the suburban rail or metro for one regular trip", "traffic", 0.4),
            ("Ask your ward about water sprinkling on the construction corridor", "dust", 0.3),
        ],
    },
    "highland_valley": {
        "label": "Highland valley",
        "basis": "regional archetype (not city-measured)",
        "winter": {
            "Residential biomass & coal": (35, 50),
            "Traffic": (20, 30),
            "Brick kilns & industry": (10, 20),
            "Dust": (10, 20),
        },
        "notes": [
            "A valley traps its own air. What the town emits stays in the bowl for days.",
            "Home heating, not traffic, is usually the leading winter source.",
        ],
        "actions": [
            ("Insulate one room and stop burning wood or coal to heat it", "residential biomass", 0.6),
            ("Switch the household to LPG or electric cooking if it is still on solid fuel", "residential biomass", 0.4),
        ],
    },
    "clean_baseline": {
        "label": "Low-pollution city",
        "basis": "regional archetype (not city-measured)",
        "winter": {
            "Traffic": (35, 50),
            "Wood heating & garden burning": (15, 30),
            "Industry & power": (15, 25),
            "Long-range transport": (10, 20),
        },
        "notes": [
            "At these levels the household's own emissions matter more to its exposure than the city's.",
            "Indoor sources usually dominate: cooking, candles, incense, a badly ventilated kitchen.",
        ],
        "actions": [
            ("Ventilate the kitchen to outdoors, not into the next room", "indoor", 0.5),
            ("Swap the wood stove or fireplace for a closed, certified unit or a heat pump", "residential biomass", 0.4),
        ],
    },
}

# Which profile applies, by country and rough geography. Deliberately coarse:
# we would rather label a guess than present false precision.
#
# The Indian split follows the physical airshed, not state borders: the
# Indo-Gangetic plain is the northern river basin where winter inversion and
# agricultural burning dominate; the peninsula south of about 20°N has a
# different chemistry, a sea breeze on three sides, and much lower winter
# concentrations.
PENINSULAR = ("bengaluru", "bangalore", "chennai", "hyderabad", "coimbatore",
              "mysuru", "mysore", "kochi", "thiruvananthapuram", "madurai",
              "visakhapatnam", "vijayawada", "mangaluru", "goa", "panaji")
COASTAL = ("mumbai", "kolkata", "chennai", "kochi", "mangaluru", "goa", "panaji",
           "visakhapatnam", "puri", "bhubaneswar", "surat", "thane")


def pick_profile(country_code: str, lat: float, lon: float, label: str = "") -> str:
    cc = (country_code or "").upper()
    text = (label or "").lower()
    if "delhi" in text or "gurugram" in text or "noida" in text or "ghaziabad" in text or "faridabad" in text:
        return "delhi_ncr"
    if cc in ("IN", "PK", "BD", "NP"):
        if "kathmandu" in text or "pokhara" in text or "lahore" in text or "peshawar" in text:
            return "highland_valley"
        if any(c in text for c in COASTAL):
            return "coastal_megacity"
        # south of the Indo-Gangetic plain: the Deccan and the peninsula
        if lat < 20.0 or any(c in text for c in PENINSULAR):
            return "clean_baseline"
        if lat > 22.0 and lon > 74.0:
            return "indo_gangetic"
        return "clean_baseline"
    if cc in ("CN", "MN", "KZ", "UZ", "KG"):
        return "highland_valley"
    if cc in ("US", "CA", "GB", "DE", "FR", "NL", "BE", "AU", "NZ", "SE", "NO", "FI", "DK",
              "IE", "ES", "IT", "JP", "KR", "PT", "AT", "CH", "PL", "CZ"):
        return "clean_baseline"
    if cc in ("MX", "BR", "ZA", "TR", "IR", "IQ", "EG", "NG", "VN", "TH", "ID", "PH", "MY", "PE", "CL"):
        return "coastal_megacity"
    return "clean_baseline"


def profile_for(country_code: str, lat: float, lon: float, label: str = "") -> dict:
    key = pick_profile(country_code, lat, lon, label)
    p = PROFILES[key]
    winter = p["winter"]
    mid = {k: round(sum(v) / 2, 1) for k, v in winter.items()}
    total = sum(mid.values()) or 1
    return {
        "key": key,
        "label": p["label"],
        "basis": p["basis"],
        "shares": winter,
        "mid": {k: round(v / total * 100, 1) for k, v in mid.items()},
        "notes": p["notes"],
        "actions": [{"label": a, "targets": t, "weight": w} for a, t, w in p["actions"]],
        "verified_city": key == "delhi_ncr",
    }


def with_local_sources(profile: dict, indoor_pm25: float, outdoor_pm25: float) -> dict:
    """
    Add the household's own contribution. This is the point most air-quality
    apps miss: on a 150 ug/m3 day, a wood-burning kitchen is emitting a
    stronger local plume than anything the city is doing outside.
    """
    ratio = indoor_pm25 / outdoor_pm25 if outdoor_pm25 else 1.0
    note = None
    if ratio > 1.3:
        note = (f"Your indoor air ({indoor_pm25:g} ug/m3) is worse than the street outside "
                f"({outdoor_pm25:g}). The source is inside the house, not the sky.")
    elif ratio < 0.7:
        note = (f"Your indoor air ({indoor_pm25:g} ug/m3) is cleaner than outside "
                f"({outdoor_pm25:g}). The envelope and any filtration are doing real work.")
    out = dict(profile)
    out["indoor_vs_outdoor"] = round(ratio, 2)
    out["local_note"] = note
    return out
