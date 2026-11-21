#!/usr/bin/env python3
"""
Tests for the generative layer.

The claims under test:
  1. no digit the model writes ever reaches the user;
  2. no token it invents resolves to anything;
  3. the plan's structure (order, cost, effect) cannot be altered by the model;
  4. a household with no children gets no paragraph about children;
  5. the deterministic plan is complete when the model is absent.

These are adversarial inputs on purpose. A 4B model will produce exactly these
failures and the boundary has to hold anyway.
"""

from __future__ import annotations

import sys

from saans import advisor, engine as E, narrator
from saans.engine import Ambient, Habits, Home, Person, Transport

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}{f'  [{detail}]' if detail else ''}")
    if not cond:
        FAILS.append(name)


def fixture(cooking="lpg", cleaner="none", kids=True):
    home = Home(cooking_fuel=cooking, cleaner=cleaner)
    habits = Habits(cook_minutes=120 if cooking == "biomass" else 60)
    tr = Transport(mode="two_wheeler", km_per_day=18)
    people = [Person("You", 34, commutes=True), Person("Amma", 68, commutes=False,
                                                       conditions=["heart"])]
    if kids:
        people.append(Person("Child", 7, commutes=False))
    amb = Ambient(pm25=148, pm10=280)
    brief = advisor.daily_brief(amb, home, habits, tr, people,
                               {"city": "Delhi", "mid": {"Traffic": 25, "Industry": 26}}, True)
    brief["stamp"] = "now"
    ranked = advisor.rank(home, habits, tr, people, amb, True)
    # Mirror what /api/brief actually returns: the computed exposure row merged
    # into each person. Building the fixture from Person.__dict__ alone is the
    # bug that handed the model "None ug" for every dose, and a fixture that
    # reproduces the bug cannot catch it.
    people_rows = brief["household"]["people"]
    payload_people = [
        row | {"sensitivity": row.get("sensitivity") or person.sensitivity,
               "conditions": list(person.conditions),
               "pregnant": person.pregnant,
               "cooks": person.cooks,
               "commutes": person.commutes}
        for person, row in zip(E._with_roles(people), people_rows)
    ]
    return home, habits, tr, people, amb, brief, ranked, payload_people


home, habits, tr, people, amb, brief, ranked, ppl = fixture()
day = narrator.skeleton(brief, ranked, ppl)
tmap = narrator.tokens(brief, day, ranked, ppl, {"city": "Delhi", "mid": {"Traffic": 25}})

# --- 1. structure is Python's, not the model's -----------------------------
check("skeleton produced actions", len(day["items"]) >= 3, str(len(day["items"])))
check("skeleton is in the order a day happens",
      [i["order"] for i in day["items"]] == sorted(i["order"] for i in day["items"]))
check("the top option is the highest-ranked intervention",
      day["top"]["key"] == ranked[0]["key"], f"{day['top']['key']} vs {ranked[0]['key']}")

# --- 2. raw digits never survive ------------------------------------------
hostile = {
    "opening": "Outside it is 999 ug/m3, which is 41x the WHO guideline. Amma is affected.",
    "for_children": "Your child is 7 years old and needs 12 hours of clean air.",
    "what_this_does_not_fix": "The city is at 148 for 300 days a year, and 500 more.",
}
clean, notes = narrator.enforce(dict(hostile), day, tmap, brief, ppl)
blob = " ".join([clean["opening"], clean["for_children"], clean["what_this_does_not_fix"]])
import re
# Strip the shapes that are legitimately allowed (clock times, a named age),
# then assert nothing numeric is left.
residual = re.sub(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", " ", blob)
residual = re.sub(r"\bAmma\s*,\s*68\b", " ", residual, flags=re.I)
check("no unverified digits survive enforcement", not re.search(r"\d", residual), residual[:90])
check("sentences without numbers are kept", "Amma is affected" in clean["opening"], clean["opening"])
check("enforcement reports what it removed", len(notes) >= 2, str(len(notes)))

# --- 2b. the legitimate shapes DO survive -------------------------------
# A clock time and a named person's age are unambiguous on their own, so they
# must pass. Allow-listing every small integer for the sake of clock hours
# would have let "3x" through, which is why these are pattern-matched.
legit = {
    "opening": "Amma, 68, cooks at 20:00 most nights. The child is 7 years old.",
    "for_children": "",
    "what_this_does_not_fix": "",
}
legit_out, legit_notes = narrator.enforce(dict(legit), day, tmap, brief, ppl)
check("a clock time survives", "20:00" in legit_out["opening"], legit_out["opening"])
check("a named person's age survives", "Amma, 68" in legit_out["opening"], legit_out["opening"])
check("an age phrase survives", "7 years old" in legit_out["opening"], legit_out["opening"])

# But the same digits in a fabricated claim must still die.
fabricated = {
    "opening": "This is 3x better. It cuts a full 87% of the dose. Only 22 minutes of exposure.",
    "for_children": "",
    "what_this_does_not_fix": "",
}
fab_out, fab_notes = narrator.enforce(dict(fabricated), day, tmap, brief, ppl)
fab_blob = fab_out["opening"]
check("a bare multiplier is still deleted", "3x" not in fab_blob, repr(fab_blob[:80]))
check("a fabricated percentage is still deleted", "87%" not in fab_blob, repr(fab_blob[:80]))
check("a fabricated minute count is still deleted", "22 minutes" not in fab_blob, repr(fab_blob[:80]))
check("an unsupported 99% is still deleted", "99%" not in fab_blob, repr(fab_blob[:80]))

# --- 2c. domain names are identifiers, not claims ----------------------
# "PM2.5" and "N95" carry digits but are names. Killing sentences over them
# deletes correct text, which is its own kind of failure: the plan loses the
# most important sentence it had.
domain = {
    "opening": "The outdoor PM2.5 is {{OUT}}. An N95 filters most of it. PM10 is not modelled here.",
    "for_children": "Wear the N95 on the road, and the KN95 if that is what you have.",
    "what_this_does_not_fix": "",
}
dom_out, dom_notes = narrator.enforce(dict(domain), day, tmap, brief, ppl)
check("a sentence naming PM2.5 survives", "PM2.5" in dom_out["opening"], dom_out["opening"])
check("a sentence naming N95 survives", "N95" in dom_out["opening"], dom_out["opening"])
check("PM10 survives", "PM10" in dom_out["opening"], dom_out["opening"])
check("KN95 survives", "KN95" in dom_out["for_children"], dom_out["for_children"])
check("the PM2.5 token still resolved", "148" in dom_out["opening"], dom_out["opening"])

# --- 2d. a doubled unit is repaired -----------------------------------
# Tokens carry their own unit, so a model writing "{{OUT}} µg/m³" produces
# "151 µg/m³ µg/m³". That reads as broken software, and it appeared in a real
# generated plan before this was caught by reading output.
dup = {
    "opening": "Outside {{OUT}} µg/m³ and at {{WHOX}}× the guideline, with {{TOP_PCT}}% of the dose.",
    "for_children": "",
    "what_this_does_not_fix": "",
}
dup_out, _ = narrator.enforce(dict(dup), day, tmap, brief, ppl)
check("a doubled µg/m³ is collapsed", "µg/m³ µg/m³" not in dup_out["opening"], dup_out["opening"])
check("a doubled %% is collapsed", "%%" not in dup_out["opening"], dup_out["opening"])
check("a doubled ×× is collapsed", "××" not in dup_out["opening"], dup_out["opening"])
check("the single unit survives", dup_out["opening"].count("µg/m³") == 1, dup_out["opening"])

# --- 2e. per-person dose is available as a token ---------------------
# The model kept copying a real dose out of the fact sheet and getting the
# sentence deleted. The fix is to give it a token, not to loosen the rule.
check("a dose token exists per person",
      any(k.startswith("DOSE_") for k in tmap), str([k for k in tmap if k.startswith("DOSE_")][:3]))
check("a dose token carries its unit",
      all("µg" in v for k, v in tmap.items() if k.startswith("DOSE_")))

# --- 2f. the digit inside a unit is not mistaken for a number -----------
# "breathes {{EXP}} ug/m3" was deleted because the 3 in the unit looked like a
# stray figure. A unit is an identifier, like PM2.5 or N95. But a free-standing
# number the engine never produced is still a claim, and must still die.
unit_ok = {
    "opening": "The child breathes {{EXP_CHILD}} ug/m3 inside.",
    "for_children": "",
    "what_this_does_not_fix": "",
}
ok_out, ok_notes = narrator.enforce(dict(unit_ok), day, tmap, brief, ppl)
check("a token plus a redundant unit is cleaned, not deleted",
      "74." in ok_out["opening"] or "µg/m³" in ok_out["opening"], ok_out["opening"])
check("the unit suffix did not cause a deletion", len(ok_notes) == 0, str(ok_notes))
check("only one unit survives in the sentence",
      ok_out["opening"].count("m³") + ok_out["opening"].count("m3") == 1, ok_out["opening"])

unit_bad = {
    "opening": "The child breathes 86.3 ug/m3 inside.",
    "for_children": "",
    "what_this_does_not_fix": "",
}
bad_out, bad_notes = narrator.enforce(dict(unit_bad), day, tmap, brief, ppl)
check("an invented number beside a real unit is still deleted",
      "86.3" not in bad_out["opening"], repr(bad_out["opening"]))

# --- 3. tokens resolve, invented tokens do not ----------------------------
tok_text = {
    "opening": "Outside {{OUT}} and indoors {{IN}}, at {{WHOX}} the guideline.",
    "for_children": "{{MADE_UP_TOKEN}} should vanish. So should {{TOP_COST}} if unknown.",
    "what_this_does_not_fix": "Nothing else.",
}
resolved, _ = narrator.enforce(dict(tok_text), day, tmap, brief, ppl)
check("known tokens resolve to real figures",
      "148" in resolved["opening"] and "9.9" in resolved["opening"], resolved["opening"])
check("an invented token leaves no residue",
      "MADE_UP" not in resolved["for_children"] and "{{" not in resolved["for_children"],
      resolved["for_children"])
check("token resolution produces no braces anywhere",
      "{{" not in " ".join([resolved["opening"], resolved["for_children"],
                            resolved["what_this_does_not_fix"]]))

# --- 3b. nothing may be called safe --------------------------------------
safe_text = {
    "opening": ("The air is safe today. Your room is perfectly safe. Stay home. "
                "You will breathe easier tonight. Amma will sleep well. "
                "Sam, will have clean air all evening."),
    "for_children": "This keeps them safe at night.",
    "what_this_does_not_fix": "",
}
safe_out, safe_notes = narrator.enforce(dict(safe_text), day, tmap, brief, ppl)
check("no reassurance by the word safe survives",
      "safe" not in " ".join([safe_out["opening"], safe_out["for_children"]]).lower(),
      safe_out["opening"])
check("every safe-bearing sentence was removed",
      not any("safe" in n.lower() and "deleted" not in n for n in safe_notes), str(safe_notes[:2]))
check("no sentence asserts what someone will do",
      "will" not in safe_out["opening"].lower(), safe_out["opening"])
check("a comma before 'will' does not evade the ban",
      "Sam" not in safe_out["opening"] or "will" not in safe_out["opening"].lower(),
      safe_out["opening"])
check("the safe filter is reported", any("safe" in n for n in safe_notes))

# --- 3c. the fact sheet carries what the model would otherwise invent -----
_fs = narrator.fact_sheet(brief, ranked, brief.get("household") or {},
                          ppl, brief.get("profile") or {}, day)
# The fixture stamps "now" for determinism, so assert the behaviour with a real
# date rather than requiring a weekday on a stamp that has none.
_b = dict(brief); _b["stamp"] = "2026-11-21 14:22 IST"
_fs_dated = narrator.fact_sheet(_b, ranked, _b.get("household") or {},
                                ppl, _b.get("profile") or {}, day)
check("a dated stamp yields a weekday the model can read", "WEEKDAY: Saturday" in _fs_dated,
      next((l for l in _fs_dated.splitlines() if "WEEKDAY" in l), "no WEEKDAY line"))
check("fact sheet carries the school verdict",
      "School and outdoor play verdict" in _fs or not (brief.get("school") or {}).get("applies"),
      "school verdict absent while school applies, so the model must guess")
check("fact sheet hour pair comes from the forward window",
      day["clean_hour"] == "now" or ":" in str(day["clean_hour"]),
      f"clean={day['clean_hour']} peak={day['peak_hour']}")

# --- 3b. invented school policy -------------------------------------------
# A model wrote "The child stays home all day" on a day the screen beside it
# printed "Normal outdoor play is fine". Keeping a child home is a household
# decision nobody reported, so the sentence must not survive the filter.
for bad in ("The child stays home all day.",
            "She is kept home from school.",
            "He misses school when the air is like this.",
            "No school today for the little one."):
    inv_text = {"opening": bad + " The air outside is {{OUT}}.",
                "for_children": "", "what_this_does_not_fix": ""}
    inv_out, _ = narrator.enforce(dict(inv_text), day, tmap, brief, ppl)
    low = inv_out["opening"].lower()
    check(f"invented school policy deleted: {bad[:30]!r}",
          not any(k in low for k in ("home all day", "misses school", "no school today", "kept home")),
          inv_out["opening"].strip()[:60])

# --- 4. children paragraph is household-dependent -------------------------
no_kids = narrator.assemble(
    {"opening": "x", "why": [], "one_thing_why": "", "for_children": "your child",
     "what_this_does_not_fix": "y"},
    day, brief, ranked,
    [p for p in ppl if p["name"] != "Child"], "model")
check("no children in the house means no children paragraph", no_kids["for_children"] == "",
      repr(no_kids["for_children"]))

with_kids = narrator.assemble(
    {"opening": "x", "why": [], "one_thing_why": "", "for_children": "your child",
     "what_this_does_not_fix": "y"},
    day, brief, ranked, ppl, "model")
check("children paragraph survives when there are children", with_kids["for_children"] != "")

# --- 5. the assembled plan cannot disagree with the engine ----------------
final = narrator.assemble(clean, day, brief, ranked, ppl, "model")
check("every action in the final plan came from the skeleton",
      all(t["action"] == day["items"][i]["action"] for i, t in enumerate(final["today"])))
check("effects in the final plan are the engine's numbers",
      [t["effect"] for t in final["today"]] == [i["effect"] for i in day["items"]])
check("the one thing is an action the reader is actually given",
      any(t["action"] == final["the_one_thing"]["action"] for t in final["today"]),
      final["the_one_thing"]["action"][:40])
check("the one thing is the biggest cut in today's plan",
      final["the_one_thing"]["effect"] == max(t["effect"] for t in final["today"]))

# The failure this guards against was found by reading a generated plan, not by
# a test: the day list offered a filter at Rs 800 while the ranking's top option
# was something else entirely, so "if you do one thing" named an action the
# reader had never been shown. Assert the two sections cannot disagree.
for label, fixture_args in [("LPG apartment", dict()), ("biomass house", dict(cooking="biomass"))]:
    h, hb, t, ps, am, br, rk, pp = fixture(**fixture_args)
    d = narrator.skeleton(br, rk, pp)
    keys_in_day = {i["key"] for i in d["items"]}
    top_key = rk[0]["key"]
    ok = top_key in keys_in_day or top_key in ("cleaner", "diy_filter") and (
        {"cleaner", "diy_filter"} & keys_in_day)
    check(f"{label}: the top-ranked option appears in the day plan", bool(ok),
          f"top={top_key} day={sorted(keys_in_day)}")
    costs = {i["key"]: i["cost_inr"] for i in d["items"]}
    for k, c in costs.items():
        rec = next(r for r in rk if r["key"] == k)
        check(f"{label}: {k} cost agrees across sections", c == rec["cost_inr"], f"{c} vs {rec['cost_inr']}")
check("costs are the engine's costs",
      all(t["cost_inr"] == day["items"][i]["cost_inr"] for i, t in enumerate(final["today"])))

# --- 6. deterministic fallback is complete --------------------------------
det = narrator.deterministic_plan(brief, ranked, ppl, day)
for key in ("opening", "today", "this_week", "the_one_thing",
            "what_this_does_not_fix", "generated_by"):
    check(f"fallback has {key}", key in det and det[key] not in (None, [], {}))
check("fallback says it is the fallback", det["generated_by"] == "deterministic")
check("fallback still carries a real effect figure",
      any(i["effect"] for i in det["today"]) and det["the_one_thing"]["effect"] > 0,
      str(det["the_one_thing"].get("effect")))

# --- 7. ordering: a filter is never sold to a house that owns one ---------
_, _, _, _, _, b2, r2, p2 = fixture(cleaner="hepa_medium")
d2 = narrator.skeleton(b2, r2, p2)
check("no filter suggestion for a house that already filters",
      all(i["key"] not in ("cleaner", "diy_filter") for i in d2["items"]),
      str([i["key"] for i in d2["items"]]))

# --- 8. a biomass house must be told about the stove ----------------------
_, _, _, _, _, b3, r3, p3 = fixture(cooking="biomass")
d3 = narrator.skeleton(b3, r3, p3)
check("a biomass house gets a stove-related action",
      any(i["key"] in ("cook_time", "clean_fuel", "induction", "keep_cooker_out") for i in d3["items"]),
      str([i["key"] for i in d3["items"]]))

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("all checks passed")
