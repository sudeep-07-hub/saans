"""
Grounded generation.

The model here is a 4B parameter LLM running on the family's own laptop. It is
good at language and bad at arithmetic, ordering and staying inside constraints
— so the architecture gives it only what it is good at.

Division of labour, strictly:
  Python decides WHAT to do and WHEN: the actions, their order, their cost,
       their measured effect, and the clock times taken from the household's
       own schedule. This is auditable, deterministic, and testable.
  The model decides HOW TO SAY IT: the opening paragraph, the reason attached
       to each action, the note for the children, the honest paragraph about
       what none of this fixes.

That is why the plan a family reads can never contain a number the engine did
not compute, and can never recommend the wrong thing first. It can only be
badly worded, and rewording is a cheap failure.

Four defences, in order:
  1. the fact sheet contains every permitted number and nothing else;
  2. the prompt asks for language, not for decisions;
  3. `enforce()` rejects wrong structure and repairs it;
  4. with no model present, `deterministic_plan()` produces the same plan in
     plainer prose, and the app says which one you are reading.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Iterator

OLLAMA_URL = os.environ.get("SAANS_OLLAMA", "http://localhost:11434")
MODEL = os.environ.get("SAANS_MODEL", "qwen3:4b")
TIMEOUT = float(os.environ.get("SAANS_LLM_TIMEOUT", "180"))

SYSTEM = """You write the spoken part of an air-quality plan for one household in South Asia. A deterministic model has already decided what they should do, in what order, at what time, and why each action works. You write only the surrounding prose.

You cannot change the plan. You cannot add an action, remove one, reorder them, move a time, or restate the mechanism — those are already written, with their citations, by the calculation. You have exactly three jobs: the opening, the note for children, and the honest limit.

NUMBERS: you may not write them. Where a figure belongs, write its token in double curly braces and the screen substitutes the verified value. The tokens are listed in the fact sheet; copy them exactly. A sentence containing a numeral you were not given is deleted before the family sees it, so a plain sentence with no number is always better than a guess.

Rules:
1. Never give medical advice, a diagnosis, a medicine or a dose. You may say someone is at higher risk.
2. Never call anything "safe". In this air nothing is.
3. Never say what someone "will" do. Describe the air and the house, not the family's conduct.
4. Explain the mechanism, not the mood. Good: "the cooking plume never reaches the bedroom". Bad: "it creates a healthy home environment".
5. No moralising. No "we", no "together", no "everyone should". This is one family's Tuesday.
6. Be specific to this household: name the people, their fuel, who is vulnerable, when their air peaks.
7. If they burn wood, dung or kerosene, say plainly that their own stove is the biggest source they control. No shame, no lecture.
8. Plain short sentences, concrete nouns. Local words where clearer (chulha, autowala, geyser). No emoji, no markdown.
9. On children, the fact sheet states the school's own verdict. Restate that verdict only. You may not say a child stays home, misses school or is kept indoors unless the fact sheet says so: the household never told anyone that, and inventing it contradicts the advice printed beside yours.

Reply with JSON only, no fences, no commentary:
 {
  "opening": "2-3 sentences on what today means for this household, naming the people and the air",
  "for_children": "one short paragraph restating the school verdict from the fact sheet if there are children, else an empty string",
  "what_this_does_not_fix": "one honest paragraph about the limits of household action"
}"""


def available() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", headers={"User-Agent": "saans"})
        with urllib.request.urlopen(req, timeout=2) as r:
            data = json.loads(r.read())
        names = [m.get("name", "") for m in data.get("models", [])]
        return any(n.split(":")[0] == MODEL.split(":")[0] for n in names)
    except Exception:
        return False


def clock(h: float) -> str:
    h = float(h) % 24
    m = int(round((h - int(h)) * 60))
    if m == 60:
        h, m = h + 1, 0
    return f"{int(h) % 24:02d}:{m:02d}"


def schedule_lines(segments: list[dict]) -> list[dict]:
    """The household's own day, formatted for the fact sheet."""
    out = []
    for s in segments or []:
        start = float(s.get("start") or 0)
        hours = float(s.get("hours") or 0)
        out.append({
            "label": s.get("label"),
            "start": clock(start),
            "end": clock(start + hours),
            "pm25": s.get("pm25"),
        })
    return out


# ---------------------------------------------------------------------------
# The skeleton: what to do, decided in Python
# ---------------------------------------------------------------------------

def skeleton(brief: dict, ranked: list[dict], people: list[dict],
             schedule: list[dict] | None = None) -> dict:
    """
    Build the day's actions deterministically.

    Each candidate is tied to a moment in the household's real schedule. Only
    the ones that survive the household's actual situation are included — a
    filter is not suggested to a house that already owns one, and a mask is not
    suggested to someone who never leaves.

    The list is returned in the order a family will live it: morning, the
    commute, the meals, the afternoon, the night. Impact is carried on each
    item and the single biggest one is highlighted separately, because a plan
    sorted by impact instead of by time is a ranking, not a plan.
    """
    a = brief["aqi"]
    items: list[dict] = []
    seen: set[str] = set()
    by_key = {r["key"]: r for r in ranked}

    def effort_for(cost: int) -> str:
        if cost <= 0:
            return "free"
        if cost <= 1200:
            return "cheap"
        return "costly"

    def add(key: str, when: str, action: str, order: float) -> None:
        if key in seen or key not in by_key:
            return
        r = by_key[key]
        if r["pct"] <= 0.4 and not r.get("unquantified"):
            return
        seen.add(key)
        items.append({
            "key": key,
            "time": when,
            "order": order,
            "action": action,
            "why": r["why"],
            "effort": effort_for(r["cost_inr"]),
            "effect": r["pct"],
            "cost_inr": r["cost_inr"],
            "who": r.get("worst_person"),
            "who_pct": r.get("worst_pct"),
        })

    def add_best(candidates: list[tuple[str, str]], when: str, order: float) -> None:
        """
        Add whichever of several ways of doing the same thing is worth the most
        per rupee, and use that option's own cost and wording.

        Without this the day plan says "run a filter" at the price of a HEPA
        while the options table recommends the box fan at a seventh of the
        cost. Same action, contradictory prices — the sort of inconsistency
        that makes a reader stop trusting every other number on the page.
        """
        usable = [k for k, _ in candidates if k in by_key and by_key[k]["pct"] > 0.4]
        if not usable:
            return
        key = max(usable, key=lambda k: by_key[k]["value_score"])
        action = dict(candidates)[key]
        add(key, when, action, order)

    morning = clock(brief["best_hour"]["hour"])

    # The household's own cooking hour, taken from the schedule this function was
    # already given, not a guessed 06:30. A family that cooks at 08:00 and 20:00
    # was being told to open the window "from 06:30", a time when nobody is at
    # the stove.
    def cook_clock() -> str:
        # Read the household's own cooking start from whatever the caller had:
        # the schedule if one was passed, otherwise the blocks on the people in
        # the brief. At the real call site `schedule` is never supplied, so
        # relying on it alone silently fell back to a guessed 07:00.
        hours: set[int] = set()
        for x in (schedule or []):
            st = x.get("start")
            if x.get("cooking") and isinstance(st, (int, float)) and 0 <= round(float(st)) <= 23:
                hours.add(int(round(float(st))))
        if not hours:
            for p in ((brief.get("household") or {}).get("people") or people or []):
                for blk in (p.get("blocks") or []):
                    st = blk.get("start")
                    if blk.get("cooking") and isinstance(st, (int, float)) and 0 <= round(float(st)) <= 23:
                        hours.add(int(round(float(st))))
        return clock(sorted(hours)[0]) if hours else clock(7)

    waking = cook_clock()

    # Morning: the first thing they do, and the biggest lever if they cook.
    if brief["kitchen_pm25"] > 90:
        add("cook_time", f"from {waking}, at both meals",
            "Kitchen window wide open, exhaust on, kitchen door shut while the stove is lit.", 1)
    if a["aqi"] >= 201:
        add("window_timing", f"{morning}, ten minutes",
            "Windows open on opposite walls for ten minutes to flush the stale air, then shut "
            "before the evening build-up.", 2)

    # Leaving the house.
    children_under_5 = [p for p in people if p.get("age", 99) < 5]
    if a["aqi"] >= 201 and children_under_5:
        add("mask_commute", "before you step out",
            "Fitted N95 for the adults, fitted child-size respirator for older children. "
            "Infants and toddlers cannot wear one safely: they stay in, or go out in the "
            "cleanest hour only.", 3)
    elif a["aqi"] >= 201:
        add("mask_commute", "before you step out",
            "Fitted N95, nose clip pressed, on before you unlock the gate and off only indoors.", 3)
    if a["aqi"] >= 201:
        add("shift_commute", "for the commute",
            "Metro or bus if a route exists. If it does not, windows shut and the vents on "
            "recirculate, not fresh air.", 4)

    # Daytime and evening.
    if any(p.get("exercises", True) and p.get("age", 30) >= 13 for p in people):
        add("exercise_time", "early afternoon",
            "Walk or train between 13:00 and 16:00, when the mixed layer is deepest.", 5)
    add("keep_cooker_out", "at both meals",
        "Pressure cooker, lid on, one pot: the same meal with fewer burner-minutes and less plume.", 6)
    add("stop_incense", "evening",
        "Incense and mosquito coils outside, never in the room where people sleep.", 7)
    # The day list must contain the option the ranking puts first, or "if you
    # do one thing" points at something the reader was never shown. The list is
    # assembled in time order and capped, so the top option is reserved a slot
    # rather than hoped for.
    if a["aqi"] >= 301:
        top_key = ranked[0]["key"] if ranked else None
        if top_key in ("cleaner", "diy_filter"):
            add_best([
                ("diy_filter", "Filter running in the bedroom with the door shut. A box-fan build "
                               "does this for a fraction of the price of a commercial unit."),
                ("cleaner", "Filter running in the bedroom with the door shut, and keep it running "
                            "while you sleep."),
            ], "tonight, an hour before bed", 8)
        else:
            add(top_key, "this week", "See the options below: this is the largest single change "
                                      "available to your household.", 8) if top_key else None
    if a["aqi"] >= 101:
        add("no_burn", "this evening",
            "Nothing burned in the yard tonight. Leaves, wrappers and sweepings go to the bin.", 9)

    items.sort(key=lambda i: i["order"])
    # The one thing must be an item the family actually sees in the list, and
    # must be the item the ranking puts first, in the ranking's own words.
    top = by_key.get(ranked[0]["key"]) if ranked else None
    # The headline hour pair must be the FORWARD window, not the daily extremum.
    # worst_hour is a max over 0-23 and best_hour a min, so at 14:00 the screen
    # was printing "cleanest hour 13:00" (87 minutes gone) beside "dirtiest hour
    # 23:00". Both now come from the same forward view the verdict uses.
    trough = brief.get("next_trough") or {}
    peak = brief.get("next_peak") or {}
    if trough.get("hour") is not None:
        clean_hour = clock(trough["hour"])
        clean_val = trough.get("pm25")
    else:
        clean_hour = "now"
        clean_val = trough.get("pm25", brief["ambient_pm25"])
    peak_hour = clock(peak["hour"]) if peak.get("hour") is not None else clock(brief["worst_hour"]["hour"])
    if peak.get("pm25") is not None:
        peak_val = peak["pm25"]
    else:
        peak_val = brief["worst_hour"]["pm25"]
    return {
        "items": items[:6],
        "peak_hour": peak_hour,
        "peak_val": peak_val,
        "clean_hour": clean_hour,
        "clean_val": clean_val,
        "top": top,
    }


# ---------------------------------------------------------------------------
# The fact sheet
# ---------------------------------------------------------------------------

def fact_sheet(brief: dict, ranked: list[dict], household: dict, people: list[dict],
               profile: dict, plan: dict, schedule: list[dict] | None = None) -> str:
    """A compact, unambiguous fact block. Everything the model may say, in one place."""
    L: list[str] = []
    a = brief["aqi"]
    L.append("PLACE: " + str(profile.get("city", "your city")))
    # The weekday is spelled out because the model cannot derive it from a
    # timestamp: given "2026-11-21 14:22 IST" a 4B model wrote "This Tuesday" on
    # a Saturday. Naming it converts a guess into a read.
    _stamp = str(brief.get("stamp", ""))
    _wd = ""
    try:
        from datetime import datetime as _dt
        _wd = _dt.strptime(_stamp[:10], "%Y-%m-%d").strftime("%A")
    except (ValueError, TypeError):
        _wd = ""
    L.append("TIME: " + _stamp + (f" ({_wd})" if _wd else ""))
    if _wd:
        L.append("WEEKDAY: " + _wd)
    L.append("")
    L.append("TODAY'S AIR")
    L.append(f"- Outdoor PM2.5: {brief['ambient_pm25']:g} ug/m3 ({brief['ambient_label']})")
    L.append(f"- CPCB AQI: {a['aqi']}, category {a['label']}, dominant pollutant {a['dominant']}")
    L.append(f"- WHO 24-hour guideline is 15 ug/m3; today is {brief['who']['multiple']}x that.")
    L.append(f"- Indoor PM2.5, modelled: {brief['indoor_pm25']:g} ug/m3")
    L.append(f"- Kitchen PM2.5 while cooking: {brief['kitchen_pm25']:g} ug/m3")
    L.append(f"- Dirtiest hour: {plan['peak_hour']} at {plan.get('peak_val', brief['worst_hour']['pm25']):g} ug/m3")
    L.append(f"- Cleanest hour: {plan['clean_hour']} at {plan.get('clean_val', brief['best_hour']['pm25']):g} ug/m3")
    if brief["grap"].get("applies"):
        L.append(f"- {brief['grap']['label']}. {brief['grap']['detail']}")
    # The school verdict is the engine's, and the model is asked to restate it.
    # Without it here the model invented "the child stays home all day" while
    # the screen beside it printed "Normal outdoor play is fine".
    _sch = brief.get("school") or {}
    if _sch.get("applies"):
        L.append(f"- School and outdoor play verdict: {_sch.get('advice', '')} "
                 f"(level: {_sch.get('level', 'unknown')}; source: {_sch.get('source', 'CPCB')})")
    L.append("")
    L.append("THE PEOPLE")
    for p in people:
        cond = ", ".join(p.get("conditions") or []) or "no conditions"
        role = []
        if p.get("pregnant"):
            role.append("pregnant")
        if p.get("cooks"):
            role.append("cooks for the house")
        if not p.get("commutes"):
            role.append("stays home in the day")
        L.append(
            f"- {p['name']}, {p['age']} ({cond}{'; ' + '; '.join(role) if role else ''}). "
            f"Breathes an average {p.get('mean_exposure')} ug/m3 across the day. "
            f"Inhaled dose {p.get('dose_ug')} ug. Sensitivity weight {p.get('sensitivity')}."
        )
    L.append("")
    L.append("THE HOUSE")
    L.append(f"- {household.get('kind')}; fuel {household.get('cooking_fuel')}; "
             f"extraction {household.get('kitchen_exhaust')}; air cleaner {household.get('cleaner')}")
    em = household.get("emissions", {})
    L.append(f"- The stove emits {em.get('cook_pm25_kg_year', 0)} kg of PM2.5 a year "
             f"and {em.get('cook_co2_kg_day', 0)} kg of CO2 a day.")
    L.append(f"- Daily travel emits {em.get('travel_co2_kg_day', 0)} kg of CO2.")
    L.append("")
    L.append("THE PLAN, ALREADY DECIDED. Do not restate these mechanisms; they are already written with their citations.")
    for i, it in enumerate(plan["items"], start=1):
        L.append(f"{i}. at {it['time']}: {it['action']}")
    L.append("")
    if plan.get("top"):
        t = plan["top"]
        L.append(f"THE ONE THING is option 1 overall: \"{t['title']}\".")
        L.append(f"  mechanism (do not restate): {t['why']}")
        L.append("")
    L.append("WINTER SOURCE SHARES IN THIS CITY")
    for k, v in (profile.get("mid") or {}).items():
        L.append(f"- {k}: {v}%")
    if profile.get("local_note"):
        L.append("- " + profile["local_note"])
    L.append("")
    if schedule:
        L.append("THE HOUSEHOLD'S OWN DAY (context only; you may not invent other times)")
        for s in schedule[:12]:
            L.append(f"- {s['start']} to {s['end']}: {s['label']}")
        L.append("")
    L.append("TOKENS - the only way you may express a number. Copy exactly, braces included.")
    L.append("Each token already includes its unit. Write {{OUT}}, never {{OUT}} ug/m3.")
    for k, v in tokens(brief, plan, ranked, people, profile).items():
        L.append(f"  {{{{{k}}}}} = {v}")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------

def _post(payload: dict) -> urllib.request.Request:
    return urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "saans"},
        method="POST",
    )


def generate(facts: str, tone: str = "practical", language: str = "en") -> Iterator[str]:
    """Stream raw text chunks from the local model."""
    prompt = (
        "FACT SHEET\n==========\n" + facts +
        f"\n\nWrite the words for this household's plan now. Tone: {tone}. Language: {language}. "
        "Only the opening, the note for children, and the honest limit. Only tokens from the list."
    )
    payload = {
        "model": MODEL,
        "stream": True,
        "think": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.5, "top_p": 0.9, "num_predict": 900, "num_ctx": 8192},
    }
    with urllib.request.urlopen(_post(payload), timeout=TIMEOUT) as resp:
        for line in resp:
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except Exception:
                continue
            if chunk.get("error"):
                yield f"\n[model error: {chunk['error']}]"
                return
            piece = (chunk.get("message") or {}).get("content") or ""
            if piece:
                yield piece
            if chunk.get("done"):
                return


def parse_plan(raw: str) -> dict | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = raw.split("```")[1] if "```" in raw[3:] else raw
        raw = raw.removeprefix("json").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        obj = json.loads(raw[start:end + 1])
    except Exception:
        return None
    if not isinstance(obj, dict) or not obj.get("opening"):
        return None
    obj.setdefault("for_children", "")
    obj.setdefault("what_this_does_not_fix", "")
    return obj

# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------

def tokens(brief: dict, plan: dict, ranked: list[dict], people: list[dict], profile: dict) -> dict[str, str]:
    """
    The complete list of figures the model may use, each as a token.

    This is the whole safety mechanism in one function: the model can only
    refer to a number by naming a token, the token is resolved here, and an
    unknown token never reaches the reader. Attribution cannot drift, because
    the model never gets to write the number beside the claim — it picks a
    label that Python already filled.
    """
    t: dict[str, str] = {
        "OUT": f"{brief['ambient_pm25']:g} µg/m³",
        "WHOX": f"{brief['who']['multiple']:g}×",
        "IN": f"{brief['indoor_pm25']:g} µg/m³",
        "KITCHEN": f"{brief['kitchen_pm25']:g} µg/m³",
        "PEAK_HOUR": plan["peak_hour"],
        "PEAK": f"{brief['worst_hour']['pm25']:g} µg/m³",
        "CLEAN_HOUR": plan["clean_hour"],
        "CLEAN": f"{brief['best_hour']['pm25']:g} µg/m³",
        "AQI": str(brief["aqi"]["aqi"]),
        "AQI_LABEL": brief["aqi"]["label"],
        "WHO_GUIDE": "15 µg/m³",
    }
    for p in people:
        key = re.sub(r"[^A-Z0-9]", "", str(p.get("name", "")).upper())[:12] or "PERSON"
        t[f"SENS_{key}"] = str(p.get("sensitivity"))
        t[f"CIG_{key}"] = str(p.get("cigarettes"))
        # The per-person dose, so the model can talk about who is carrying the
        # most without reaching for a raw number. Without these tokens it was
        # copying the figure out of the fact sheet and getting the sentence
        # deleted as unverified — correct behaviour, wrong cause.
        if p.get("dose_ug") is not None:
            t[f"DOSE_{key}"] = f"{p['dose_ug']:,} µg/day"
        if p.get("mean_exposure") is not None:
            t[f"EXP_{key}"] = f"{p['mean_exposure']:g} µg/m³"
    if plan.get("top"):
        top = plan["top"]
        t["TOP_PCT"] = f"{top['pct']:g}%"
        t["TOP_COST"] = f"Rs {top['cost_inr']:,}"
        if top.get("worst_person"):
            t["TOP_WHO"] = str(top["worst_person"])
            t["TOP_WHO_PCT"] = f"{top['worst_pct']:g}%"
    for k, v in (profile.get("mid") or {}).items():
        safe = re.sub(r"[^A-Z0-9]", "", k.upper())[:12]
        t[f"SHARE_{safe}"] = f"{v:g}%"
    return t


_TOKEN = re.compile(r"\{\{\s*([A-Z0-9_]+)\s*\}\}")
_DIGIT = re.compile(r"\d")


# Three things reliably produce confident claims about people the model was
# never told about: "you will step out early", "they are safe", and telling a
# named family member what they "will" breathe. Each is deleted, because a plan
# that tells a parent what their child will do has stopped describing and
# started asserting.
# The ban is on the word, not on a phrasing. In air this bad there is no
# correct sentence containing "safe", so trying to enumerate the grammar that
# makes a reassurance ("is safe", "keeps them safe", "the air reads safe") is
# wasted effort that leaves holes. Any sentence with the word goes.
_BANNED = re.compile(
    r"\bsafe(?:ly)?\b"
    r"|\b(will|would|going to)\s+(step|go|leave|head)\s+out\b"
    r"|\b(you|they|he|she|we|it)\s*,?\s+(will|would)\s+\w+"
    r"|\b([A-Z][a-z]{2,12})\s*,?\s+(will|would)\s+\w+"
    # School and staying-home claims. The engine owns the school verdict, and a
    # child being kept home is a household decision nobody reported: a model
    # wrote "the child stays home all day" on a day the screen beside it printed
    # "Normal outdoor play is fine".
    r"|\bstays?\s+(?:at\s+)?home\s+(?:all\s+day|today|from\s+school)\b"
    r"|\bkept\s+(?:at\s+)?home\b"
    r"|\bmiss(?:es|ing)?\s+school\b"
    r"|\bmiss(?:es|ing)?\s+(?:a\s+day\s+of\s+)?(?:class|classes)\b"
    r"|\bno\s+school\s+today\b",
    re.I,
)


def _verified_literals(token_map: dict[str, str]) -> set[str]:
    """
    The numbers that need no mask, because a token already carries them.

    Clock hours are stripped BEFORE harvesting. A token whose value is "22:00"
    was putting bare "22" into this set, which then allowed "Only 22 minutes of
    exposure" through — a fabricated figure licensed by an unrelated clock time.
    Clock times are matched by pattern in `_scrub_patterns`, so they lose
    nothing by being excluded here; a bare hour with no colon never had a claim
    to legitimacy.
    """
    lit: set[str] = set()
    for v in token_map.values():
        # Drop clock times first: "22:00" must not license "22".
        cleaned = re.sub(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", " ", str(v))
        lit |= set(re.findall(r"\d{1,4}(?:\.\d+)?", cleaned))
    # A bare 0-23 is indistinguishable from a clock hour, and clock hours are
    # masked by pattern where they are unambiguous. Leaving them in the allowlist
    # would let any small integer through as "verified".
    lit = {x for x in lit if not (x.isdigit() and 0 <= int(x) <= 23)}
    return lit


# Pollutants, standards, product classes — and units — carry digits in their
# names. They are identifiers, not claims, and treating them as numbers deletes
# correct sentences: "the outdoor PM2.5 is {{OUT}}" died because of the 2.5 in
# the pollutant's name, and "breathes 86.3 ug/m3" died because of the 3 in the
# unit. Units are included here so a plain reading of the number survives; the
# number itself is still checked.
_DOMAIN_TERMS = re.compile(
    r"\b(?:PM\s?2\.5|PM\s?10|PM\s?1|N95|KN95|KF94|FFP[23]|N99|"
    r"NO2|NOx|SO2|CO2|O3|NH3|Pb|CO)\b"
    r"|\b(?:ug|µg|mg|ng)\s*/\s*m(?:3|³)\b"      # the unit, not a claim
    r"|\bm(?:3|³)\b|\bm2\b",                     # cubic/metre squared as written
    re.I,
)


def _scrub_patterns(people: list[dict]) -> list[re.Pattern]:
    """
    The narrow shapes in which digits are unambiguous on their own.

    Clock times and an age attached to a named member of this household, plus
    the pollutant and product names above. These are masked before the stray-
    digit scan, so "22:00", "Amma, 68" and "PM2.5" pass while "3x better" and
    "87% of the dose" do not. Allow-listing bare numbers 0-23 for the sake of
    clock hours would let a fabricated multiplier through, which is exactly
    the failure this layer exists to prevent.
    """
    pats = [
        re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b"),
        _DOMAIN_TERMS,
    ]
    for p in people:
        name = str(p.get("name") or "").strip()
        age = p.get("age")
        if not name or age is None:
            continue
        esc = re.escape(name)
        pats.append(re.compile(rf"\b{esc}\s*,\s*{age}\b(?!\d)", re.I))
        pats.append(re.compile(rf"\b(?:age|aged)\s+{age}\b(?!\d)", re.I))
        pats.append(re.compile(rf"\b{age}\s*(?:-\s*)?(?:year|yr)s?[-\s]?old\b", re.I))
    return pats


_UNIT = r"(?:µg|ug|mg|ng)\s*/\s*m(?:3|³)"
_DUP_UNIT = re.compile(
    rf"{_UNIT}\s*{_UNIT}"          # "217.8 µg/m³ µg/m³" or "74.7 µg/m³ ug/m3"
    r"|(%)[^%\w]{0,3}%"            # "22.5%%"
    r"|(×)[^×\w]{0,3}×",           # "9.9× ×"
    re.I,
)


def _dedupe_units(text: str) -> str:
    """
    Collapse a unit the model repeated after a token already supplied it.

    Tokens carry their own unit ("151.3 µg/m³"), and a model writing
    "{{OUT}} µg/m³" produces "151.3 µg/m³ µg/m³". It also mixes encodings —
    "74.7 µg/m³ ug/m3" — so the pattern matches any two unit variants in a row,
    not an exact duplicate. A doubled unit reads as broken software at exactly
    the moment the reader is deciding whether to trust the number.
    """
    prev = None
    while prev != text:
        prev = text
        text = _DUP_UNIT.sub(
            lambda m: m.group(0).split()[0] if not (m.group(1) or m.group(2)) else (m.group(1) or m.group(2)),
            text,
        )
    return text


def enforce(text: dict, plan: dict, token_map: dict[str, str],
            brief: dict | None = None, people: list[dict] | None = None) -> tuple[dict, list[str]]:
    """
    Resolve tokens, delete anything unverifiable.

    A sentence may only contain digits the engine is holding: a clock time, an
    age attached to a named household member, or a figure already in a token.
    Any other numeral means the model produced a claim nobody computed, and the
    sentence goes with it. A token that is not in the map loses just the token,
    so the rest of the thought survives.

    Sentences that call a person or a room "safe", or that tell someone what
    they "will" do, are also removed. In air this dirty nothing is safe, and a
    plan that asserts behaviour has stopped describing and started predicting.
    """
    notes: list[str] = []
    people = people or []
    verified = _verified_literals(token_map)
    masks = _scrub_patterns(people)
    num = re.compile(r"\d{1,4}(?:\.\d+)?")

    def scrub(s: str) -> str:
        if not isinstance(s, str):
            return ""
        keep = []
        for sentence in re.split(r"(?<=[.!?])\s+", s):
            masked = sentence
            for pat in masks:
                # Keep the whitespace structure so word boundaries in the
                # remaining text are not corrupted by the mask itself.
                masked = pat.sub(lambda m: " " * len(m.group(0)), masked)
            bad = [m.group(0) for m in num.finditer(masked) if m.group(0) not in verified]
            if bad:
                notes.append(f"deleted a sentence with an unverified number ({bad[0]}): {sentence[:58]}")
                continue
            if _BANNED.search(sentence):
                notes.append(f"deleted a sentence that overclaimed: {sentence[:58]}")
                continue
            unknown = [m.group(1) for m in _TOKEN.finditer(sentence)
                       if m.group(1) not in token_map]
            if unknown:
                notes.append(f"removed unknown token(s): {', '.join(unknown[:3])}")
            sentence = _TOKEN.sub(lambda m: token_map.get(m.group(1), ""), sentence)
            keep.append(sentence)
        out = " ".join(keep)
        out = _dedupe_units(out)
        out = re.sub(r"\s+([.,;:])", r"\1", out)
        out = re.sub(r"\s{2,}", " ", out)
        return out.strip()

    for key in ("opening", "for_children", "what_this_does_not_fix"):
        text[key] = scrub(text.get(key, ""))
    # The model no longer writes per-action reasons; the engine's own, which
    # are cited and contain legitimate figures, are used directly.
    text["_notes"] = notes
    return text, notes


def assemble(text: dict, plan: dict, brief: dict, ranked: list[dict],
             people: list[dict], generated_by: str = "model") -> dict:
    """
    Merge the model's words with Python's decisions into the final plan.

    The model supplied sentences with no numerals. Here each sentence is
    paired with the figures it was describing, so the screen can print "the
    dirtiest hour is tonight" followed by "22:00, 179 µg/m³" and the pairing
    is guaranteed correct because Python did the joining.
    """
    items = plan["items"]
    today = []
    for it in items:
        # The reason is the engine's own: cited, and containing figures the
        # engine computed. The model was never asked to restate it.
        today.append({
            "time": it["time"],
            "action": it["action"],
            "why": it["why"],
            "effort": it["effort"],
            "effect": it["effect"],
            "cost_inr": it["cost_inr"],
            "who": it.get("who"),
            "who_pct": it.get("who_pct"),
        })

    # "If you do one thing" must name something the reader was actually given,
    # or they are told to do an action they never saw. First choice is the
    # ranking's own top option; if the day's list has no room for it, the
    # largest cut in the list takes its place.
    top_key = plan["top"]["key"] if plan.get("top") else None
    in_list = [i for i in items if i["key"] == top_key]
    if in_list:
        chosen = max(in_list, key=lambda i: i["effect"])
    elif items:
        chosen = max(items, key=lambda i: i["effect"])
    else:
        chosen = None
    top = next((r for r in ranked if chosen and r["key"] == chosen["key"]), None)
    top_action = chosen["action"] if chosen else (top["title"] if top else "")
    this_week = []
    for r in ranked[:3]:
        if r["pct"] <= 0.4 and not r.get("unquantified"):
            continue
        this_week.append({
            "action": r["title"],
            "why": r["why"],
            "cost_inr": r["cost_inr"],
            "impact": f"{r['pct']}% less of the household daily dose, biggest gain for "
                      f"{r.get('worst_person')} at {r.get('worst_pct')}%",
            "key": r["key"],
        })

    # The figures the opening paragraph is allowed to be about, printed beside
    # it rather than inside it.
    figures = [
        {"label": "outdoor now", "value": f"{brief['ambient_pm25']:g}", "unit": "µg/m³"},
        {"label": "times WHO 24h", "value": f"{brief['who']['multiple']:g}", "unit": "×"},
        {"label": "indoors", "value": f"{brief['indoor_pm25']:g}", "unit": "µg/m³"},
        {"label": "dirtiest hour", "value": plan["peak_hour"], "unit": f"{plan.get('peak_val', brief['worst_hour']['pm25']):g} µg/m³"},
        {"label": "cleanest hour", "value": plan["clean_hour"], "unit": f"{plan.get('clean_val', brief['best_hour']['pm25']):g} µg/m³"},
    ]
    band = top["band_pct"] if top else ([chosen["effect"], chosen["effect"]] if chosen else [])

    # A household with no children must not get a paragraph about children,
    # even if the model wrote one out of habit.
    has_children = any(p.get("age", 99) < 18 for p in people)
    if not has_children:
        text["for_children"] = ""

    return {
        "opening": text.get("opening") or brief["headline"],
        "figures": figures,
        "today": today,
        "this_week": this_week[:3],
        "the_one_thing": {
            "action": top_action,
            "why": top["why"] if top else "",
            "effect": chosen["effect"] if chosen else (top["pct"] if top else 0),
            "band": band,
            "cost_inr": top["cost_inr"] if top else 0,
            "runtime_inr_yr": top["runtime_inr_yr"] if top else 0,
            "who": top.get("worst_person") if top else None,
            "who_pct": top.get("worst_pct") if top else None,
            "source": top["source"] if top else "",
        } if top else {},
        "for_children": text.get("for_children") or "",
        "what_this_does_not_fix": text.get("what_this_does_not_fix") or (
            "None of this cleans the city. It changes what your household breathes and what it emits."
        ),
        "generated_by": generated_by,
        "notes": text.get("_notes", []),
    }


# ---------------------------------------------------------------------------
# Deterministic fallback
# ---------------------------------------------------------------------------

def deterministic_plan(brief: dict, ranked: list[dict], people: list[dict],
                       plan: dict | None = None, schedule: list[dict] | None = None) -> dict:
    """
    The same plan in plainer prose, when no model is running or the model
    fails. Same shape, same honesty, less grace.
    """
    if plan is None:
        plan = skeleton(brief, ranked, people, schedule)
    children = [p for p in people if p["age"] < 18]
    # The children's paragraph must not contradict the school verdict printed
    # beside it. The old text always said "keep their play indoors", which is
    # wrong advice on a moderate day when the engine itself says normal outdoor
    # play is fine.
    _sch = brief.get("school") or {}
    _advice = (_sch.get("advice") or "").strip()
    if children and _advice:
        _lead = ("Children take in more air per kilo than adults, so the same street costs them more. ")
        _for_kids = _lead + f"The school guidance for today is: {_advice[0].lower() + _advice[1:]}"
    elif children:
        _for_kids = ("Children take in more air per kilo than adults, so the same street costs them more. "
                     f"Outdoor air is at {brief['ambient_pm25']:g} ug/m3 today: watch the hour they play in, "
                     "and keep the room they sleep in filtered.")
    else:
        _for_kids = ""
    text = {
        "opening": brief["headline"],
        "for_children": _for_kids,
        "what_this_does_not_fix": (
            "None of this cleans the city. A filter, a mask and a chimney reduce what your household "
            "breathes and what it emits; the street outside stays as it is until the sources change."
        ),
        "_notes": [],
    }
    return assemble(text, plan, brief, ranked, people, generated_by="deterministic")
