"""
CPCB National Air Quality Index (India) and the GRAP stages that follow from it.

Breakpoints: CPCB "About AQI" (8 pollutants, 24-hour averaging) and
"How is AQI Calculated?" (cpcbccr.com). The sub-index is a linear
interpolation inside each band; the overall AQI is the worst sub-index, and
that pollutant is the "dominant pollutant".
"""

from __future__ import annotations

from dataclasses import dataclass

# CPCB bands. The index has a gap between categories (50 -> 51), so the
# concentration bound of each higher band starts one unit above the previous
# band's ceiling. That is what makes the official worked examples come out
# exactly: 31 -> 51, 45 -> 75, 60 -> 100.
PM25_BREAKPOINTS = [
    (0, 30, 0, 50),
    (31, 60, 51, 100),
    (61, 90, 101, 200),
    (91, 120, 201, 300),
    (121, 250, 301, 400),
    (251, 1000, 401, 500),
]
PM10_BREAKPOINTS = [
    (0, 50, 0, 50),
    (51, 100, 51, 100),
    (101, 250, 101, 200),
    (251, 350, 201, 300),
    (351, 430, 301, 400),
    (431, 2000, 401, 500),
]
NO2_BREAKPOINTS = [
    (0, 40, 0, 50),
    (41, 80, 51, 100),
    (81, 180, 101, 200),
    (181, 280, 201, 300),
    (281, 400, 301, 400),
    (401, 2000, 401, 500),
]

CATEGORIES = [
    (0, 50, "Good", "good"),
    (51, 100, "Satisfactory", "satisfactory"),
    (101, 200, "Moderate", "moderate"),
    (201, 300, "Poor", "poor"),
    (301, 400, "Very Poor", "very_poor"),
    (401, 500, "Severe", "severe"),
]

# Advisory text mirrors the CPCB health statements, condensed.
HEALTH = {
    "good": "Air is clean enough for normal outdoor activity.",
    "satisfactory": "Fine for most people. Very sensitive people may notice mild irritation.",
    "moderate": "Children, older adults and people with asthma should ease off long outdoor exertion.",
    "poor": "Breathing discomfort on prolonged exertion. Cut outdoor exercise and mask if you must be on the road.",
    "very_poor": "Respiratory illness on prolonged exposure. Keep outdoor time short, filter indoor air, mask outside.",
    "severe": "Serious risk for everyone. Stay indoors in filtered air, cancel outdoor activity, watch children and elders.",
}


def sub_index(conc: float, breakpoints) -> float:
    """Linear interpolation inside the CPCB band, as the standard defines it."""
    if conc is None:
        return 0.0
    c = max(0.0, float(conc))
    for c_lo, c_hi, i_lo, i_hi in breakpoints:
        if c <= c_hi:
            if c_hi == c_lo:
                return float(i_hi)
            return i_lo + (i_hi - i_lo) * (c - c_lo) / (c_hi - c_lo)
    # Beyond 500: keep extrapolating with the last band's slope so the number
    # stays ordered instead of saturating at 500.
    c_lo, c_hi, i_lo, i_hi = breakpoints[-1]
    slope = (i_hi - i_lo) / (c_hi - c_lo)
    return i_hi + slope * (c - c_hi)


def category(aqi: float) -> tuple[str, str]:
    """Return (label, slug) for an AQI value."""
    a = max(0.0, float(aqi or 0))
    for lo, hi, label, slug in CATEGORIES:
        if a <= hi:
            return label, slug
    return "Severe", "severe"


def compute(pm25=None, pm10=None, no2=None) -> dict:
    """CPCB AQI from whatever pollutants we have. Dominant pollutant included."""
    parts = {}
    if pm25 is not None:
        parts["PM2.5"] = sub_index(pm25, PM25_BREAKPOINTS)
    if pm10 is not None:
        parts["PM10"] = sub_index(pm10, PM10_BREAKPOINTS)
    if no2 is not None:
        parts["NO2"] = sub_index(no2, NO2_BREAKPOINTS)
    if not parts:
        return {"aqi": 0, "label": "Unknown", "slug": "moderate", "dominant": None, "sub_indices": {}}
    dominant = max(parts, key=parts.get)
    aqi = round(parts[dominant])
    label, slug = category(aqi)
    return {
        "aqi": aqi,
        "label": label,
        "slug": slug,
        "dominant": dominant,
        "sub_indices": {k: round(v) for k, v in parts.items()},
        "health": HEALTH[slug],
    }


# ---------------------------------------------------------------------------
# GRAP - the Delhi-NCR Graded Response Action Plan, keyed to Delhi AQI.
# CAQM schedule: Stage I 201-300, II 301-400, III 401-450, IV >450.
# ---------------------------------------------------------------------------
GRAP = [
    (201, 300, "I", "GRAP I - Poor",
     "Dust control, no open burning, strict PUC enforcement. Construction sites under scrutiny."),
    (301, 400, "II", "GRAP II - Very Poor",
     "Stricter dust control, higher parking fees, staggered office timings. Consider cutting non-essential car trips."),
    (401, 450, "III", "GRAP III - Severe",
     "BS-III petrol and BS-IV diesel cars restricted in Delhi and four NCR districts. Construction paused. Primary classes may go online."),
    (451, 10_000, "IV", "GRAP IV - Severe Plus",
     "Trucks restricted, non-essential commercial activity may pause, odd-even possible. Work from home if you can."),
]

_NO_STAGE = {
    "stage": "none",
    "label": "No GRAP stage in force",
    "detail": "Normal activity. This app still works because PM2.5 above 15 ug/m3 is already above the WHO guideline.",
    "applies": False,
}


def is_ncr(lat: float, lon: float, label: str = "", cc: str = "IN") -> bool:
    """
    Is this inside the National Capital Region, where GRAP is in force?

    A bounding box around Delhi plus the named NCR towns. Being generous here
    only means someone sees an extra line of policy; being wrong the other way
    would hide an active restriction from a household it applies to.
    """
    if (cc or "").upper() != "IN":
        return False
    text = (label or "").lower()
    named = ("delhi", "new delhi", "gurugram", "gurgaon", "noida", "ghaziabad",
             "faridabad", "greater noida", "sonipat", "panipat", "rohtak", "meerut",
             "baghpat", "hapur", "bulandshahr", "karnal", "mewat", "nuh", "palwal",
             "rewari", "jhajjar", "charkhi dadri", "bhiwani", "mahendragarh", "jind",
             "chandigarh", "mohali", "panchkula", "alwar", "bharatpur", "koshi")
    if any(c in text for c in named):
        return True
    # the NCR core, roughly 27.5-29.5 N and 76.0-78.5 E
    return 27.4 <= lat <= 29.6 and 75.9 <= lon <= 78.6


def grap_stage(aqi: float, in_ncr: bool = True) -> dict:
    """
    GRAP applies to Delhi-NCR only.

    Reporting a Delhi emergency regulation for Chennai would be both wrong and
    confusing, so outside the National Capital Region the stage is suppressed
    and the app says the city has no equivalent scheme rather than inventing
    one.
    """
    a = max(0.0, float(aqi or 0))
    if not in_ncr:
        return {
            "stage": "n/a",
            "label": "No GRAP here",
            "detail": ("GRAP is a Delhi-NCR measure. This city has its own action plan; "
                       "the health advice below is from CPCB and applies anywhere."),
            "applies": False,
        }
    if a < 201:
        return dict(_NO_STAGE)
    for lo, hi, stage, label, detail in GRAP:
        if lo <= a <= hi:
            return {"stage": stage, "label": label, "detail": detail, "applies": True}
    return dict(_NO_STAGE)


def who_band(pm25: float) -> dict:
    """Where a concentration sits against WHO 2021 guideline and interim targets."""
    if pm25 is None:
        return {"band": "unknown", "multiple": None, "label": "no data"}
    v = float(pm25)
    if v <= 15:
        return {"band": "aqg", "multiple": round(v / 15, 2), "label": "at or below the WHO 24-hour guideline"}
    if v <= 37.5:
        return {"band": "it3", "multiple": round(v / 15, 1), "label": "between WHO interim targets 2 and 3"}
    if v <= 50:
        return {"band": "it2", "multiple": round(v / 15, 1), "label": "between interim targets 1 and 2"}
    if v <= 75:
        return {"band": "it1", "multiple": round(v / 15, 1), "label": "between interim target 1 and the guideline"}
    return {"band": "above_it1", "multiple": round(v / 15, 1), "label": "above WHO interim target 1"}
