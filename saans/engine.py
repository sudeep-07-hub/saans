"""
The exposure engine.

Design rules:

1. Every number that reaches the screen is traceable to a factor in
   constants.py, and every factor carries its source.
2. The model is a single-zone mass balance, not a black box. A user can read
   the formula, change one assumption, and watch the answer move.
3. Uncertainty is propagated by re-running the model at low and high settings
   of the assumptions that actually dominate the answer, and the range is
   shown next to the point estimate. A number without a band is a lie.
4. People have different days. A grandmother at home all day and a
   two-wheeler commuter must not receive the same dose, so the timeline is
   built per person and only the shared hours are shared.
5. Nothing here decides for the user. It computes the arithmetic of a choice;
   the choice, and the context only they know, stays theirs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Literal

from . import constants as C

Scenario = Literal["low", "mid", "high"]

# Multipliers for the uncertainty re-run. Chosen from the spread in the
# underlying literature, not invented: inhalation rates vary ~20%, fitted
# infiltration 0.28-0.45, measured kitchen PM2.5 spans a factor of 2-3.
UNCERTAINTY = {
    "low": {"ir": 0.85, "infil": 0.75, "kitchen": 0.65, "cleaner": 0.85, "mask": 0.85},
    "mid": {"ir": 1.00, "infil": 1.00, "kitchen": 1.00, "cleaner": 1.00, "mask": 1.00},
    "high": {"ir": 1.15, "infil": 1.25, "kitchen": 1.40, "cleaner": 1.15, "mask": 1.15},
}

# Office and classroom have no Delhi-specific microenvironment study behind
# them, so these are declared as engineering estimates rather than dressed up
# as measurements.
OFFICE_FACTOR = 0.40
SCHOOL_FACTOR = 0.55
SCHOOL_NOTE = "classroom with windows and no filtration"

# Share of a cooking plume that escapes the kitchen into the rest of the home.
# Estimate, not measurement: doors are usually open, kitchens are not sealed.
COOKING_SPILL = 0.35


@dataclass
class Ambient:
    pm25: float = 120.0
    pm10: float | None = None
    no2: float | None = None
    temp_c: float | None = None
    wind_kmh: float | None = None
    rh: float | None = None
    label: str = "modelled"
    source: str = "assumption"
    hourly: list = field(default_factory=list)  # [{hour, pm25}]

    def at_hour(self, hour: float) -> float:
        """Ambient PM2.5 at a given local hour, from the forecast if we have it."""
        h = int(hour) % 24
        if not self.hourly:
            # No forecast (offline or a test fixture): apply the winter diurnal
            # shape rather than holding the concentration flat. Without this the
            # app would claim that moving exercise to the afternoon changes
            # nothing, which is false in every real city.
            return max(1.0, self.pm25 * float(0.82 + 0.62 * _diurnal_shape(h)))
        for row in self.hourly:
            if int(row.get("hour") or 0) == h:
                return float(row.get("pm25") or self.pm25)
        return self.pm25


def _diurnal_shape(hour: int) -> float:
    morning = math.exp(-((hour - 7) ** 2) / 12.0)
    evening = math.exp(-((hour - 21) ** 2) / 18.0)
    midday = math.exp(-((hour - 14) ** 2) / 30.0)
    return 0.45 * morning + 0.55 * evening - 0.35 * midday


@dataclass
class Person:
    name: str = "You"
    age: int = 34
    pregnant: bool = False
    conditions: list[str] = field(default_factory=list)  # asthma, copd, heart, diabetes
    smoker: bool = False
    commutes: bool = True
    cooks: bool = False
    exercises: bool = True

    @property
    def ir_scale(self) -> float:
        """Body-size and developmental scaling of inhaled volume."""
        if self.age < 1:
            return 0.35
        if self.age < 5:
            return 0.55
        if self.age < 13:
            return 0.75
        if self.age >= 65:
            return 0.90
        return 1.0

    @property
    def sensitivity(self) -> float:
        """
        Relative sensitivity to a given inhaled dose, used only to flag who in
        the household is carrying the risk, never to produce a medical
        probability.
        """
        s = 1.0
        if self.age < 5:
            s = 1.6
        elif self.age >= 65:
            s = 1.4
        if "asthma" in self.conditions:
            s *= 1.5
        if "copd" in self.conditions:
            s *= 1.6
        if "heart" in self.conditions:
            s *= 1.4
        if self.pregnant:
            s *= 1.3
        return round(s, 2)


@dataclass
class Home:
    kind: str = "apartment"          # apartment | independent | single_room
    cooking_fuel: str = "lpg"        # biomass | kerosene | lpg | png | electric
    kitchen_exhaust: str = "none"    # chimney | fan | window | none
    cleaner: str = "none"            # none | box_fan | hepa_small | hepa_medium
    mixer: str = "none"              # secondary fuel used some days, or none
    windows_day: str = "mixed"       # closed | mixed | open
    windows_night: str = "closed"
    occupants: int = 4


@dataclass
class Habits:
    incense_per_day: int = 0
    mosquito_coil: bool = False
    dry_sweeping: bool = True
    waste_burning_kg_week: float = 0.0
    outdoor_exercise: bool = True
    exercise_hour: int = 7
    cook_hours: list[float] = field(default_factory=lambda: [8.0, 20.0])
    cook_minutes: int = 90


@dataclass
class Transport:
    mode: str = "two_wheeler"
    km_per_day: float = 18.0
    mask: str = "none"


@dataclass
class Block:
    """One stretch of one person's day, in one microenvironment."""
    label: str
    start: float
    hours: float
    place: str                 # home | kitchen | outdoor | vehicle | work | school
    intensity: str = "home"    # key into constants.IR
    mode: str | None = None
    mask: str = "none"
    cooking: bool = False
    conc: float | None = None


# ---------------------------------------------------------------------------
# Concentrations
# ---------------------------------------------------------------------------

def dwelling_volume(home: Home) -> float:
    return {"apartment": 185.0, "independent": 260.0, "single_room": 36.0}.get(home.kind, 185.0)


def _u(scenario: Scenario, key: str) -> float:
    return UNCERTAINTY[scenario][key]


def window_state(home: Home, hour: float) -> str:
    return home.windows_night if (hour < 6.5 or hour >= 22) else home.windows_day


def indoor_concentration(
    ambient_pm25: float,
    home: Home,
    habits: Habits,
    hour: float = 12.0,
    scenario: Scenario = "mid",
    windows: str | None = None,
    cleaner_override: str | None = None,
) -> float:
    """
    Single-zone steady state.

        C_in = F_inf * C_out  +  S
        C_in_clean = C_in * ACH / (ACH + CADR/V)

    F_inf already nets out penetration and deposition against the envelope.
    S is the summed 24-hour-mean contribution of indoor sources.
    """
    u = _u(scenario, "infil")
    win = windows or window_state(home, hour)
    finf = C.INFILTRATION.get(win, C.INFILTRATION["mixed"]).value * u
    ach = C.ACH.get(home.kind, C.ACH["apartment"]).value
    vol = dwelling_volume(home)

    # Indoor sources are expressed as a concentration while the source is
    # active, then time-weighted to a 24-hour mean. One sweep or one incense
    # stick is a short event; it should not dominate the daily average.
    sources = 0.0
    if habits.incense_per_day:
        sources += C.INDOOR_SOURCE_PM25["incense"].value * min(habits.incense_per_day, 8) * (45 / 1440)
    if habits.mosquito_coil:
        # coils burn 6-8 h overnight, mostly one room
        sources += C.INDOOR_SOURCE_PM25["mosquito_coil"].value * (7 / 24) * 0.45
    if habits.dry_sweeping:
        # three sweeps a day at 10 minutes each, in part of the house
        sources += C.INDOOR_SOURCE_PM25["sweeping_dry"].value * (30 / 1440) * 0.30

    base = finf * ambient_pm25 + sources

    # Cooking plume migrates out of the kitchen. Modelling the kitchen as an
    # isolated box would make a wood stove look harmless to everyone except the
    # cook, which is not how a two-room flat behaves. The spill fraction is an
    # engineering estimate, declared as one.
    if habits and habits.cook_minutes:
        k = kitchen_concentration(ambient_pm25, home, habits, scenario)
        cook_hours = habits.cook_minutes * len(habits.cook_hours or [1]) / 60.0
        base += max(0.0, k - base) * min(cook_hours / 24.0, 1.0) * COOKING_SPILL

    cleaner = cleaner_override if cleaner_override is not None else home.cleaner
    cadr = C.CLEANER_CADR.get(cleaner, C.CLEANER_CADR["none"]).value
    if cadr > 0:
        # A single unit does not treat every cubic metre equally. Coverage is the
        # share of the dwelling it effectively serves, so the whole-home average
        # lands where the field trials land (~49%) instead of at an idealised
        # well-mixed number that no household achieves.
        cadr_eff = cadr * C.CLEANER_ROOM_SHARE.get(cleaner, 0.5)
        kf = cadr_eff / vol
        reduction = 1.0 - ach / (ach + kf * _u(scenario, "cleaner"))
        reduction = min(reduction, C.CLEANER_CAP.value)
        base = base * (1.0 - reduction)

    return max(0.0, round(base, 1))


def kitchen_concentration(
    ambient_pm25: float,
    home: Home,
    habits: Habits | None = None,
    scenario: Scenario = "mid",
    cooking: bool = True,
) -> float:
    """
    Kitchen during cooking. The dominant term is the stove, not the ambient
    air: measured 24-hour kitchen means are 134 ug/m3 on biomass against
    27 ug/m3 on LPG in the same villages. Ambient leaks in at a reduced
    fraction because kitchens are the best-vented room in the house.
    """
    u = _u(scenario, "kitchen")
    fuel = home.cooking_fuel
    exhaust = C.EXHAUST_MODIFIER.get(home.kitchen_exhaust, C.EXHAUST_MODIFIER["none"]).value
    base = C.KITCHEN_PM25.get(fuel, C.KITCHEN_PM25["lpg"]).value * u * exhaust
    if cooking and home.mixer and home.mixer not in ("none", fuel):
        # secondary fuel used on some days: weight it in at 40%
        base += 0.4 * C.KITCHEN_PM25.get(home.mixer, C.KITCHEN_PM25["lpg"]).value * u * exhaust
    leak = 0.25 * ambient_pm25 * _u(scenario, "infil")
    return max(0.0, round(base + leak, 1))


def vehicle_concentration(ambient_pm25: float, mode: str) -> float:
    f = C.MODE_FACTOR.get(mode, C.MODE_FACTOR["bus"]).value
    return max(0.0, round(ambient_pm25 * f, 1))


def workplace_concentration(ambient_pm25: float, kind: str = "office") -> float:
    f = OFFICE_FACTOR if kind == "office" else SCHOOL_FACTOR
    return max(0.0, round(ambient_pm25 * f, 1))


def mask_penetration(mask: str, scenario: Scenario = "mid") -> float:
    """Fraction of particles that get past the mask. Never zero, never 1."""
    ffe = C.MASK_FFE.get(mask, C.MASK_FFE["none"]).value
    if ffe <= 0:
        return 1.0
    ffe = min(0.985, ffe / _u(scenario, "mask"))
    return 1.0 - ffe


# ---------------------------------------------------------------------------
# Per-person timelines
# ---------------------------------------------------------------------------

def _with_roles(people: list[Person]) -> list[Person]:
    """
    Resolve the cooking role.

    If nobody in the household is marked as cooking, the kitchen would become
    invisible to the model and a wood stove would look harmless. Somebody does
    cook in a house where a stove exists, so the role defaults to the first
    adult who does not commute — usually the person with the highest exposure
    in the whole household, which is exactly the pattern the literature
    reports. The user can override it.
    """
    if not people:
        return [Person()]
    if any(p.cooks for p in people):
        return people
    out = [replace(p) for p in people]
    adults = [p for p in out if p.age >= 18]
    non_commuters = [p for p in adults if not p.commutes]
    target = (non_commuters or adults or out)[0]
    target.cooks = True
    return out


def day_for(person: Person, home: Home, habits: Habits, transport: Transport,
            office: bool = True) -> list[Block]:
    """
    Build one person's day, exactly 24 hours, no gaps and no overlaps.

    Roles decide the day: a commuter travels and works, a child goes to school,
    someone at home stays in it, and whoever cooks takes the kitchen plume on
    behalf of everyone. Everything is editable in the UI; this is the default.

    The schedule is anchored on real events (meals, the commute, school) and any
    leftover hour is filled at home rather than dropped, because a day that
    silently loses two hours would understate the dose.
    """
    raw: list[Block] = []

    def add(label, start, hours, place, intensity=None, **kw):
        if hours <= 0.02:
            return
        raw.append(Block(label, float(start), float(hours), place,
                         intensity or ("home" if place == "home" else place), **kw))

    cook_am = habits.cook_hours[0] if habits.cook_hours else 8.0
    cook_pm = habits.cook_hours[1] if len(habits.cook_hours) > 1 else 20.0
    cook_h = max(0.25, habits.cook_minutes / 60.0)

    add("Asleep", 0.0, 6.5, "home", "sleep")
    wake = 6.5
    add("Morning at home", wake, 1.0, "home", "home")

    cursor = wake + 1.0
    if person.exercises and habits.outdoor_exercise:
        add("Walk or exercise outside", habits.exercise_hour, 0.7, "outdoor", "outdoor")

    meal_am_end = cook_am + cook_h
    if person.cooks:
        add("Cooking (breakfast)", cook_am, cook_h, "kitchen", "cook", cooking=True)
    else:
        add("Breakfast at home", cook_am, cook_h, "home", "home")

    # The middle of the day
    mid_start = max(meal_am_end, 9.0)
    if person.commutes:
        speed = max(C.COMMUTE_SPEED.get(transport.mode, 15.0), 1.0)
        one_way = (transport.km_per_day / 2) / speed
        add(f"Commute out ({prettify_mode(transport.mode)})", mid_start, one_way, "vehicle",
            "commute", mode=transport.mode, mask=transport.mask)
        away = 8.0 if office else 0.0
        add("At work", mid_start + one_way, away, "work", "work")
        back = mid_start + one_way + away
        add(f"Commute home ({prettify_mode(transport.mode)})", back, one_way, "vehicle",
            "commute", mode=transport.mode, mask=transport.mask)
    elif 5 <= person.age < 18:
        add("At school", 8.0, 7.0, "school", "school")
    # else: at home, which the gap fill below covers

    if person.cooks:
        add("Cooking (dinner)", cook_pm, cook_h, "kitchen", "cook", cooking=True)

    return _fill_day(raw)


def _fill_day(raw: list[Block]) -> list[Block]:
    """Trim overlaps, fill gaps with home blocks, and end at 24.0 exactly."""
    raw = sorted((b for b in raw if b.hours > 0.02), key=lambda b: b.start)
    out: list[Block] = []

    # clear frozen intervals of conflicts by keeping the earlier-starting block
    for b in raw:
        if out and b.start < out[-1].start + out[-1].hours:
            overlap = out[-1].start + out[-1].hours - b.start
            remaining = b.hours - overlap
            if remaining <= 0.02:
                continue
            b.start = out[-1].start + out[-1].hours
            b.hours = remaining
        out.append(b)

    if not out:
        return [Block("Day at home", 0.0, 24.0, "home", "home")]

    # everything before the first anchored block is home
    if out[0].start > 0.02:
        out.insert(0, Block("At home", 0.0, out[0].start, "home", "home"))

    # gap fill between anchors, split between the two neighbours' context
    filled: list[Block] = []
    for i, b in enumerate(out):
        filled.append(b)
        nxt = out[i + 1] if i + 1 < len(out) else None
        end = b.start + b.hours
        if nxt is not None and nxt.start - end > 0.02:
            filled.append(Block("At home", end, nxt.start - end, "home", "home"))
        elif nxt is None and 24.0 - end > 0.02:
            filled.append(Block("Evening at home", end, 24.0 - end, "home", "home"))

    # if the day overran 24h, shorten the final block rather than the anchors
    total = sum(b.hours for b in filled)
    if total > 24.0:
        over = total - 24.0
        for b in reversed(filled):
            cut = min(over, b.hours - 0.05)
            if cut > 0:
                b.hours -= cut
                over -= cut
            if over <= 0.001:
                break
        filled = [b for b in filled if b.hours > 0.02]
    return filled


def prettify_mode(mode: str) -> str:
    return {
        "car_ac": "AC car", "car_open": "car, windows open", "two_wheeler": "two-wheeler",
        "auto": "auto-rickshaw", "bus": "bus", "metro": "metro", "walk": "walking",
        "cycle": "cycling", "wfh": "working from home",
    }.get(mode, mode)


def _resolve(block: Block, ambient: Ambient, home: Home, habits: Habits,
             scenario: Scenario) -> float:
    """Concentration this person met during this block, before any mask."""
    hour = block.start + block.hours / 2
    amb = ambient.at_hour(hour)
    if block.place == "outdoor":
        return round(amb, 1)
    if block.place == "kitchen":
        return kitchen_concentration(amb, home, habits, scenario, cooking=block.cooking)
    if block.place == "vehicle":
        mode = block.mode or "bus"
        if mode == "wfh":
            return indoor_concentration(amb, home, habits, hour, scenario)
        return vehicle_concentration(amb, mode)
    if block.place == "work":
        if home.cleaner != "none":
            return round(workplace_concentration(amb, "office") * 0.9, 1)
        return workplace_concentration(amb, "office")
    if block.place == "school":
        return workplace_concentration(amb, "school")
    return indoor_concentration(amb, home, habits, hour, scenario)


def evaluate(
    people: list[Person],
    ambient: Ambient,
    home: Home,
    habits: Habits,
    transport: Transport,
    scenario: Scenario = "mid",
    office: bool = True,
) -> dict:
    """Run every person's day and return dose, exposure and where it came from."""
    people = _with_roles(people)
    rows = []
    for p in people:
        blocks = day_for(p, home, habits, transport, office=office)
        dose = 0.0
        volume = 0.0
        by_place: dict[str, float] = {}
        total_h = 0.0
        for b in blocks:
            b.conc = _resolve(b, ambient, home, habits, scenario)
            ir = C.IR.get(b.intensity, C.IR["home"]).value * _u(scenario, "ir") * p.ir_scale
            conc = b.conc * mask_penetration(b.mask, scenario)
            hours = b.hours
            d = conc * ir * hours
            dose += d
            volume += ir * hours
            total_h += hours
            by_place[b.place] = by_place.get(b.place, 0.0) + d
        mean_exposure = dose / volume if volume else 0.0
        rows.append({
            "name": p.name,
            "age": p.age,
            "blocks": [
                {"label": b.label, "start": b.start, "hours": b.hours, "place": b.place,
                 "pm25": b.conc, "mask": b.mask, "mode": b.mode, "cooking": b.cooking}
                for b in blocks
            ],
            "dose_ug": round(dose),
            "inhaled_m3": round(volume, 1),
            "mean_exposure": round(mean_exposure, 1),
            "cigarettes": round(mean_exposure / C.CIGARETTE_PM25.value, 2),
            "who_multiple": round(mean_exposure / C.WHO_PM25_24H.value, 1),
            "sensitivity": p.sensitivity,
            "hours_accounted": round(total_h, 1),
            "attributed_risk_share": 0.0,
            "by_place": {k: round(v) for k, v in sorted(by_place.items(), key=lambda kv: -kv[1])},
        })

    weighted = [(r["dose_ug"] * r["sensitivity"], r) for r in rows]
    tw = sum(w for w, _ in weighted) or 1.0
    for w, row in weighted:
        row["attributed_risk_share"] = round(w / tw, 3)

    household_dose = sum(r["dose_ug"] for r in rows)
    return {
        "people": rows,
        "household_dose_ug": round(household_dose),
        "household_cigarettes": round(sum(r["cigarettes"] for r in rows) / max(len(rows), 1), 2),
        "scenario": scenario,
        "hourly": hourly_profile(people, ambient, home, habits, transport, scenario, office),
    }


def hourly_profile(people, ambient, home, habits, transport, scenario, office) -> list[dict]:
    """
    24 points, the mean concentration the household is actually breathing at
    each hour, weighted by how many people are in each microenvironment then.
    This is the curve the UI draws.
    """
    days = {p.name: day_for(p, home, habits, transport, office=office) for p in people}
    resolved: dict[str, list[tuple[float, float, float]]] = {}
    for name, blocks in days.items():
        spans = []
        for b in blocks:
            conc = _resolve(b, ambient, home, habits, scenario)
            spans.append((b.start, b.start + b.hours, conc * mask_penetration(b.mask, scenario)))
        resolved[name] = spans

    out = []
    for h in range(24):
        vals = []
        for name, spans in resolved.items():
            for a, b, c in spans:
                if a <= h < b or (a <= h + 0.5 < b):
                    vals.append(c)
                    break
        out.append({"hour": h, "pm25": round(sum(vals) / len(vals), 1) if vals else round(ambient.at_hour(h), 1)})
    return out


def compare(base: dict, alt: dict) -> dict:
    """The delta a choice actually produces."""
    d_dose = base["household_dose_ug"] - alt["household_dose_ug"]
    pct = (d_dose / base["household_dose_ug"] * 100) if base["household_dose_ug"] else 0.0
    return {
        "dose_before": base["household_dose_ug"],
        "dose_after": alt["household_dose_ug"],
        "dose_saved_ug": round(d_dose),
        "pct": round(pct, 1),
        "cig_before": base["household_cigarettes"],
        "cig_after": alt["household_cigarettes"],
        "cig_saved": round(base["household_cigarettes"] - alt["household_cigarettes"], 2),
    }


# ---------------------------------------------------------------------------
# Emissions: what the household puts into the air, and what it costs.
# ---------------------------------------------------------------------------

def household_emissions(home: Home, habits: Habits, transport: Transport, people: int) -> dict:
    fuel = home.cooking_fuel
    kg_day = C.DAILY_FUEL_KG.get(fuel, 0.4) * max(home.occupants, 1) / 4.0
    ef = C.COOK_PM25_EF.get(fuel, C.COOK_PM25_EF["lpg"]).value
    kitchen_pm = kg_day * ef              # grams of PM2.5 per day

    cook_co2 = kg_day * C.COOK_CO2.get(fuel, C.COOK_CO2["lpg"]).value
    cook_cost = kg_day * C.COOK_COST.get(fuel, C.COOK_COST["lpg"])

    km = transport.km_per_day
    travel_co2 = km * C.COMMUTE_CO2.get(transport.mode, C.COMMUTE_CO2["bus"]).value
    travel_cost = km * C.COMMUTE_COST.get(transport.mode, C.COMMUTE_COST["bus"])

    burn_pm = habits.waste_burning_kg_week * C.BURN_PM25_EF.value / 7.0   # grams/day
    burn_co2 = habits.waste_burning_kg_week * 1.9 / 7.0                   # kg CO2e/day

    return {
        "cook_pm25_g_day": round(kitchen_pm, 1),
        "cook_pm25_kg_year": round(kitchen_pm * 365 / 1000, 1),
        "cook_co2_kg_day": round(cook_co2, 2),
        "cook_cost_inr_day": round(cook_cost, 1),
        "travel_co2_kg_day": round(travel_co2, 2),
        "travel_cost_inr_day": round(travel_cost, 1),
        "burn_pm25_g_day": round(burn_pm, 1),
        "burn_co2_kg_day": round(burn_co2, 2),
        "pm25_g_day": round(kitchen_pm + burn_pm, 1),
        "co2_kg_day": round(cook_co2 + travel_co2 + burn_co2, 2),
        "cost_inr_day": round(cook_cost + travel_cost, 1),
        "people": people,
    }


def local_burn_increment(kg_week: float) -> float:
    """
    How much a household's own open burning raises the air it breathes.

    Engineering estimate, declared as one: 10 g PM2.5 per kg, dispersed into
    roughly the volume of a residential block's airshed (~150 m x 150 m x 40 m
    of mixing depth, refreshed about once an hour). It is not a measurement,
    and the UI labels it as an estimate, but the point it makes is real: the
    plume you light yourself lands on you first.
    """
    if kg_week <= 0:
        return 0.0
    grams_day = kg_week * C.BURN_PM25_EF.value / 7.0
    volume_m3 = 150 * 150 * 40
    air_changes_per_day = 24
    return round(grams_day * 1e6 / (volume_m3 * air_changes_per_day), 1)


def fuel_switch_saving(home: Home) -> dict:
    em = household_emissions(home, Habits(), Transport(), home.occupants)
    alt = household_emissions(
        Home(kind=home.kind, cooking_fuel="lpg", occupants=home.occupants),
        Habits(), Transport(), home.occupants,
    )
    return {
        "current_pm25_kg_year": em["cook_pm25_kg_year"],
        "lpg_pm25_kg_year": alt["cook_pm25_kg_year"],
        "saved_pm25_kg_year": round(em["cook_pm25_kg_year"] - alt["cook_pm25_kg_year"], 1),
        "current_co2_kg_day": em["cook_co2_kg_day"],
        "lpg_co2_kg_day": alt["cook_co2_kg_day"],
    }


def pm25_to_cigarettes(pm25: float) -> float:
    return round(float(pm25) / C.CIGARETTE_PM25.value, 2)


def worst_hour(ambient: Ambient) -> dict:
    """The hour of the day the outdoor air is worst, from the forecast."""
    hours = _hour_series(ambient)
    best = max(hours, key=lambda r: r["pm25"])
    return {"hour": best["hour"], "pm25": round(best["pm25"], 1)}


def _local_hour(ambient: Ambient) -> int | None:
    """The local hour at the location, when the upstream model tells us the time."""
    for row in ambient.hourly:
        t = row.get("time")
        if isinstance(t, str) and "T" in t and len(t) >= 13:
            try:
                return int(t[11:13])
            except ValueError:
                return None
    return None


def next_hours(ambient: Ambient, count: int = 6) -> list[dict]:
    """
    The next few hours, starting now.

    This exists because `worst_hour` is a maximum over the whole 0-23 series,
    which at 21:00 returns 21:00 even though the actual peak was 07:00 and the
    advice built on it ("keep windows shut until the lull") is then about the
    past. A daily-use screen has to answer *what happens next*, so it needs the
    forward window, not the daily extremum.
    """
    hours = _hour_series(ambient)
    if not hours:
        return []
    now = _local_hour(ambient)
    if now is None:
        # No clock from upstream: fall back to the system clock. Wrong by a few
        # hours at most, and the caller labels this as modelled rather than live.
        from datetime import datetime
        now = datetime.now().hour
    forward = [h for h in hours if h["hour"] >= now][:count]
    if len(forward) < count:                      # wrap past midnight
        forward += [h for h in hours if h["hour"] < now][: count - len(forward)]
    return forward


def next_trough(ambient: Ambient, within: int = 12) -> dict | None:
    """
    The next genuinely clean window, which is what a ventilation decision needs.

    Returns the lowest point in the forward window, so a user at 23:00 is told
    about tomorrow afternoon rather than about a trough that passed eight hours
    ago.
    """
    fwd = next_hours(ambient, within)
    if not fwd:
        return None
    low = min(fwd, key=lambda r: r["pm25"])
    return {"hour": low["hour"], "pm25": round(low["pm25"], 1)}


def next_peak(ambient: Ambient, within: int = 12) -> dict | None:
    """The next rise worth bracing for, in the forward window."""
    fwd = next_hours(ambient, within)
    if not fwd:
        return None
    high = max(fwd, key=lambda r: r["pm25"])
    return {"hour": high["hour"], "pm25": round(high["pm25"], 1)}


def is_elevated_now(ambient: Ambient, share: float = 0.85) -> bool:
    """
    Is the air right now near the day's own worst, rather than in a lull?

    Relative, not absolute: 60 ug/m3 is a lull in Delhi in November and an
    emergency in London in July. The question the UI asks is "should I keep the
    windows shut", and the honest answer depends on whether we are near this
    day's peak.
    """
    hours = _hour_series(ambient)
    if not hours:
        return False
    current = ambient.pm25
    peak = max(r["pm25"] for r in hours) or current
    return current >= peak * share


def cleanest_hour(ambient: Ambient, morning_only: bool = False) -> dict:
    """
    The cleanest hour of the whole day.

    Defaults to the whole day rather than the morning, because in a winter
    inversion the morning is usually the worst part of it: the cleanest window
    is typically mid-afternoon, and recommending the morning would be exactly
    backwards. For "what should I do next", use `next_trough` instead.
    """
    hours = _hour_series(ambient)
    if morning_only:
        subset = [r for r in hours if 5 <= r["hour"] <= 11]
        hours = subset or hours
    best = min(hours, key=lambda r: r["pm25"])
    return {"hour": best["hour"], "pm25": round(best["pm25"], 1)}


def _hour_series(ambient: Ambient) -> list[dict]:
    if ambient.hourly:
        by_hour: dict[int, list[float]] = {}
        for r in ambient.hourly:
            by_hour.setdefault(int(r.get("hour") or 0), []).append(float(r.get("pm25") or 0))
        return [{"hour": h, "pm25": sum(v) / len(v)} for h, v in sorted(by_hour.items())]
    return [{"hour": h, "pm25": ambient.at_hour(h)} for h in range(24)]
