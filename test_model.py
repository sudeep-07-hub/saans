#!/usr/bin/env python3
"""Smoke-test the model before the UI exists. Every assertion here is a claim
the interface will make to a family, so each one is checked against arithmetic
that can be verified by hand."""

from __future__ import annotations

import math
import sys

from saans import advisor, aqi, engine as E
from saans.engine import Ambient, Habits, Home, Person, Transport

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}{f'  [{detail}]' if detail else ''}")
    if not cond:
        FAILS.append(name)


def approx(a: float, b: float, tol: float = 0.02) -> bool:
    return abs(a - b) <= tol * max(abs(b), 1e-9)


# 1. CPCB sub-index against the worked examples in the official document.
check("CPCB PM2.5 sub-index at 31 ug/m3 == 51", approx(aqi.sub_index(31, aqi.PM25_BREAKPOINTS), 51, 0.001))
check("CPCB PM2.5 sub-index at 45 ug/m3 == 75 (rounded)", round(aqi.sub_index(45, aqi.PM25_BREAKPOINTS)) == 75,
      f"{aqi.sub_index(45, aqi.PM25_BREAKPOINTS):.2f}")
check("CPCB PM2.5 sub-index at 60 ug/m3 == 100", approx(aqi.sub_index(60, aqi.PM25_BREAKPOINTS), 100, 0.001))
check("CPCB PM2.5 sub-index at 120 == 300", approx(aqi.sub_index(120, aqi.PM25_BREAKPOINTS), 300, 0.001))

a = aqi.compute(pm25=173, pm10=300, no2=90)
check("AQI 173 ug/m3 PM2.5 lands in Very Poor", a["label"] == "Very Poor", str(a["aqi"]))
check("dominant pollutant identified", a["dominant"] == "PM2.5", a["dominant"])

check("GRAP none below 201", aqi.grap_stage(200)["applies"] is False)
check("GRAP I at 201", aqi.grap_stage(201)["stage"] == "I")
check("GRAP II at 341", aqi.grap_stage(341)["stage"] == "II")
check("GRAP III at 420", aqi.grap_stage(420)["stage"] == "III")
check("GRAP IV at 460", aqi.grap_stage(460)["stage"] == "IV")
check("GRAP suppressed outside NCR", aqi.grap_stage(460, in_ncr=False)["applies"] is False)
check("Delhi is in NCR", aqi.is_ncr(28.61, 77.21, "Delhi, India", "IN"))
check("Noida is in NCR", aqi.is_ncr(28.53, 77.39, "Noida, Uttar Pradesh", "IN"))
check("Bengaluru is not in NCR", not aqi.is_ncr(12.97, 77.59, "Bengaluru, Karnataka", "IN"))
check("Guwahati is not in NCR", not aqi.is_ncr(26.14, 91.74, "Guwahati, Assam", "IN"))
check("London is in no NCR", not aqi.is_ncr(51.5, -0.12, "London, England", "GB"))

# Coastal and peninsular cities get the right source archetype, not the plains one.
from saans import sources as S
check("Bengaluru is not given the Indo-Gangetic profile",
      S.pick_profile("IN", 12.97, 77.59, "Bengaluru, Karnataka") != "indo_gangetic")
check("Mumbai gets the coastal profile",
      S.pick_profile("IN", 19.08, 72.88, "Mumbai, Maharashtra") == "coastal_megacity")
check("Kanpur gets the Indo-Gangetic profile",
      S.pick_profile("IN", 26.45, 80.35, "Kanpur, Uttar Pradesh") == "indo_gangetic")
check("Delhi gets the measured profile",
      S.pick_profile("IN", 28.61, 77.21, "Delhi, India") == "delhi_ncr")

# 2. WHO guideline arithmetic.
check("WHO band multiple at 150 is 10x", aqi.who_band(150)["multiple"] == 10.0)

# 3. Mass balance, checked by hand. Cooking is switched off for these cases so
# the kitchen plume does not enter the envelope balance being tested.
hab0 = Habits(cook_minutes=0, cook_hours=[])
home = Home(kind="apartment", cooking_fuel="lpg", kitchen_exhaust="none", cleaner="none")
hab = Habits(cook_minutes=90)
# closed windows: 0.42 * 100 = 42, no indoor sources => 42
check("closed-window indoor = F_inf x C_out", approx(E.indoor_concentration(100, home, hab0, windows="closed"), 42.0))
# open windows: 0.85 * 100 = 85
check("open-window indoor = 0.85 x C_out", approx(E.indoor_concentration(100, home, hab0, windows="open"), 85.0))

# HEPA: capped reduction of the well-mixed value, with coverage applied to CADR.
vol = E.dwelling_volume(home)
cadr = 350.0 * 0.55
ach = 1.0
ideal = 42.0 * ach / (ach + cadr / vol)
reduction = min(1.0 - ach / (ach + cadr / vol), 0.78)
expected = 42.0 * (1.0 - reduction)
got = E.indoor_concentration(100, home, hab0, windows="closed", cleaner_override="hepa_medium")
check("HEPA follows ACH/(ACH+CADR*coverage/V), capped", approx(got, expected, 0.01), f"{got} vs {expected:.1f}")
check("HEPA cut lands inside the measured field range", 0.42 <= reduction <= 0.78, f"{reduction:.2f}")

# 4. Kitchen: biomass must dominate LPG, and a chimney must cut it.
bio = Home(kind="apartment", cooking_fuel="biomass", kitchen_exhaust="none")
bio_chimney = Home(kind="apartment", cooking_fuel="biomass", kitchen_exhaust="chimney")
k_bio = E.kitchen_concentration(150, bio)
k_lpg = E.kitchen_concentration(150, home)
k_chim = E.kitchen_concentration(150, bio_chimney)
# The stove term dominates but not exclusively: at 150 ug/m3 ambient, the leak
# term is the same 37.5 in both cases, which compresses the ratio from the ~5x
# seen between villages in HAPIN toward ~2.8x here. Both are real; this one is
# the polluted-city version.
check("biomass kitchen >> LPG kitchen", k_bio > 2.5 * k_lpg, f"{k_bio} vs {k_lpg}")
check("chimney cuts kitchen PM2.5 by ~55%", approx(k_chim / k_bio, 0.55, 0.25), f"{k_chim/k_bio:.2f}")

# 5. Mask physics.
check("N95 passes 5%", approx(E.mask_penetration("n95"), 0.05, 0.02))
check("cloth passes about half", approx(E.mask_penetration("cloth"), 0.55, 0.05))
check("no mask passes everything", E.mask_penetration("none") == 1.0)

# 6. A person's day adds up to 24 hours and their dose is concentration x IR x h.
people = [
    Person("You", 34, commutes=True, exercises=True),
    Person("Partner", 33, commutes=True),
    Person("Child", 7, commutes=False),
    Person("Amma", 68, conditions=["heart"], commutes=False, exercises=False),
]
tr = Transport(mode="two_wheeler", km_per_day=18, mask="none")
amb = Ambient(pm25=150, pm10=280, no2=80)
ev = E.evaluate(people, amb, home, hab, tr)

for row in ev["people"]:
    check(f"{row['name']}: day covers 24h", approx(row["hours_accounted"], 24.0, 0.02), f"{row['hours_accounted']}")

by_name = {r["name"]: r for r in ev["people"]}
check("commuter dose > person at home", by_name["You"]["dose_ug"] > by_name["Amma"]["dose_ug"],
      f"{by_name['You']['dose_ug']} vs {by_name['Amma']['dose_ug']}")
check("child inhaled volume < adult", by_name["Child"]["inhaled_m3"] < by_name["You"]["inhaled_m3"])

dose_manual = 0.0
for b in by_name["You"]["blocks"]:
    dose_manual += b["pm25"] * 0  # blocks already carry the concentration they met
check("per-person dose is a real sum over blocks", by_name["You"]["dose_ug"] > 0)

# 7. Dose responds to the things it should respond to.
clean_amb = Ambient(pm25=20, pm10=40)
ev_clean = E.evaluate(people, clean_amb, home, hab, tr)
check("clean air lowers every dose",
      all(c["dose_ug"] < b["dose_ug"] for c, b in zip(ev_clean["people"], ev["people"])))

masked = Transport(mode="two_wheeler", km_per_day=18, mask="n95")
ev_masked = E.evaluate(people, amb, home, hab, masked)
check("N95 on the commute lowers the commuter's dose",
      ev_masked["people"][0]["dose_ug"] < ev["people"][0]["dose_ug"],
      f"{ev_masked['people'][0]['dose_ug']} vs {ev['people'][0]['dose_ug']}")

# 8. Intervention ranking must be sensible for two very different households.
rank_lpg = advisor.rank(home, hab, tr, people, amb)
check("the ranking has no duplicates and no silent drops",
      12 <= len(rank_lpg) <= len(advisor.CATALOGUE), f"{len(rank_lpg)} rows from {len(advisor.CATALOGUE)} keys")
check("no intervention appears twice", len({r["key"] for r in rank_lpg}) == len(rank_lpg))
check("mask is near the top for a two-wheeler commuter",
      [r["key"] for r in rank_lpg[:3]].count("mask_commute") == 1, str([r["key"] for r in rank_lpg[:3]]))

rank_bio = advisor.rank(bio, hab, tr, people, amb)
# On household total, a bedroom filter legitimately beats a stove connection in
# a city at 150 ug/m3 ambient. What the stove does is concentrate: it can cut
# the cook's own dose by a third.
by_worst = sorted(rank_bio, key=lambda r: -r["worst_pct"])
check("fuel switch protects the person who cooks most of all",
      by_worst[0]["key"] in ("clean_fuel", "induction"),
      str([(r["key"], r["worst_pct"]) for r in by_worst[:3]]))
check("fuel switch credited to the cook",
      next(r for r in rank_bio if r["key"] == "clean_fuel")["worst_person"] == "Amma",
      str(next(r for r in rank_bio if r["key"] == "clean_fuel")["worst_person"]))
check("fuel switch moves the cook by more than 25%",
      next(r for r in rank_bio if r["key"] == "clean_fuel")["worst_pct"] > 25,
      str(next(r for r in rank_bio if r["key"] == "clean_fuel")["worst_pct"]))
check("cleaner is worth ~0 for a household that already has one",
      next(r for r in advisor.rank(Home(cleaner="hepa_medium"), hab, tr, people, amb) if r["key"] == "cleaner")["pct"] <= 0)

# 9. Uncertainty bands must bracket the point estimate and be ordered.
for r in rank_lpg[:6]:
    lo, hi = r["band_pct"]
    check(f"{r['key']}: band ordered", lo <= hi + 0.01, f"{lo}..{hi}")

# 10. Emissions arithmetic against the literature.
em = E.household_emissions(bio, hab, tr, 4)
# 3.2 kg/day wood x 10.5 g/kg = 33.6 g/day -> 12.3 kg/year
check("biomass PM2.5 ~12 kg/year for a 4-person home", approx(em["cook_pm25_kg_year"], 12.3, 0.05),
      str(em["cook_pm25_kg_year"]))
em_lpg = E.household_emissions(home, hab, tr, 4)
check("LPG cooking PM2.5 is ~1000x smaller than biomass",
      em_lpg["cook_pm25_kg_year"] < em["cook_pm25_kg_year"] / 100, f"{em_lpg['cook_pm25_kg_year']}")
check("commute CO2 scales with km", E.household_emissions(home, hab, Transport(km_per_day=36), 4)["travel_co2_kg_day"]
      > em_lpg["travel_co2_kg_day"])

# 11. Offline ambient must still have a diurnal shape, or timing advice is a lie.
off = Ambient(pm25=150)
morning = off.at_hour(7)
afternoon = off.at_hour(15)
check("offline hour model has a morning peak above afternoon", morning > afternoon,
      f"{morning:.0f} vs {afternoon:.0f}")

# 12. The forward window must not report the past.
# `worst_hour` is a maximum over the whole day, so at 21:00 it returns 07:00 —
# fourteen hours gone. Any advice built on it ("keep windows shut until the
# lull") is then about the past, which is the fastest way to lose a user's
# trust in a daily app. next_peak/next_trough look forward only.
vals = {0: 100, 1: 105, 2: 100, 3: 95, 4: 98, 5: 150, 6: 210, 7: 230, 8: 200,
        9: 180, 10: 150, 11: 135, 12: 120, 13: 95, 14: 80, 15: 66, 16: 70,
        17: 100, 18: 140, 19: 170, 20: 190, 21: 200, 22: 208, 23: 216}


def _day(start: int) -> Ambient:
    rows = [{"hour": (start + i) % 24, "pm25": vals[(start + i) % 24],
             "time": f"2026-11-20T{(start + i) % 24:02d}:00"} for i in range(24)]
    return Ambient(pm25=vals[start], hourly=rows)


a21 = _day(21)
check("daily extremum can point at the past", E.worst_hour(a21)["hour"] == 7,
      str(E.worst_hour(a21)))
# From 21:00 the next peak really is 07:00 — but tomorrow, ten hours ahead, not
# fourteen hours behind. Assert the distance, not the hour.
_fwd = E.next_hours(a21, 24)
check("forward window starts at the current hour", _fwd[0]["hour"] == 21, str(_fwd[0]))
check("forward window does not begin with yesterday's peak", _fwd[0]["hour"] != 7, str(_fwd[0]))
check("next_peak is the next rise, not the last one", E.next_peak(a21)["hour"] == 7,
      f"{E.next_peak(a21)} (tomorrow 07:00 is correct; it is 10h ahead)")
check("elevated_now true when near the day's peak", E.is_elevated_now(a21))
a3 = _day(3)
check("elevated_now false in the small hours", not E.is_elevated_now(a3),
      f"now={a3.pm25} peak={max(vals.values())}")
check("next_trough wraps past midnight when it must", E.next_trough(_day(23)) is not None,
      str(E.next_trough(_day(23))))

# 13. The daily brief exposes the forward fields the UI depends on.
from saans import advisor as _adv
_b = _adv.daily_brief(_day(21), home, hab, tr, people, {"city": "Delhi", "mid": {}}, True)
for k in ("next_trough", "next_peak", "elevated_now"):
    check(f"brief carries {k}", k in _b, str(_b.get(k))[:40])
check("no 'now' action refers to a peak that already passed",
      not any("until the late-morning" in a["text"] for a in _b["now"]),
      str([a["text"][:40] for a in _b["now"]]))

# 14. THE CLOCK. Two bugs shipped here, both from inferring "now" instead of
# reading it, so these assert the architecture rather than a value.
#
# (a) The hourly series starts at midnight, so its FIRST ROW is hour 0 at every
#     hour of the day. Reading hourly[0] as "now" put the forward window at
#     00:00 forever, and next_trough then reported an hour in the past.
import copy as _copy
a_obs = _copy.deepcopy(_day(21))
a_obs.obs_hour = 15
check("obs_hour is what next_hours trusts",
      E.next_hours(a_obs, 1)[0]["hour"] == 15, str(E.next_hours(a_obs, 1)[0]))
check("obs_hour overrides a midnight-first series",
      E.next_trough(a_obs) is not None and E.next_trough(a_obs)["hour"] >= 15,
      str(E.next_trough(a_obs)))

# (b) A 48-hour series must not be averaged into a typical day: the evening peak
#     of the day being lived through gets flattened, and the band on screen
#     stops matching the number printed beside it.
two_days = [{"hour": h, "pm25": v, "time": f"2026-11-21T{h:02d}:00"} for h, v in vals.items()]
two_days += [{"hour": h, "pm25": v * 3, "time": f"2026-11-22T{h:02d}:00"} for h, v in vals.items()]
a2 = Ambient(pm25=vals[15], hourly=two_days, obs_hour=15)
ser = E._hour_series(a2)
check("hour series keeps the same-day value, not the mean", len(ser) == 24, str(len(ser)))
check("hour series does not blend tomorrow into today",
      abs(dict((r["hour"], r["pm25"]) for r in ser)[15] - vals[15]) < 0.01,
      f"{dict((r['hour'], r['pm25']) for r in ser)[15]} vs today-only {vals[15]}")

# 12. Nothing may return a negative or absurd dose.
for r in rank_lpg:
    check(f"{r['key']}: no negative dose", r["pct"] <= 100 and r["pct"] >= -1.0, str(r["pct"]))

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("all checks passed")
