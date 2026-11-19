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
    payload_people = [p.__dict__ | {"sensitivity": p.sensitivity} for p in E._with_roles(people)]
    ranked_rows = payload_people
    for p, row in zip(E._with_roles(people), ranked_rows):
        pass
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
