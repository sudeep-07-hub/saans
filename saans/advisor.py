"""
The recommendation engine: a catalogue of interventions, each with its own
arithmetic, its cost, and its honest caveat.

Every intervention is a patch plus an explanation. A patch changes one thing
about the household — the fuel, the exhaust, the commute, the mask — and the
engine re-runs the whole day against it. Nothing here hard-codes a percentage
saving; the saving falls out of the model, which is why the same suggestion can
be worth 40% for a two-wheeler commuter and 4% for someone who already works
from home.

Ordering is by measured benefit per rupee, not by how good it sounds.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, Callable

from . import constants as C
from . import engine as E
from .aqi import compute as aqi_compute, grap_stage, who_band


def _patch(home=None, habits=None, transport=None) -> dict:
    return {"home": home or {}, "habits": habits or {}, "transport": transport or {}}


# ---------------------------------------------------------------------------
# Interventions: (patch, copy)
# ---------------------------------------------------------------------------

# Rank of each option along its own dimension, used so an intervention can only
# ever move a household forward. Recommending a box-fan filter to a house that
# already runs a HEPA would produce a negative "saving", which is nonsense.
FUEL_RANK = {"biomass": 0, "kerosene": 1, "lpg": 2, "png": 3, "electric": 4}
EXHAUST_RANK = {"none": 0, "window": 1, "fan": 2, "chimney": 3}
CLEANER_RANK = {"none": 0, "box_fan": 1, "hepa_small": 2, "hepa_medium": 3}


def _up(current: str, rank: dict, steps: int = 1) -> str:
    """The next rung up the ladder, never a rung down."""
    order = sorted(rank, key=rank.get)
    i = order.index(current) if current in rank else 0
    return order[min(i + steps, len(order) - 1)]


def i_cleaner(home: E.Home, habits: E.Habits, tr: E.Transport, people, ambient):
    """A cleaner in the room people sleep in is the strongest move at home."""
    target = home.cleaner if CLEANER_RANK.get(home.cleaner, 0) >= 3 else "hepa_medium"
    return _patch(home={"cleaner": target}), {
        "title": "Run a HEPA filter in the room you sleep in",
        "why": ("Field trials cut bedroom PM2.5 by 42-60%, and 71% in a well-sealed room. "
                "Sleep is 7-8 hours of your daily dose, all of it in one room, which is why "
                "filtering only that room beats filtering the whole house."),
        "source": "Riederer 2021, Indoor Air (60% bedroom); NCCEH review 2022 (71% sealed room)",
        "cost_inr": 5500,
        "runtime_inr_yr": 2400,
        "effort": "Buy once, run it at night",
        "tags": ["indoor", "health", "cost"],
    }


def i_diy_filter(home, habits, tr, people, ambient):
    # A box fan is only ever offered as an upgrade from nothing. Offering it to
    # a household that already owns a HEPA would be a downgrade dressed up as a
    # saving, and the model would show a negative benefit.
    target = "box_fan" if CLEANER_RANK.get(home.cleaner, 0) < 1 else home.cleaner
    return _patch(home={"cleaner": target}), {
        "title": "Box-fan filter: a MERV13 furnace filter taped to a 20-inch fan",
        "why": ("Blocks the same particles for roughly Rs 800 and 200 W. When a commercial HEPA "
                "is out of reach, this still buys most of the bedroom benefit, and the EPA's own "
                "testing covers the build."),
        "source": "US EPA, Residential Air Cleaners: A Technical Summary, 3rd ed. (2018)",
        "cost_inr": 800,
        "runtime_inr_yr": 1800,
        "effort": "One afternoon to build",
        "tags": ["indoor", "health", "cheap"],
    }


def i_kitchen_exhaust(home, habits, tr, people, ambient):
    target = _up(home.kitchen_exhaust, EXHAUST_RANK)
    return _patch(home={"kitchen_exhaust": target}), {
        "title": "Put a chimney or exhaust fan over the stove, venting outdoors",
        "why": ("A chimney over a solid-fuel stove cut kitchen PM2.5 by about 60% in field "
                "trials in India; a built-in chimney on a traditional stove cut it by 60% "
                "against none. This is the intervention that protects whoever cooks, who "
                "usually carries the highest exposure in the house."),
        "source": "EST 2022, Environ. Sci. Technol. (cookstove RCT, 1205 kitchen-days, India)",
        "cost_inr": 3500,
        "runtime_inr_yr": 300,
        "effort": "Half a day of fitting",
        "tags": ["kitchen", "health"],
    }


def i_clean_fuel(home, habits, tr, people, ambient):
    """
    Move up the fuel ladder, and name the change accurately.

    A household already on LPG is not being asked to "stop burning wood" — it
    is being offered the last rung, electricity, which is a different claim
    with different economics. Saying it honestly matters more than reusing one
    tidy sentence.
    """
    current = FUEL_RANK.get(home.cooking_fuel, 0)
    if current >= 4:
        return _patch(), {
            "title": "You already cook on electricity",
            "why": "There is no cleaner fuel to move to. Your remaining sources are the commute, "
                   "anything burned outdoors, and what drifts in from the street.",
            "source": "CEA grid factor; WHO household air pollution",
            "cost_inr": 0, "runtime_inr_yr": 0, "effort": "Nothing to do",
            "tags": ["kitchen"],
        }
    if current >= 2:      # lpg or png
        return _patch(home={"cooking_fuel": "electric", "mixer": "none"}), {
            "title": "Move the last cooking off gas, onto electricity",
            "why": ("Gas already removed almost all the particulate from your kitchen, so this is "
                    "a smaller step than it sounds: what it removes is the nitrogen dioxide and the "
                    "residual plume, and on the Indian grid it also emits less CO2 per meal."),
            "source": "CEA CO2 Baseline Database v21.0; LPG 2.98 kg CO2e/kg",
            "cost_inr": 4000, "runtime_inr_yr": -1200,
            "effort": "One appliance, a dedicated circuit",
            "tags": ["kitchen", "climate", "cost"],
        }
    return _patch(home={"cooking_fuel": "lpg", "mixer": "none"}), {
        "title": "Move cooking off wood, dung or kerosene onto LPG",
        "why": ("Switching from biomass to LPG dropped median kitchen PM2.5 from 134 to "
                "27 ug/m3 in an Indian field trial and cut women's personal exposure by 78%. "
                "No filter competes with removing the source, and it removes tonnes of PM2.5 "
                "from the neighbourhood, not just your kitchen."),
        "source": "HAPIN pilot, Tamil Nadu (2020); WHO household air pollution (2021)",
        "cost_inr": 12000, "runtime_inr_yr": 6500,
        "effort": "Connection, cylinder and a new stove",
        "tags": ["kitchen", "health", "climate"],
    }


def i_no_burn(home, habits, tr, people, ambient):
    return _patch(habits={"waste_burning_kg_week": 0.0}), {
        "title": "Stop burning leaves, waste and wood outdoors",
        "why": ("Open burning of yard waste releases about 10 g of PM2.5 per kg. Two bags a "
                "week makes the household a real emitter and the plume lands on your own "
                "street first. It is also banned outright under GRAP I, so a complaint "
                "actually gets acted on."),
        "source": "US EPA AP-42 (open burning of yard waste); CAQM GRAP Stage I",
        "cost_inr": 0,
        "runtime_inr_yr": 0,
        "effort": "Compost pit, or use municipal pickup",
        "tags": ["community", "climate", "free"],
    }


def i_mask_commute(home, habits, tr, people, ambient):
    return _patch(transport={"mask": "n95"}), {
        "title": "Wear a fitted N95 on the commute",
        "why": ("A fitted N95 filters 97-98% of fine particles when actually worn, against "
                "about 50% for cloth and 38-60% for a loose surgical mask. On a road at 1.3-1.5x "
                "the ambient level this is the cheapest large cut to a commuter's daily dose."),
        "source": "PLoS ONE 2024 (fitted filtration efficiency); Clapp 2021, JAMA Intern. Med.",
        "cost_inr": 400,
        "runtime_inr_yr": 3600,
        "effort": "Buy a box, learn the nose-clip fit",
        "tags": ["outdoor", "commute", "cheap", "health"],
    }


def i_shift_commute(home, habits, tr, people, ambient):
    best = "metro" if tr.mode in ("car_ac", "car_open", "two_wheeler", "auto") else "bus"
    return _patch(transport={"mode": best}), {
        "title": f"Move the commute to {E.prettify_mode(best)} where the route exists",
        "why": ("In Delhi measurements a metro carriage sat at 0.8x ambient PM2.5 and an "
                "AC car at 0.5x, while an auto-rickshaw or an open-window car ran 1.3-1.5x. "
                "Same city, roughly half the dose, and a fraction of the CO2 and the money."),
        "source": "Goel et al. 2015, Atmos. Environ. (11 Delhi transport microenvironments)",
        "cost_inr": 0,
        "runtime_inr_yr": -9000,   # a saving, not a cost
        "effort": "Route planning",
        "tags": ["commute", "climate", "cost"],
    }


def i_window_timing(home, habits, tr, people, ambient):
    return _patch(home={"windows_day": "mixed", "windows_night": "closed"}), {
        "title": "Ventilate in the cleanest hour, seal through the peaks",
        "why": ("Winter PM2.5 in the Indo-Gangetic plain peaks 05:00-09:00 and again after "
                "20:00, when the night's emissions are trapped under an inversion. Ten minutes "
                "with windows open on opposite walls at the daily low clears CO2 and cooking "
                "moisture without importing the peak."),
        "source": "CPCB hourly station records; boundary-layer cycle",
        "cost_inr": 0,
        "runtime_inr_yr": 0,
        "effort": "A habit and a phone reminder",
        "tags": ["indoor", "free"],
    }


def i_cook_time(home, habits, tr, people, ambient):
    if home.kitchen_exhaust != "none":
        return _patch(), {
            "title": "Cook with the exhaust on and the kitchen door closed",
            "why": ("Your kitchen already has extraction. The remaining gain is in using it "
                    "every time and keeping the plume from moving into the bedrooms."),
            "source": "HAPIN 2020; Pune 2019 indoor measurements",
            "cost_inr": 0,
            "runtime_inr_yr": 0,
            "effort": "Free",
            "tags": ["kitchen", "free"],
        }
    return _patch(home={"kitchen_exhaust": "window"}), {
        "title": "Cook with the kitchen window wide open and the door shut",
        "why": ("Cooking adds 40-70 ug/m3 indoors even on gas, and far more on solid fuel. "
                "An open window is not as good as an exhaust hood, but it is free, it works "
                "today, and keeping the door shut stops the plume reaching the beds."),
        "source": "Pune 2019, low-income urban homes (n=166); HAPIN 2020",
        "cost_inr": 0,
        "runtime_inr_yr": 0,
        "effort": "Free",
        "tags": ["kitchen", "free"],
    }


def i_stop_incense(home, habits, tr, people, ambient):
    return _patch(habits={"incense_per_day": 0, "mosquito_coil": False}), {
        "title": "Move incense and mosquito coils outdoors, or drop them",
        "why": ("Incense and coils are small fires inside the room. Coil use was associated "
                "with 1.5x higher 24-hour PM2.5 in Pune homes, as strongly as wood cooking. "
                "If it is mosquitoes, a net or a fan is the air-quality answer."),
        "source": "Pune 2018, Sources of household air pollution in low-income homes (n=166)",
        "cost_inr": 500,
        "runtime_inr_yr": 0,
        "effort": "Swap the habit",
        "tags": ["indoor", "free", "health"],
    }


def i_exercise_time(home, habits, tr, people, ambient):
    return _patch(habits={"exercise_hour": 15}), {
        "title": "Move the walk or run to the early afternoon",
        "why": ("You inhale 1.6-2.5 m3/h when exercising, roughly double your resting rate, so "
                "the same 30 minutes outdoors costs about twice the dose. The afternoon "
                "boundary layer is deeper and the road is quieter."),
        "source": "US EPA Exposure Factors Handbook Ch.6 (inhalation rates); diurnal cycle",
        "cost_inr": 0,
        "runtime_inr_yr": 0,
        "effort": "Reschedule",
        "tags": ["outdoor", "free", "health"],
    }


def i_induction(home, habits, tr, people, ambient):
    target = "electric" if FUEL_RANK.get(home.cooking_fuel, 0) < 4 else home.cooking_fuel
    return _patch(home={"cooking_fuel": target, "mixer": "none"}), {
        "title": "An induction cooktop for the daily meals",
        "why": ("Zero on-site combustion and no PM2.5 plume in the kitchen at all. On the "
                "Indian grid it also emits less CO2 than LPG per meal, though the grid factor "
                "decides that, not the stove."),
        "source": "CEA CO2 Baseline Database v21.0 (0.71 kg CO2e/kWh); LPG 2.98 kg CO2e/kg",
        "cost_inr": 4000,
        "runtime_inr_yr": -1200,
        "effort": "One purchase, a dedicated circuit",
        "tags": ["kitchen", "climate", "cost"],
    }


def i_keep_cooker_out(home, habits, tr, people, ambient):
    return _patch(habits={"cook_minutes": max(25, habits.cook_minutes - 20)}), {
        "title": "Shorter, higher-heat cooking: pressure-cook, lid on, one pot",
        "why": ("Kitchen PM2.5 accumulates with burner-minutes, so the fix is fewer of them. "
                "A pressure cooker cuts both the time and the fuel; the plume is proportional "
                "to the time the stove is lit."),
        "source": "Engineering estimate from stove emission rates; ACP 2017 emission factors",
        "cost_inr": 0,
        "runtime_inr_yr": -600,
        "effort": "Change of method",
        "tags": ["kitchen", "free", "cost"],
    }


def i_geotag_burn(home, habits, tr, people, ambient):
    return _patch(), {
        "title": "Report a burning site or a smoking genset in your ward",
        "why": ("Open waste burning is the one source a resident can get shut down in days, "
                "because GRAP I already bans it and a geotagged photo is enough to route a "
                "complaint. This is the highest-leverage act outside your own gate, even "
                "though no app can put a percentage on it."),
        "source": "CAQM GRAP Stage I; municipal complaint channels",
        "cost_inr": 0,
        "runtime_inr_yr": 0,
        "effort": "One report",
        "tags": ["community", "free"],
        "unquantified": True,
    }


def i_plant_trees(home, habits, tr, people, ambient):
    return _patch(), {
        "title": "Plant and water a shade tree, and stop paving the yard",
        "why": ("This does not clean today's air and we will not pretend it does. It cuts the "
                "dust your household resuspends and the heat that drives ozone, over years. "
                "Treat it as the long game, not as protection this week."),
        "source": "CPCB road-dust share; urban heat-island literature",
        "cost_inr": 600,
        "runtime_inr_yr": 400,
        "effort": "Seasonal, repeated",
        "tags": ["community", "climate", "long"],
        "unquantified": True,
    }


CATALOGUE: dict[str, dict[str, Any]] = {
    "cleaner":         {"fn": i_cleaner},
    "diy_filter":      {"fn": i_diy_filter},
    "kitchen_exhaust": {"fn": i_kitchen_exhaust},
    "clean_fuel":      {"fn": i_clean_fuel},
    "no_burn":         {"fn": i_no_burn},
    "mask_commute":    {"fn": i_mask_commute},
    "shift_commute":   {"fn": i_shift_commute},
    "window_timing":   {"fn": i_window_timing},
    "cook_time":       {"fn": i_cook_time},
    "stop_incense":    {"fn": i_stop_incense},
    "exercise_time":   {"fn": i_exercise_time},
    "induction":       {"fn": i_induction},
    "keep_cooker_out": {"fn": i_keep_cooker_out},
    "geotag_burn":     {"fn": i_geotag_burn},
    "plant_trees":     {"fn": i_plant_trees},
}


def apply_patch(home: E.Home, habits: E.Habits, tr: E.Transport, patch: dict):
    h = replace(home, **patch.get("home", {})) if patch.get("home") else home
    ha = replace(habits, **patch.get("habits", {})) if patch.get("habits") else habits
    t = replace(tr, **patch.get("transport", {})) if patch.get("transport") else tr
    return h, ha, t


def simulate(
    key: str,
    home: E.Home,
    habits: E.Habits,
    tr: E.Transport,
    people: list[E.Person],
    ambient: E.Ambient,
    office: bool = True,
) -> dict:
    """Run one intervention and return before/after dose with its uncertainty band."""
    spec = CATALOGUE.get(key)
    if not spec:
        return {"ok": False, "error": f"unknown intervention: {key}"}

    patch, meta = spec["fn"](home, habits, tr, people, ambient)
    home2, habits2, tr2 = apply_patch(home, habits, tr, patch)

    def run(scenario):
        return (
            E.evaluate(people, ambient, home, habits, tr, scenario, office),
            E.evaluate(people, ambient, home2, habits2, tr2, scenario, office),
        )

    b_mid, a_mid = run("mid")
    b_lo, a_lo = run("low")
    b_hi, a_hi = run("high")
    delta = E.compare(b_mid, a_mid)

    saved_lo = b_lo["household_dose_ug"] - a_lo["household_dose_ug"]
    saved_hi = b_hi["household_dose_ug"] - a_hi["household_dose_ug"]
    band = sorted([
        round((saved_lo / b_lo["household_dose_ug"] * 100) if b_lo["household_dose_ug"] else 0, 1),
        round((saved_hi / b_hi["household_dose_ug"] * 100) if b_hi["household_dose_ug"] else 0, 1),
    ])

    emis0 = E.household_emissions(home, habits, tr, len(people))
    emis1 = E.household_emissions(home2, habits2, tr2, len(people))

    # who benefits: the per-person delta, so the app can say "this one is for Amma"
    per_person = []
    for i, p in enumerate(people):
        before = b_mid["people"][i]
        after = a_mid["people"][i]
        per_person.append({
            "name": p.name,
            "before": before["dose_ug"],
            "after": after["dose_ug"],
            "saved": before["dose_ug"] - after["dose_ug"],
            "pct": round((before["dose_ug"] - after["dose_ug"]) / before["dose_ug"] * 100, 1)
            if before["dose_ug"] else 0.0,
        })
    per_person.sort(key=lambda r: -r["pct"])

    return {
        "ok": True,
        "key": key,
        "title": meta["title"],
        "why": meta["why"],
        "source": meta["source"],
        "effort": meta.get("effort"),
        "honest": meta.get("honest"),
        "unquantified": meta.get("unquantified", False),
        "cost_inr": meta.get("cost_inr", 0),
        "runtime_inr_yr": meta.get("runtime_inr_yr", 0),
        "tags": meta["tags"],
        "effect": delta,
        "band_pct": band,
        "before": b_mid,
        "after": a_mid,
        "per_person": per_person,
        "emissions_before": emis0,
        "emissions_after": emis1,
        "patch": patch,
    }


def rank(
    home: E.Home,
    habits: E.Habits,
    tr: E.Transport,
    people: list[E.Person],
    ambient: E.Ambient,
    office: bool = True,
    keys: list[str] | None = None,
) -> list[dict]:
    """Score every candidate by dose saved per rupee, with a floor for honesty."""
    rows = []
    for key in keys or list(CATALOGUE):
        r = simulate(key, home, habits, tr, people, ambient, office)
        if not r.get("ok"):
            continue
        pct = max(r["effect"]["pct"], 0.0)
        # A household average hides concentrated benefit. Switching a wood
        # stove barely moves a 4-person household total, but it cuts the dose of
        # the person who cooks by a quarter. Ranking on the household average
        # alone would bury exactly the intervention that protects the person
        # carrying the most risk, so the score is half household, half
        # worst-affected person, and the UI shows both numbers.
        worst = r["per_person"][0] if r["per_person"] else {"name": None, "pct": 0}
        benefit = 0.5 * pct + 0.5 * max(worst["pct"], 0.0)
        # Benefit per rupee, with a floor under "free". A Rs 0 change is not
        # infinitely valuable, and letting it be treated that way would bury a
        # Rs 400 mask that removes 40% of a commuter's dose under a free habit
        # that removes 2%. The floor treats anything under Rs 300 as Rs 300.
        cost_effective = max(r["cost_inr"], 300)
        value = benefit / math.sqrt(cost_effective) if not r.get("unquantified") else 0.0
        rows.append({
            "key": key,
            "title": r["title"],
            "pct": r["effect"]["pct"],
            "worst_person": worst["name"],
            "worst_pct": worst["pct"],
            "band_pct": r["band_pct"],
            "cost_inr": r["cost_inr"],
            "runtime_inr_yr": r["runtime_inr_yr"],
            "effort": r["effort"],
            "honest": r.get("honest"),
            "unquantified": r.get("unquantified", False),
            "tags": r["tags"],
            "value_score": round(value, 3),
            "source": r["source"],
            "why": r["why"],
            "per_person": r["per_person"],
        })
    rows.sort(key=lambda r: (-r["value_score"], -r["pct"]))

    # Two entries that describe the same physical change (moving gas cooking to
    # electricity is both "clean fuel" and "induction") must not appear twice
    # with identical numbers. Keep the cheaper one and say nothing about the
    # other, rather than showing a duplicate the reader has to reconcile.
    seen_effect: set[tuple[str, float]] = set()
    deduped = []
    for r in rows:
        if r["key"] in ("clean_fuel", "induction"):
            key = ("fuel", round(r["pct"], 1))
            if key in seen_effect:
                continue
            seen_effect.add(key)
        deduped.append(r)
    return deduped


def plan_for_person(catalogue: list[dict], person: E.Person) -> list[dict]:
    """
    Reorder the same list for one household member. Children and people with
    asthma get indoor and kitchen items first; a commuting adult gets the mask
    and mode shift first.
    """
    def score(item):
        s = item["value_score"] + (0.01 if item["pct"] > 0 else 0)
        if person.age < 5 or "asthma" in person.conditions or "copd" in person.conditions:
            if "indoor" in item["tags"] or "kitchen" in item["tags"]:
                s *= 1.8
        if person.age >= 65:
            if "outdoor" in item["tags"]:
                s *= 0.7
            if "indoor" in item["tags"]:
                s *= 1.5
        if "commute" in item["tags"] and person.commutes:
            s *= 1.3
        if "kitchen" in item["tags"] and person.cooks:
            s *= 1.5
        return s

    return sorted(catalogue, key=lambda i: -score(i))


def daily_brief(ambient, home, habits, tr, people, profile, office=True, ncr: bool = True) -> dict:
    """The one screen a family reads at 07:00."""
    aqi = aqi_compute(pm25=ambient.pm25, pm10=ambient.pm10, no2=ambient.no2)
    grap = grap_stage(aqi["aqi"], in_ncr=ncr)
    base = E.evaluate(people, ambient, home, habits, tr, "mid", office)
    indoor = E.indoor_concentration(ambient.pm25, home, habits)
    kitchen = E.kitchen_concentration(max(ambient.pm25, 60), home, habits)
    worst = E.worst_hour(ambient)
    best = E.cleanest_hour(ambient)
    trough = E.next_trough(ambient)
    peak_next = E.next_peak(ambient)
    elevated = E.is_elevated_now(ambient)

    children = [p for p in people if p.age < 13]
    elders = [p for p in people if p.age >= 65]
    sensitive = [p for p in people if p.sensitivity >= 1.4]

    return {
        "aqi": aqi,
        "grap": grap,
        "who": who_band(ambient.pm25),
        "ambient_pm25": ambient.pm25,
        "ambient_label": ambient.label,
        "ambient_source": ambient.source,
        "indoor_pm25": indoor,
        "kitchen_pm25": kitchen,
        "worst_hour": worst,
        "best_hour": best,
        # The forward window. `worst_hour` and `best_hour` are extrema over the
        # whole 0-23 series and are therefore often in the past; a daily screen
        # has to answer "what happens next", which is these two.
        "next_trough": trough,
        "next_peak": peak_next,
        "elevated_now": elevated,
        "household": base,
        "children_at_risk": [p.name for p in children],
        "elders_at_risk": [p.name for p in elders],
        "sensitive_people": [{"name": p.name, "sensitivity": p.sensitivity} for p in sensitive],
        "profile": profile,
        "headline": _headline(aqi, ambient, indoor),
        "now": _now_actions(aqi, grap, ambient, indoor, home, habits, worst, best,
                            trough=trough, peak_next=peak_next, elevated=elevated),
    }


def _headline(aqi: dict, ambient, indoor: float) -> str:
    mult = round(ambient.pm25 / C.WHO_PM25_24H.value, 1)
    if aqi["aqi"] >= 401:
        return (f"Severe. Outdoor PM2.5 is {ambient.pm25:g} ug/m3, {mult}x the WHO 24-hour "
                f"guideline. Inside your home it models at {indoor:g}. Today is a stay-in day.")
    if aqi["aqi"] >= 301:
        return (f"Very poor. {ambient.pm25:g} ug/m3 outside, {indoor:g} inside. "
                f"Short trips only, mask on, filter running.")
    if aqi["aqi"] >= 201:
        return (f"Poor. {ambient.pm25:g} ug/m3 outside, {indoor:g} inside. "
                f"Exercise indoors and keep windows shut through the morning.")
    if aqi["aqi"] >= 101:
        return (f"Moderate. {ambient.pm25:g} ug/m3 outside, {indoor:g} inside. "
                f"Fine for most people; sensitive lungs should take it easier.")
    return f"{ambient.pm25:g} ug/m3 outside, {indoor:g} inside. A good day to open the windows."


def _trough_when(trough: dict) -> str:
    """How to name the clean window: an hour, or 'now' when it is the reading in hand."""
    if trough.get("hour") is None:
        return "now"
    return f"{trough['hour']:02d}:00"


def _now_actions(aqi, grap, ambient, indoor, home, habits, worst, best,
                 trough=None, peak_next=None, elevated=False) -> list[dict]:
    acts: list[dict] = []
    # A kitchen with no extraction and a gas flame is still the strongest
    # indoor source in most homes, even when the stove is not a biomass one.
    if home.kitchen_exhaust == "none" and home.cooking_fuel in ("lpg", "png"):
        acts.append({"icon": "stove", "text": "Cook with the kitchen window wide open and the door shut.",
                     "why": ("Even on gas, cooking adds 40-70 ug/m3 indoors. With no exhaust, the open "
                             "window is the free version, and the shut door keeps it out of the beds.")})
    if aqi["aqi"] >= 201 and elevated:
        # Only while it is actually elevated. Telling someone at 20:00 to "keep
        # windows shut until the lull" when the peak was at 07:00 is advice
        # about the past, and it is the fastest way to lose their trust.
        acts.append({"icon": "window", "text": "Keep the windows shut for now.",
                     "why": (f"Air is near today's peak ({ambient.pm25:g} ug/m3). "
                             + (f"The next low is around {_trough_when(trough)} at {trough['pm25']:g}."
                                if trough else ""))})
    elif aqi["aqi"] >= 201 and trough:
        now_is_low = trough.get("hour") is None
        acts.append({"icon": "window",
                     "text": ("Open the windows now, while it is at its cleanest."
                              if now_is_low else f"Open the windows around {_trough_when(trough)}."),
                     "why": (f"Air is easing now and this is the cleanest point in the "
                             f"next twelve hours, at {trough['pm25']:g} ug/m3."
                             if now_is_low else
                             f"Air is easing now. {_trough_when(trough)} is the cleanest window in the "
                             f"next twelve hours, at {trough['pm25']:g} ug/m3.")})
    if aqi["aqi"] >= 201:
        acts.append({"icon": "mask", "text": "N95 for anyone stepping out, children included.",
                     "why": "A fitted N95 removes about 97% of fine particles; cloth removes about half."})
    if home.cooking_fuel in ("biomass", "kerosene"):
        acts.append({"icon": "stove", "text": "Cook with the exhaust on and the kitchen door shut.",
                     "why": "Your stove is the strongest source in the house today, stronger than the street."})
    if indoor > 60 and home.cleaner == "none":
        acts.append({"icon": "filter",
                     "text": "No filter in the house yet. A box-fan build tonight is the cheapest way in.",
                     "why": ("Field trials cut bedroom PM2.5 by 42-60% with one unit. A 20-inch fan "
                             "and a MERV13 filter does most of that for about Rs 800.")})
    elif indoor > 60 and home.cleaner != "none":
        acts.append({"icon": "filter", "text": "Filter running in the bedroom from an hour before bed.",
                     "why": "You already own one. The gain is in running it through the night, door shut."})
    if habits.outdoor_exercise and aqi["aqi"] >= 201 and trough:
        acts.append({"icon": "run", "text": "Walk indoors today, or out at the afternoon low.",
                     "why": (f"The next low is around {_trough_when(trough)} at {trough['pm25']:g} ug/m3. "
                             f"You inhale roughly twice as much air when exercising.")})
    if grap.get("applies"):
        acts.append({"icon": "gov", "text": grap["label"], "why": grap["detail"]})
    return acts


def school_guidance(aqi_value: int, people: list[E.Person]) -> dict:
    """What to do about school and outdoor play, scaled to the AQI."""
    children = [p for p in people if p.age < 18]
    if not children:
        return {"applies": False}
    if aqi_value >= 401:
        return {
            "applies": True, "level": "severe",
            "advice": ("Keep children home if the school has no filtered classroom. Under GRAP "
                       "III and IV, physical classes up to Class V may already be suspended in "
                       "Delhi-NCR, and upper classes up to IX at Stage IV."),
            "source": "CAQM GRAP Stage III/IV schedule; CPCB health advisory",
        }
    if aqi_value >= 301:
        return {
            "applies": True, "level": "very_poor",
            "advice": ("No outdoor play or assembly. Indoor PE only. Worth asking whether the "
                       "classroom has any filtration at all."),
            "source": "CPCB health advisory for Very Poor",
        }
    if aqi_value >= 201:
        return {
            "applies": True, "level": "poor",
            "advice": "Keep outdoor games under 30 minutes, and not in the morning peak.",
            "source": "CPCB health advisory for Poor",
        }
    return {"applies": True, "level": "moderate", "advice": "Normal outdoor play is fine.",
            "source": "CPCB"}

def combine(
    keys: list[str],
    home: E.Home,
    habits: E.Habits,
    tr: E.Transport,
    people: list[E.Person],
    ambient: E.Ambient,
    office: bool = True,
) -> dict:
    """
    What a household gets from doing several things at once.

    `simulate` answers one intervention. This answers the question a family
    actually asks — "if I do these four, where do we end up?" — because
    interventions do not stack additively. A filter and a chimney both cut the
    indoor concentration, and once the filter has taken 34% the chimney's
    contribution to the total is smaller than its solo number suggests.
    Reporting the sum of individual percentages would overstate every
    combination, so each set is applied and the day is re-run from scratch.

    The order is deliberately the caller's: patches are dict-merged, and a later
    patch overwriting an earlier one is a real conflict, which is reported
    rather than silently resolved. "Fit a chimney" and "cook on electric" cannot
    both be true if one changes the fuel and the other assumes the fuel.
    """
    unknown = [k for k in keys if k not in CATALOGUE]
    if unknown:
        return {"ok": False, "error": f"unknown intervention: {', '.join(unknown)}"}

    base = E.evaluate(people, ambient, home, habits, tr, "mid", office)
    base_lo = E.evaluate(people, ambient, home, habits, tr, "low", office)
    base_hi = E.evaluate(people, ambient, home, habits, tr, "high", office)

    patch: dict[str, dict] = {}
    applied: list[dict] = []
    conflicts: list[dict] = []

    # Order must not change the answer. Two interventions can both write the same
    # field (cleaner: HEPA vs box fan), and "first one wins" made the household
    # total depend on which box the user ticked first — 24.3% or 26.2% for the
    # same pair. Sort the keys, and resolve a shared field by the catalogue's own
    # capability ranking (HEPA over box fan, chimney over fan, electric over LPG),
    # so the result is a function of the SET the household chose.
    RANK = {"cleaner": CLEANER_RANK, "kitchen_exhaust": EXHAUST_RANK,
            "cooking_fuel": FUEL_RANK, "mixer": FUEL_RANK}

    def rank_of(field_name: str, value) -> int:
        return RANK.get(field_name, {}).get(value, -1)

    ordered = sorted(set(keys))
    for key in ordered:
        spec = CATALOGUE[key]
        p, meta = spec["fn"](home, habits, tr, people, ambient)
        for section in ("home", "habits", "transport"):
            for field_name, value in (p.get(section) or {}).items():
                if section in patch and field_name in patch[section] \
                        and patch[section][field_name] != value:
                    # Keep the more capable value, not the earlier one.
                    incumbent = patch[section][field_name]
                    keep_new = rank_of(field_name, value) > rank_of(field_name, incumbent)
                    conflicts.append({
                        "field": f"{section}.{field_name}",
                        "kept": value if keep_new else incumbent,
                        "dropped": incumbent if keep_new else value,
                        "by": key,
                    })
                    if keep_new:
                        patch[section][field_name] = value
                    continue
                patch.setdefault(section, {})[field_name] = value
        applied.append({
            "key": key,
            "title": meta["title"],
            "cost_inr": meta.get("cost_inr", 0),
            "runtime_inr_yr": meta.get("runtime_inr_yr", 0),
            "solo_pct": round(
                (base["household_dose_ug"] - E.evaluate(
                    people, ambient,
                    *apply_patch(home, habits, tr, p), "mid", office
                )["household_dose_ug"]) / base["household_dose_ug"] * 100, 1
            ) if base["household_dose_ug"] else 0.0,
        })

    h2, ha2, t2 = apply_patch(home, habits, tr, patch)
    after = E.evaluate(people, ambient, h2, ha2, t2, "mid", office)
    after_lo = E.evaluate(people, ambient, h2, ha2, t2, "low", office)
    after_hi = E.evaluate(people, ambient, h2, ha2, t2, "high", office)

    def pct(before: float, aft: float) -> float:
        return round((before - aft) / before * 100, 1) if before else 0.0

    total = pct(base["household_dose_ug"], after["household_dose_ug"])
    band = sorted([
        pct(base_lo["household_dose_ug"], after_lo["household_dose_ug"]),
        pct(base_hi["household_dose_ug"], after_hi["household_dose_ug"]),
    ])

    # The honest arithmetic note: what the individual percentages would have
    # claimed if they were added up, beside what actually happens.
    naive_sum = round(sum(a["solo_pct"] for a in applied), 1)

    per_person = []
    for i, person in enumerate(people):
        b = base["people"][i]
        a = after["people"][i]
        per_person.append({
            "name": person.name,
            "before": round(b["dose_ug"], 1),
            "after": round(a["dose_ug"], 1),
            "saved": round(b["dose_ug"] - a["dose_ug"], 1),
            "pct": pct(b["dose_ug"], a["dose_ug"]),
        })
    per_person.sort(key=lambda r: -r["pct"])

    emis0 = E.household_emissions(home, habits, tr, len(people))
    emis1 = E.household_emissions(h2, ha2, t2, len(people))

    return {
        "ok": True,
        "keys": keys,
        "applied": applied,
        "conflicts": conflicts,
        "effect": {
            "dose_before": round(base["household_dose_ug"], 1),
            "dose_after": round(after["household_dose_ug"], 1),
            "dose_saved_ug": round(base["household_dose_ug"] - after["household_dose_ug"], 1),
            "pct": total,
            "cig_before": base["household_cigarettes"],
            "cig_after": after["household_cigarettes"],
        },
        "band_pct": band,
        "naive_sum_pct": naive_sum,
        "overlap_pct": round(naive_sum - total, 1),
        "per_person": per_person,
        "emissions_before": emis0,
        "emissions_after": emis1,
        "cost_inr": sum(a["cost_inr"] for a in applied),
        "runtime_inr_yr": sum(a["runtime_inr_yr"] for a in applied),
        "after_state": {
            "home": {k: v for k, v in patch.get("home", {}).items()},
            "habits": {k: v for k, v in patch.get("habits", {}).items()},
            "transport": {k: v for k, v in patch.get("transport", {}).items()},
        },
    }
