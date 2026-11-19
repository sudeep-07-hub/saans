"""
Every physical constant used by the exposure and emissions model lives here,
with the source that justifies it.

Rule for this file: no number without a citation and a note on what kind of
number it is (measured / literature median / engineering estimate). If a value
is an estimate, `kind` says so and the UI surfaces it as editable.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class Factor:
    value: float
    unit: str
    source: str
    kind: str = "literature"  # literature | measured | estimate | standard

    def as_dict(self) -> dict[str, Any]:
        return asdict(self) | {"kind": self.kind}


# ---------------------------------------------------------------------------
# Health reference levels
# ---------------------------------------------------------------------------

# WHO 2021 global air quality guidelines, PM2.5.
# https://iris.who.int/bitstream/handle/10665/345329/9789240034228-eng.pdf
WHO_PM25_24H = Factor(15.0, "ug/m3", "WHO 2021 AQG, 24-hour PM2.5", "standard")
WHO_PM25_ANNUAL = Factor(5.0, "ug/m3", "WHO 2021 AQG, annual PM2.5", "standard")
WHO_PM25_IT1_24H = Factor(75.0, "ug/m3", "WHO 2021 interim target 1, 24-hour", "standard")
WHO_PM25_IT2_24H = Factor(50.0, "ug/m3", "WHO 2021 interim target 2, 24-hour", "standard")
WHO_PM25_IT3_24H = Factor(37.5, "ug/m3", "WHO 2021 interim target 3, 24-hour", "standard")

# Berkeley Earth (Muller & Muller): 1 cigarette/day ~= 22 ug/m3 PM2.5 for a day.
# It is a mortality-risk rule of thumb, not a toxicological equivalence.
CIGARETTE_PM25 = Factor(
    22.0, "ug/m3 per cigarette/day",
    "Berkeley Earth PM2.5-to-cigarette equivalence", "estimate"
)

# ---------------------------------------------------------------------------
# Inhalation rates, m3/hour, adult
# EPA Exposure Factors Handbook Ch.6: rest ~0.5 m3/h; light indoor activity
# ~1.2 m3/h (20 L/min); moderate 1.5-2.5 m3/h; active commuting higher.
# ---------------------------------------------------------------------------
IR = {
    "sleep": Factor(0.45, "m3/h", "EPA EFH Ch.6, rest", "literature"),
    "home": Factor(1.10, "m3/h", "EPA EFH Ch.6, light activity", "literature"),
    "work": Factor(1.10, "m3/h", "EPA EFH Ch.6, light activity", "literature"),
    "school": Factor(1.30, "m3/h", "EPA EFH Ch.6, child light activity", "literature"),
    "cook": Factor(1.70, "m3/h", "EPA EFH Ch.6, moderate activity", "literature"),
    "commute": Factor(1.80, "m3/h", "EPA EFH Ch.6, walking / transit", "literature"),
    "cycle": Factor(2.60, "m3/h", "EPA EFH Ch.6, vigorous activity", "literature"),
    "outdoor": Factor(1.80, "m3/h", "EPA EFH Ch.6, moderate activity", "literature"),
}

# ---------------------------------------------------------------------------
# Outdoor-to-indoor PM2.5 transfer
# Literature: infiltration factor 0.28 +/- 0.15 (48 Chinese homes, winter 0.34),
# 0.45 median for wildfire smoke, I/O 0.47-0.62 with windows closed,
# 0.76-0.92 with windows open (NCCEH review, 20 studies).
# ---------------------------------------------------------------------------
INFILTRATION = {
    "closed": Factor(0.42, "fraction", "NCCEH review; Chen et al. F_inf 0.28-0.45", "literature"),
    "mixed": Factor(0.60, "fraction", "NCCEH review, median I/O 0.62-0.76", "literature"),
    "open": Factor(0.85, "fraction", "NCCEH review, I/O with windows open 0.76-0.92", "literature"),
}

# Air changes per hour of the whole dwelling, when no cleaner is running.
# NBC 2016 / CSIR: bedrooms 2-4 ACH, living 3-6 ACH design; measured
# infiltration in Indian apartments is lower, ~1 ACH (Buildings & Cities 2022).
ACH = {
    "apartment": Factor(1.0, "1/h", "Buildings & Cities 2022 infiltration 1 ACH", "literature"),
    "independent": Factor(1.4, "1/h", "NBC 2016 bedrooms 2-4 ACH, leaky envelope", "estimate"),
    "single_room": Factor(1.8, "1/h", "single-room dwelling, high leakage", "estimate"),
}

# Measured kitchen PM2.5 attributable to the stove, 24-hour means.
# HAPIN pilot (Tamil Nadu): biomass median 134 ug/m3, LPG 27 ug/m3, ambient 23.
# Pune low-income homes: wood 249, LPG-only 141, all homes 167 (24h TWA).
# The Pune LPG figure includes heavy ambient infiltration in a polluted city,
# which the engine adds separately, so the stove-only terms here are lower and
# deliberately not inflated to match a total that double counts.
KITCHEN_PM25 = {
    "biomass": Factor(180.0, "ug/m3", "HAPIN 2020 (134) & Pune 2019 wood (249)", "measured"),
    "kerosene": Factor(120.0, "ug/m3", "Pune 2019, kerosene users 172 incl. ambient", "measured"),
    "lpg": Factor(40.0, "ug/m3", "HAPIN 2020 LPG kitchen 27 vs ambient 23", "measured"),
    "png": Factor(35.0, "ug/m3", "as LPG, slightly cleaner combustion", "estimate"),
    "electric": Factor(12.0, "ug/m3", "cooking aerosol and oil smoke only", "estimate"),
}

# Multiplier applied to kitchen concentration by exhaust arrangement.
EXHAUST_MODIFIER = {
    "chimney": Factor(0.45, "x", "chimney stoves ~60% lower PM2.5 (EST 2022)", "measured"),
    "fan": Factor(0.60, "x", "kitchen exhaust fan to outdoors", "estimate"),
    "none": Factor(1.00, "x", "no extraction", "standard"),
    "window": Factor(0.80, "x", "cooking with kitchen window wide open", "estimate"),
}

# Additional indoor PM2.5 sources, ug/m3 added to the room while in use.
INDOOR_SOURCE_PM25 = {
    "incense": Factor(45.0, "ug/m3", "incense associated with higher 24h PM2.5 (Pune 2018)", "measured"),
    "mosquito_coil": Factor(65.0, "ug/m3", "coil use GMR 1.5 for 24h PM2.5 (Pune 2018)", "measured"),
    "candle": Factor(12.0, "ug/m3", "paraffin candle particulate", "estimate"),
    "sweeping_dry": Factor(25.0, "ug/m3", "dry sweeping resuspension, short-lived", "estimate"),
    "firewood_heating": Factor(160.0, "ug/m3", "indoor wood/coal heating, high but episodic", "estimate"),
}

# ---------------------------------------------------------------------------
# Air cleaners. CADR in m3/h. Effectiveness is capped by field evidence:
# meta-analysis of 148 field studies: mean 49% +/- 20% PM2.5 reduction.
# ---------------------------------------------------------------------------
CLEANER_CADR = {
    "none": Factor(0.0, "m3/h", "no cleaner", "standard"),
    "box_fan": Factor(300.0, "m3/h", "20in box fan + MERV13 shroud, DIY build", "estimate"),
    "hepa_small": Factor(180.0, "m3/h", "entry HEPA, 20 m2 room", "estimate"),
    "hepa_medium": Factor(350.0, "m3/h", "mid HEPA, 30 m2 room", "estimate"),
}
CLEANER_CAP = Factor(0.78, "fraction", "field studies: 49% mean, up to 79% in-room", "measured")
CLEANER_ROOM_SHARE = {
    "box_fan": 0.55,     # living room / where people sit
    "hepa_small": 0.42,  # bedroom
    "hepa_medium": 0.55,
}

# ---------------------------------------------------------------------------
# Masks. Fitted filtration efficiency when actually worn.
# PLoS ONE 2024: cloth 47-55%, L1 52-60%, L3 60-77%, KN95/KF94 57-77%,
# N95 97-98% without formal fit testing.
# ---------------------------------------------------------------------------
MASK_FFE = {
    "n95": Factor(0.95, "fraction", "PLoS ONE 2024, N95 worn 97-98%", "measured"),
    "kn95": Factor(0.70, "fraction", "PLoS ONE 2024, KN95/KF94 57-77%", "measured"),
    "surgical": Factor(0.55, "fraction", "PLoS ONE 2024, level 1 52-60%", "measured"),
    "cloth": Factor(0.45, "fraction", "PLoS ONE 2024, 2-layer cotton 47-55%", "measured"),
    "none": Factor(0.0, "fraction", "no mask", "standard"),
}

# ---------------------------------------------------------------------------
# Commute microenvironments: PM2.5 inside the mode / ambient PM2.5.
# Delhi measurements: AC car 0.5x, metro 0.8x, bus 1.2x, open car 1.3x,
# 2-wheeler 1.3x, auto-rickshaw 1.5x (190 vs 130 ug/m3), walking 1.4x.
# ---------------------------------------------------------------------------
MODE_FACTOR = {
    "car_ac": Factor(0.50, "x", "Goel et al. 2015, AC car 50% below ambient", "measured"),
    "metro": Factor(0.80, "x", "Goel et al. 2015, metro carriage 20% below ambient", "measured"),
    "bus": Factor(1.20, "x", "Goel et al. 2015, bus 20% above ambient", "measured"),
    "car_open": Factor(1.30, "x", "Goel et al. 2015, open-window car", "measured"),
    "two_wheeler": Factor(1.30, "x", "Goel et al. 2015, motorised 2W", "measured"),
    "auto": Factor(1.50, "x", "Goel et al. 2015; Apte 2011, auto-rickshaw 1.5x", "measured"),
    "walk": Factor(1.40, "x", "Goel et al. 2015, walking 40% above ambient", "measured"),
    "cycle": Factor(1.40, "x", "as walking; higher dose from ventilation rate", "measured"),
    "wfh": Factor(0.42, "x", "stays home, indoor infiltration applies", "estimate"),
}

# ---------------------------------------------------------------------------
# Emissions factors for the "sustainable alternatives" side.
# ---------------------------------------------------------------------------
GRID_EF = Factor(0.71, "kg CO2e/kWh", "CEA CO2 Baseline Database v21.0, FY2024-25", "measured")

COMMUTE_CO2 = {  # kg CO2e per passenger-km
    "car_ac": Factor(0.15, "kg/pkm", "petrol car ~7 L/100km, 1.5 occupants", "estimate"),
    "car_open": Factor(0.15, "kg/pkm", "same vehicle, windows open", "estimate"),
    "two_wheeler": Factor(0.055, "kg/pkm", "100cc motorcycle, 45 km/L", "estimate"),
    "auto": Factor(0.090, "kg/pkm", "CNG auto-rickshaw", "estimate"),
    "bus": Factor(0.035, "kg/pkm", "city bus, average occupancy", "estimate"),
    "metro": Factor(0.020, "kg/pkm", "Delhi Metro, Indian grid", "estimate"),
    "walk": Factor(0.0, "kg/pkm", "zero tailpipe", "standard"),
    "cycle": Factor(0.0, "kg/pkm", "zero tailpipe", "standard"),
    "wfh": Factor(0.0, "kg/pkm", "no trip", "standard"),
}
COMMUTE_COST = {  # INR per km, out of pocket
    "car_ac": 8.75, "car_open": 8.75, "two_wheeler": 2.20, "auto": 15.0,
    "bus": 1.50, "metro": 2.20, "walk": 0.0, "cycle": 0.0, "wfh": 0.0,
}
COMMUTE_SPEED = {  # km/h, for converting trip minutes to km
    "car_ac": 18.0, "car_open": 18.0, "two_wheeler": 20.0, "auto": 16.0,
    "bus": 12.0, "metro": 25.0, "walk": 4.5, "cycle": 12.0, "wfh": 0.0,
}

# PM2.5 emission factor of traditional cookstoves, real-world field data.
# ACP 2017 (India, chulha): wood 10.5 g/kg, agri residue 11.1, dung 22.6.
# 2017 discussion-paper version reported 6.8 / 7.1 / 14.5 g/kg; we use the
# published final values and expose the choice.
COOK_PM25_EF = {
    "biomass": Factor(10.5, "g PM2.5/kg fuel", "ACP 2017 field EF, fuel wood", "measured"),
    "kerosene": Factor(0.35, "g PM2.5/kg fuel", "kerosene wick stove", "estimate"),
    "lpg": Factor(0.05, "g PM2.5/kg fuel", "gas combustion, near-zero particulate", "estimate"),
    "png": Factor(0.04, "g PM2.5/kg fuel", "piped gas", "estimate"),
    "electric": Factor(0.0, "g PM2.5/kg fuel", "no on-site combustion", "standard"),
}
COOK_CO2 = {  # kg CO2e per kg fuel
    "biomass": Factor(1.75, "kg CO2e/kg", "wood, non-renewable biomass fraction", "estimate"),
    "kerosene": Factor(2.50, "kg CO2e/kg", "kerosene combustion", "literature"),
    "lpg": Factor(2.98, "kg CO2e/kg", "LPG 63.1 g CO2/MJ x 47.3 MJ/kg", "literature"),
    "png": Factor(2.75, "kg CO2e/kg", "natural gas", "literature"),
    "electric": Factor(0.0, "kg CO2e/kg", "accounted via electricity", "standard"),
}
COOK_COST = {  # INR per kg fuel
    "biomass": 6.0, "kerosene": 75.0, "lpg": 63.4, "png": 52.0, "electric": 60.0,
}
DAILY_FUEL_KG = {
    "biomass": 3.2, "kerosene": 0.9, "lpg": 0.40, "png": 0.36, "electric": 0.0,
}

# Open burning of waste: ~10 g PM2.5 per kg of mixed yard/leaf waste.
BURN_PM25_EF = Factor(10.0, "g PM2.5/kg", "US EPA AP-42, yard waste open burning", "estimate")

# Food, kg CO2e per kg product (Poore & Nemecek 2018, via OWID).
FOOD_CO2 = {
    "beef": 60.0, "mutton": 24.0, "chicken": 6.0, "fish": 3.0,
    "cheese": 11.0, "milk": 3.2, "rice": 2.7, "legumes": 0.9,
    "vegetables": 0.4, "wheat": 1.4,
}

PETROL_PRICE = Factor(105.0, "INR/L", "Delhi retail, editable assumption", "estimate")
IDLE_L_PER_HOUR = Factor(0.6, "L/h", "idling a 1.5L petrol engine", "estimate")

# Coal / wood indoor heating is a carbon-monoxide hazard, not just a PM one.
# No numbers here on purpose: the app refuses to model it and tells you not to.
