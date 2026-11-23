"""
Saans - the server.

Three responsibilities, kept apart on purpose:
  /api/brief     deterministic. Air quality in, household numbers out.
  /api/simulate  deterministic. One change, its delta, its uncertainty band.
  /api/plan      generative. A verified fact sheet goes to a local model,
                 prose comes back, and the numbers in it are checked again.

If the model is missing the app still works: /api/plan falls back to the
deterministic plan and says so in the payload.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import advisor, aqi, data, engine as E, narrator, sources
from . import constants as C

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Saans", version="1.0", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """
    Baseline hardening.

    The app is served from localhost and never loads third-party assets, so the
    content policy can be genuinely strict: no remote script, no remote style,
    no framing, no inline event handlers. The one inline block is the page's own
    <style> and <script>, which is why 'unsafe-inline' appears for those two
    directives only — there is no third-party origin to protect against and the
    page's own code is the app.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; "
        # The app is one inline <script>, so 'unsafe-inline' is needed for the
        # block itself. script-src-attr 'none' then removes the specific hole
        # that matters: inline event handlers such as onerror= or onclick=,
        # which is what an injected string would use. Without it, an
        # innerHTML sink anywhere in the page is a live XSS.
        "script-src 'self' 'unsafe-inline'; "
        "script-src-attr 'none'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "frame-ancestors 'none'"
    )
    return response


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class Location(BaseModel):
    # Bounds are validation, not decoration: an unbounded lat or a 10,000
    # character label would reach an upstream API and a regex engine.
    lat: float = Field(28.6139, ge=-90, le=90)
    lon: float = Field(77.2090, ge=-180, le=180)
    label: str = Field("Delhi, India", max_length=120)
    city: str = Field("Delhi", max_length=80)
    country_code: str = Field("IN", max_length=2)
    tz: str = Field("auto", max_length=64)


class PersonIn(BaseModel):
    name: str = Field("You", max_length=40)
    age: int = Field(34, ge=0, le=120)
    pregnant: bool = False
    conditions: list[Literal["asthma", "copd", "heart", "diabetes"]] = Field(
        default_factory=list, max_length=4)
    smoker: bool = False
    commutes: bool = True
    cooks: bool = False
    exercises: bool = True


class HomeIn(BaseModel):
    kind: Literal["apartment", "independent", "single_room"] = "apartment"
    cooking_fuel: Literal["biomass", "kerosene", "lpg", "png", "electric"] = "lpg"
    kitchen_exhaust: Literal["chimney", "fan", "window", "none"] = "none"
    cleaner: Literal["none", "box_fan", "hepa_small", "hepa_medium"] = "none"
    mixer: Literal["none", "biomass", "kerosene", "lpg", "png", "electric"] = "none"
    windows_day: Literal["closed", "mixed", "open"] = "mixed"
    windows_night: Literal["closed", "mixed", "open"] = "closed"
    occupants: int = Field(4, ge=1, le=30)


class HabitsIn(BaseModel):
    incense_per_day: int = Field(0, ge=0, le=24)
    mosquito_coil: bool = False
    dry_sweeping: bool = True
    waste_burning_kg_week: float = Field(0.0, ge=0, le=200)
    outdoor_exercise: bool = True
    exercise_hour: int = Field(7, ge=0, le=23)
    cook_hours: list[float] = Field(default_factory=lambda: [8.0, 20.0], max_length=6)
    cook_minutes: int = Field(90, ge=0, le=480)


class TransportIn(BaseModel):
    mode: Literal["car_ac", "car_open", "two_wheeler", "auto", "bus", "metro",
                  "walk", "cycle", "wfh"] = "two_wheeler"
    km_per_day: float = Field(18.0, ge=0, le=500)
    mask: Literal["none", "cloth", "surgical", "kn95", "n95"] = "none"


class Household(BaseModel):
    location: Location = Field(default_factory=Location)
    home: HomeIn = Field(default_factory=HomeIn)
    habits: HabitsIn = Field(default_factory=HabitsIn)
    transport: TransportIn = Field(default_factory=TransportIn)
    # Bounded: every extra person is another timeline evaluated three times per
    # intervention, so an unbounded list is a cheap denial of service.
    people: list[PersonIn] = Field(
        default_factory=lambda: [
            PersonIn(name="You", age=34, commutes=True),
            PersonIn(name="Partner", age=33, commutes=True),
            PersonIn(name="Child", age=7, commutes=False),
            PersonIn(name="Amma", age=68, commutes=False, exercises=False, conditions=["heart"]),
        ],
        min_length=1, max_length=12)
    office: bool = True
    tone: Literal["practical", "gentle", "direct"] = "practical"


class SimRequest(BaseModel):
    """Kept in the wrapped shape for API compatibility with /api/simulate."""
    household: Household
    key: str = Field(..., max_length=40)


class CombineRequest(Household):
    """
    Several interventions at once.

    Inherits the household fields directly, so the payload is FLAT and identical
    to /api/brief, /api/skeleton and /api/plan. They used to be nested under
    `household` here while the other three took them at the top level, so a client
    sending one convention silently got the default household from the other set —
    which is how a configured biomass flat was shown gas-stove numbers.

    Also bounded: each key re-evaluates a whole day per person per scenario, so an
    unbounded list is a cheap denial of service. 14 is the catalogue size.
    """
    keys: list[str] = Field(default_factory=list, max_length=15)


def to_models(h: Household):
    home = E.Home(**h.home.model_dump())
    habits = E.Habits(**h.habits.model_dump())
    tr = E.Transport(**h.transport.model_dump())
    people = [E.Person(**p.model_dump()) for p in h.people] or [E.Person()]
    return home, habits, tr, people


def _hourly(amb) -> list[dict]:
    """
    The 24-hour series the chart draws, one value per hour.

    Delegates to the engine rather than reimplementing it. This was a second
    copy, and it kept the bug I had already fixed in engine._hour_series:
    averaging the 48-hour response into a typical day, which put the chart's
    evening peak at 150 while the legend beside it — which reads next_peak —
    said 211 at the same hour. The picture and the number disagreed about
    tonight. One implementation means they cannot drift again.
    """
    return [{"hour": r["hour"], "pm25": round(r["pm25"], 1)} for r in E._hour_series(amb)]


def build(h: Household) -> dict:
    home, habits, tr, people = to_models(h)
    loc = h.location
    amb = data.fetch_ambient(loc.lat, loc.lon, loc.label, loc.tz)
    profile = sources.profile_for(loc.country_code, loc.lat, loc.lon, loc.label)
    profile["city"] = loc.city or loc.label
    indoor = E.indoor_concentration(amb.pm25, home, habits)
    profile = sources.with_local_sources(profile, indoor, amb.pm25)
    burn = E.local_burn_increment(habits.waste_burning_kg_week)
    if burn > 0:
        profile["local_note"] = (
            f"Your own open burning adds an estimated {burn} ug/m3 to the air around your home, "
            "on top of the city background."
        )

    brief = advisor.daily_brief(
        amb, home, habits, tr, people, profile, h.office,
        aqi.is_ncr(loc.lat, loc.lon, f"{loc.label} {loc.city}", loc.country_code),
    )
    brief["stamp"] = data.stamp()
    brief["school"] = advisor.school_guidance(brief["aqi"]["aqi"], people)
    ranked = advisor.rank(home, habits, tr, people, amb, h.office)

    # The household-level timeline is the commuter's, relabelled, so the drawn
    # day matches the person whose exposure most people want to see first.
    lead = next((p for p in brief["household"]["people"] if p["name"] == people[0].name),
                brief["household"]["people"][0])
    emissions = E.household_emissions(home, habits, tr, len(people))
    brief["emissions"] = emissions
    brief["local_burn_increment"] = burn
    brief["fuel_switch"] = (
        E.fuel_switch_saving(home) if home.cooking_fuel in ("biomass", "kerosene") else None
    )

    return {
        "brief": brief,
        "ranked": ranked,
        "emissions": emissions,
        "home": home.__dict__,
        "habits": {**habits.__dict__, "cook_hours": list(habits.cook_hours)},
        "transport": tr.__dict__,
        # Merge the computed exposure row into each person, so the fact sheet and
        # the narrator get the dose the engine actually calculated. Before this,
        # the model was handed "None ug" for every member's dose — the numbers it
        # would most want to write about were missing from its own fact sheet.
        "people": [
            row | {"sensitivity": row.get("sensitivity") or person.sensitivity,
                   "conditions": list(person.conditions),
                   "pregnant": person.pregnant,
                   "cooks": person.cooks,
                   "commutes": person.commutes}
            for person, row in zip(E._with_roles(people), brief["household"]["people"])
        ],
        "segments": lead["blocks"],
        "hourly": _hourly(amb),
        "model": {"available": narrator.available(), "name": narrator.MODEL},
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "model": {"name": narrator.MODEL, "available": narrator.available()}}


@app.get("/api/geocode")
def geocode(q: str):
    if len(q.strip()) < 2:
        return {"results": []}
    return {"results": data.geocode(q.strip())}


@app.get("/api/ambient")
def ambient(lat: float, lon: float, label: str = "", tz: str = "auto", cc: str = ""):
    amb = data.fetch_ambient(lat, lon, label, tz)
    a = aqi.compute(pm25=amb.pm25, pm10=amb.pm10, no2=amb.no2)
    return {
        "pm25": amb.pm25, "pm10": amb.pm10, "no2": amb.no2,
        "temp_c": amb.temp_c, "wind_kmh": amb.wind_kmh, "rh": amb.rh,
        "source": amb.source, "label": amb.label,
        "aqi": a,
        "grap": aqi.grap_stage(a["aqi"], aqi.is_ncr(lat, lon, label, cc)),
        "who": aqi.who_band(amb.pm25),
        "worst_hour": E.worst_hour(amb), "best_hour": E.cleanest_hour(amb),
        "hourly": _hourly(amb),
        "profile": sources.profile_for(cc, lat, lon, label),
        "stamp": data.stamp(),
    }


@app.post("/api/brief")
def brief(h: Household):
    try:
        return build(h)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.post("/api/simulate")
def simulate(req: SimRequest):
    home, habits, tr, people = to_models(req.household)
    loc = req.household.location
    amb = data.fetch_ambient(loc.lat, loc.lon, loc.label, loc.tz)
    if req.key not in advisor.CATALOGUE:
        raise HTTPException(status_code=404, detail="unknown intervention")
    return advisor.simulate(req.key, home, habits, tr, people, amb, req.household.office)


@app.post("/api/combine")
def combine(req: CombineRequest):
    """
    Several interventions at once, re-run from scratch.

    The app's centrepiece lets a household tick four or five actions and see
    where they land. Effects do not add, so this cannot be done by summing the
    per-intervention numbers client-side; the whole day is re-evaluated with
    every patch applied.
    """
    home, habits, tr, people = to_models(req)
    loc = req.location
    amb = data.fetch_ambient(loc.lat, loc.lon, loc.label, loc.tz)
    unknown = [k for k in req.keys if k not in advisor.CATALOGUE]
    if unknown:
        # Same status as /api/simulate, so a client handles both the same way.
        raise HTTPException(status_code=404, detail=f"unknown intervention: {', '.join(unknown)}")
    return advisor.combine(req.keys, home, habits, tr, people, amb, req.office)


# --- generation -------------------------------------------------------------

NUM = re.compile(r"\b(\d{1,4}(?:\.\d+)?)\s*(ug/m3|µg/m³|%|x|hours?|hrs?|minutes?|cigarettes?)\b", re.I)


def allowed_numbers(payload: dict) -> set[str]:
    brief, ranked = payload["brief"], payload["ranked"]
    vals = {
        round(brief["ambient_pm25"]), round(brief["indoor_pm25"]), round(brief["kitchen_pm25"]),
        brief["aqi"]["aqi"], round(brief["who"]["multiple"] or 0),
        round(brief["worst_hour"]["pm25"]), round(brief["best_hour"]["pm25"]),
    }
    for r in ranked:
        vals |= {round(abs(r["pct"])), round(r["cost_inr"]), round(abs(r["runtime_inr_yr"]))}
        vals |= {round(v) for v in r["band_pct"]}
    for p in brief["household"]["people"]:
        vals |= {round(p["dose_ug"]), round(p["mean_exposure"])}
    out = {str(v) for v in vals if v >= 0}
    out |= {str(v) for v in range(0, 32)}
    out |= {"15", "5", "22", "35", "50", "75", "100"}
    return out


def _schedule_lines(segments: list[dict]) -> list[dict]:
    """The household's own day, formatted for the fact sheet."""
    return narrator.schedule_lines(segments)


@app.post("/api/skeleton")
def skeleton_endpoint(h: Household):
    """
    The plan's actions, times and effects — without the model's prose.

    /api/plan takes 30-90 seconds because a 4B model writes three paragraphs.
    The five actions and their effects are decided by `narrator.skeleton()`, pure
    Python over the same brief, and take milliseconds. The UI uses this to keep
    the numbers honest when a household edits itself, instead of re-waiting a
    minute and a half for wording that is not load-bearing.

    It calls the same function the generation path calls, so the two cannot drift.
    """
    payload = build(h)
    brief_, ranked = payload["brief"], payload["ranked"]
    schedule = narrator.schedule_lines(payload["segments"])
    day = narrator.skeleton(brief_, ranked, payload["people"], schedule)
    return {
        "ok": True,
        "today": day["items"],
        "peak_hour": day["peak_hour"],
        "peak_val": day.get("peak_val"),
        "clean_hour": day["clean_hour"],
        "clean_val": day.get("clean_val"),
        "the_one_thing": {
            "action": (day["top"] or {}).get("title", ""),
            "why": (day["top"] or {}).get("why", ""),
        } if day.get("top") else None,
    }


@app.post("/api/plan")
def plan(h: Household):
    """Server-sent events: the words streaming in, then the finished plan."""
    payload = build(h)
    brief_, ranked = payload["brief"], payload["ranked"]
    schedule = narrator.schedule_lines(payload["segments"])
    day = narrator.skeleton(brief_, ranked, payload["people"], schedule)
    facts = narrator.fact_sheet(
        brief_, ranked,
        {"kind": h.home.kind, "cooking_fuel": h.home.cooking_fuel,
         "kitchen_exhaust": h.home.kitchen_exhaust, "cleaner": h.home.cleaner,
         "emissions": payload["emissions"]},
        payload["people"], brief_["profile"], day, schedule,
    )

    def stream():
        yield f"event: facts\ndata: {json.dumps({'facts': facts, 'chars': len(facts), 'actions': len(day['items'])})}\n\n"
        if not narrator.available():
            det = narrator.deterministic_plan(brief_, ranked, payload["people"], day, schedule)
            det["fallback_reason"] = "no local model is running, so the built-in wording is shown"
            yield f"event: plan\ndata: {json.dumps(det)}\n\n"
            yield "event: done\ndata: {}\n\n"
            return
        buf: list[str] = []
        try:
            for chunk in narrator.generate(facts, tone=h.tone):
                buf.append(chunk)
                yield f"event: token\ndata: {json.dumps({'t': chunk})}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
        text = narrator.parse_plan("".join(buf))
        if text is None:
            out = narrator.deterministic_plan(brief_, ranked, payload["people"], day, schedule)
            out["fallback_reason"] = "the model's answer did not parse; the built-in wording is shown"
        else:
            tmap = narrator.tokens(brief_, day, ranked, payload["people"], brief_["profile"])
            text, _notes = narrator.enforce(text, day, tmap, brief_, payload["people"])
            out = narrator.assemble(text, day, brief_, ranked, payload["people"], "model")
        yield f"event: plan\ndata: {json.dumps(out)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/factors")
def factors():
    """Everything the model believes, with its source, for the evidence drawer."""
    groups = {
        "health reference levels": {
            "WHO 24-hour PM2.5 guideline (ug/m3)": C.WHO_PM25_24H.as_dict(),
            "WHO annual PM2.5 guideline (ug/m3)": C.WHO_PM25_ANNUAL.as_dict(),
            "WHO interim target 1, 24-hour (ug/m3)": C.WHO_PM25_IT1_24H.as_dict(),
            "cigarette equivalence (ug/m3 per cigarette/day)": C.CIGARETTE_PM25.as_dict(),
        },
        "inhalation rate (m3/h)": {k: v.as_dict() for k, v in C.IR.items()},
        "outdoor-to-indoor (fraction)": {k: v.as_dict() for k, v in C.INFILTRATION.items()},
        "air changes per hour": {k: v.as_dict() for k, v in C.ACH.items()},
        "kitchen PM2.5 by fuel (ug/m3)": {k: v.as_dict() for k, v in C.KITCHEN_PM25.items()},
        "exhaust modifier (x)": {k: v.as_dict() for k, v in C.EXHAUST_MODIFIER.items()},
        "indoor sources (ug/m3 while active)": {k: v.as_dict() for k, v in C.INDOOR_SOURCE_PM25.items()},
        "air cleaner CADR (m3/h)": {k: v.as_dict() for k, v in C.CLEANER_CADR.items()},
        "mask fitted filtration": {k: v.as_dict() for k, v in C.MASK_FFE.items()},
        "transport microenvironment (x ambient)": {k: v.as_dict() for k, v in C.MODE_FACTOR.items()},
        "cooking emission factor (g PM2.5/kg fuel)": {k: v.as_dict() for k, v in C.COOK_PM25_EF.items()},
        "India grid": {"CO2 per kWh": C.GRID_EF.as_dict()},
    }
    return {
        "groups": groups,
        "method": [
            "Single zone mass balance: C_in = F_inf x C_out + S, then reduced by ACH/(ACH + CADR x coverage / V), capped at the 78% best case seen in field studies.",
            "Dose = concentration x inhalation rate x hours, summed over each person's own 24-hour timeline of microenvironments.",
            "Uncertainty is a re-run at low and high settings of the assumptions that dominate the answer (inhalation rate, infiltration, measured kitchen concentration, cleaner effectiveness), and the range is shown next to every point estimate.",
            "Cigarette equivalents use the Berkeley Earth rule of thumb of one cigarette a day per 22 ug/m3 PM2.5. It compares mortality risk, not chemistry.",
            "Nothing here is a medical prediction. It is arithmetic on published exposure factors.",
        ],
        "limits": [
            "Ambient values come from a gridded model at 1-11 km resolution, not a monitor on your street.",
            "Indoor values are modelled from a handful of inputs. A real sensor will disagree, sometimes by a factor of two.",
            "Kitchen concentrations are population medians; your kitchen may be better or much worse.",
            "Chemical composition is not modelled. PM2.5 from a diesel exhaust and from dust are not equally harmful, and this app cannot tell them apart.",
            "The cooking-spill fraction and workplace/school indoor factors are declared engineering estimates, not measurements.",
        ],
    }


@app.get("/api/sources")
def source_profile(lat: float = 28.6139, lon: float = 77.209, cc: str = "IN", label: str = ""):
    return sources.profile_for(cc, lat, lon, label)
