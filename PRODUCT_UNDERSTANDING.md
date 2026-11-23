# PRODUCT UNDERSTANDING — Saans

Every claim below is tagged. **[VERIFIED]** means I read it in the source or saw it
in a live run. **[INFERRED]** means it follows from verified facts. **[ASSUMED]**
means it is a reasonable guess I have not proven — treated as a hypothesis to test,
never as a design premise.

---

## A. Product identity

### What it is

A single-user, no-account web application that models **one household's daily
inhaled PM2.5 dose** and computes what a specific change would do to it.
**[VERIFIED]** — `saans/engine.py` (800 lines) builds the dose; `saans/advisor.py`
(780 lines) holds 14 interventions that each re-run the day.

Saans (साँस, "breath") runs as one local FastAPI process plus one HTML file. There
is no database, no login, no cloud inference. **[VERIFIED]** — `requirements.txt`
lists only fastapi, uvicorn, pydantic; the model is called over plain HTTP to
`localhost:11434`.

### What it actually does

Given a household (4 people with ages/conditions, a fuel, a stove exhaust, a
commute mode, a location), it:

1. Fetches outdoor PM2.5 for that lat/lon from Open-Meteo/CAMS. **[VERIFIED]**
2. Builds each person's day as blocks (asleep, cooking, commute, school, work).
   **[VERIFIED]** — `engine.day_for()`
3. Resolves each block to a concentration: single-zone mass balance outdoors→indoors,
   plus a kitchen plume term, plus a vehicle/workplace multiplier.
   **[VERIFIED]** — `indoor_concentration()`, `kitchen_concentration()`,
   `vehicle_concentration()`
4. Multiplies by inhalation rate × hours to get **µg inhaled per person per day**.
   **[VERIFIED]**
5. Re-runs that whole day with each of 14 interventions applied, and ranks them by
   dose removed per rupee. **[VERIFIED]**
6. Re-runs it again for **any combination** of interventions, reporting the actual
   combined effect plus the overlap between them. **[VERIFIED]** — `/api/combine`,
   added because 15.3% + 4.0% gives 16.1% together, not 19.3%.
7. Has a local 4B model write three short paragraphs around the computed plan.
   **[VERIFIED]** — `narrator.py`, qwen3:4b, temperature 0.5, JSON format.

### The problem it solves

**[VERIFIED, stated in README]** Existing air-quality apps report a city-level AQI
and stop. "341 — Very Poor" is not actionable for a family. Two people on the same
street inhale different amounts: the grandmother at the stove, the father on a
two-wheeler, the child in a classroom with open windows.

The product's claim is that the actionable unit is **the household's dose**, not the
city's concentration.

### Why choose it over an alternative

This is where I must be honest, because the honest answer is narrower than the
marketing.

**It beats a city AQI app** because it answers a question those apps structurally
cannot: *which of my four people is absorbing the most, and what shifts it.*
That is not a feature difference; it is a different unit of analysis. **[VERIFIED]**

**It beats a generic "air quality" chatbot** because the numbers are computed, not
recalled. The model is forbidden from writing any numeral, and a filter deletes any
sentence carrying one it was not given. **[VERIFIED]** — `enforce()`, and a live
test where `PEAK_HOUR="22:00"` was licensing a fabricated "22 minutes" until fixed.

**It does NOT beat a commercial HEPA purchase decision engine, a doctor, or an
official CPCB/CAQM advisory.** It does not measure your indoor air — it models it.
**[VERIFIED, stated on screen]** Every home input is an assumption and the app says
so.

### Primary value proposition

> **Your dose, not your city's number — and the arithmetic of changing it.**

A household can see four people's daily inhaled micrograms, which one is worst, and
what each realistic change would actually remove. That is defensible, specific, and
not available elsewhere. **[INFERRED from verified arithmetic]**

---

## B. Target audience

I have deliberately not invented demographics. These groups follow from what the
code actually accepts as input.

### Group 1 — The urban Indian household (primary)

**Who.** 3–6 people sharing a dwelling in Delhi-NCR or another Indo-Gangetic city,
November–February. Mixed ages including at least one adult over 60 or a child.
**[VERIFIED]** — this is the default household in `DEFAULTS` and the persona the
README documents.

**Primary needs.** Whether to open windows and when; whether the child can play
outside; whether their stove is hurting them; which single change matters most.

**Technical proficiency.** Low to moderate. **[ASSUMED]** They can use a phone app
but will not read a methodology section. Evidence for the assumption: the interface
inputs are tappable cards and a place search, and the app was designed for "a cheap
Android phone in a cold kitchen".

**Expectations.** An answer in seconds, in imperatives, not a dashboard.

**Frustrations.** Being told the city is "Very Poor" with no instruction; apps that
want an account; apps that show a gauge and no consequence.

**What makes it useful.** Telling them the *hour* and the *person* — "Amma carries
34.8%, and it is 73% from the home".

### Group 2 — The biomass or kerosene household

**Who.** A household burning wood, dung or kerosene, often with no chimney.
**[VERIFIED]** — first-class in the model: `cooking_fuel` enum, kitchen PM2.5 at
180 µg/m³ for biomass vs 35 for PNG, a `clean_fuel` and `kitchen_exhaust`
intervention, and a deliberate rule that the stove must never be silently invisible.

**Needs.** To be told, without shame, that their own stove is the biggest source
they control, and what it would take to change it.

**Technical proficiency.** Lower. **[ASSUMED]** The app's own copy rule is "plain
short sentences, local words (chulha, autowala), no moralising".

**Frustrations.** Being lectured, or being given advice they cannot afford.

**What makes it useful.** An honest rupee cost and a cheaper alternative — the
box-fan filter at ₹800 exists for exactly this.

### Group 3 — The asthmatic, pregnant, or cardiac individual

**Who.** Someone whose own body makes the dose matter more. **[VERIFIED]** —
`conditions: asthma | copd | heart | diabetes`, `pregnant`, and a sensitivity
multiplier that reweights the household share.

**Needs.** Their own number, and which action is *for them* specifically.

**What makes it useful.** The ranking reports `worst_person` and `worst_pct` — "this
one is for Amma". **[VERIFIED]**

### Group 4 — The researcher, judge, or reviewer (secondary)

**Who.** Someone assessing whether the arithmetic is honest. **[VERIFIED]** — the
repo ships 250 automated checks, a frozen contract, and a 56-constant evidence
drawer with source and kind per constant.

**Needs.** To see the sources, the uncertainty bands, and what the model cannot see.

**Frustrations.** A black box. Precisely why the app refuses to hide the band.

### Explicitly NOT the audience

- **Someone wanting a measurement.** This models; it does not measure. No sensor.
- **A hospital or clinician.** The app refuses medical advice by design.
- **A city administrator.** GRAP is read, not authored here.
- **Someone outside South Asia.** **[VERIFIED]** Regional archetypes are labelled as
  archetypes; the app says so rather than pretending to local data.

---

## C. Product story

### What a user should understand in five seconds

**That this is about their family, not their city.** **[VERIFIED]** — Level 1 leads
with an imperative sentence about their household and an exposure ladder
(outdoor → indoors → stove → what one person breathes in a day).

### The primary action

**Choose what they could actually do and see the effect.** **[VERIFIED]** — the
"Build your plan" bench, 14 tappable interventions, live recomputation. Before this
existed the page had no verb at all: it was a sentence, a chart, three numbers and
two rows that revealed more reading.

### What makes the AI capability valuable

Not that it writes. **That it writes only where it cannot do harm.** **[VERIFIED]**

The division is: Python decides every action, time, order, cost, and figure. The
model writes the opening, the paragraph for children, and the honest limit. It is
forbidden numerals, forbidden the word "safe", forbidden claims about future
behaviour, and forbidden inventing school policy. Any sentence that breaks these is
deleted before display, and the deletion is reported on screen.

So the value of the GenAI is **register, not reasoning** — it turns a table of
correct figures into something a tired parent will read. That is worth having, and
it is the only thing it is allowed to do.

### Beginning-to-end experience

Open → one imperative sentence + the chain from street air to a person's dose →
drag the 24-hour surface to find the clean hour → tick two or three actions and
watch the household number fall → read the generated plan with the one thing marked
→ check who carries it → optionally open the evidence drawer.

### What should make them return

**Honest answer: only partly built.** **[VERIFIED]**

- Exists: `done:` markers per action, and picks persisted in localStorage.
- Exists: the app remembers the household, so setup happens once.
- **Does not work:** a "versus yesterday" comparison line, because it needs a
  stored reading from a prior day and has never once rendered in a live session.
  **[VERIFIED by inspection — I could not make it appear]**
- **Missing:** any trigger. No notification, no digest, no reason to open it on a
  particular morning. `DESIGN.md` names this as the rejected-but-real retention
  lever, ruled out only by the single-file, no-service-worker constraint.

This is the weakest part of the product and I will not claim otherwise.

### Narrative

> **Problem** — A city AQI tells a family nothing they can act on, and hides the
> fact that four people in one flat are breathing different air.
>
> **Solution** — Model each person's daily inhaled dose, then compute what each
> realistic change does to it, with the arithmetic and its uncertainty visible.
>
> **Experience** — One imperative sentence, a chain from the street to a person, a
> scrubable day, and a bench where you tick what you could do and watch the number
> move.
>
> **Outcome** — The household knows which one person is worst off, what single
> action removes the most, and what it costs — and knows it was computed, not
> guessed at.

---

## D. User journey

### 1. Landing

Server-rendered page, no spinner-to-content flash. On load it `POST`s `/api/brief`
and paints the verdict, ladder, chart, people, ledger, and picks.
**[VERIFIED]** — first paint at 390px completes with zero console errors.

**Friction:** the generated plan is a second round trip that takes 30–90 s on the
local 4B model. **[VERIFIED]** The page shows a "Reading your numbers" state but the
user must scroll past the bench to reach it.

### 2. Understanding the purpose

The verdict sentence and the ladder do this without instruction. **[VERIFIED]**

**Friction:** the word "dose" is never defined on screen. A first-time user may not
know that 6283 µg/day is "about 3.4 cigarettes' worth" until they read the sub-label.
**[INFERRED]**

### 3. Input / data submission

The household editor: three steps (who lives here → how you cook → how you get
around), persisted to localStorage. Location via `/api/geocode` search.
**[VERIFIED]**

**Friction:** the editor is discoverable only by scrolling to the bottom or noticing
a small text button. **[VERIFIED — it is the last section]**

### 4. AI processing

`POST /api/plan` streams SSE: `facts`, then `token` chunks, then `plan`, then
`done`. **[VERIFIED]**

**Defect found during this inspection:** the client parser reads the stream but only
keeps events carrying a `today` key, so it **discards every `token` chunk** and shows
a static "Reading your numbers" indicator for the entire generation.
**[VERIFIED — `index.html` line ~737 keeps only `obj.today`]**

That wastes the single best signal the app has: a 4B model thinking out loud is
where "this is genuinely generated" becomes visible. It is currently invisible.

### 5. Results

Plan with opening prose, five figures, the children paragraph, actions on a time
rail with the top one marked, the honest limit, and a count of deleted sentences.
**[VERIFIED]**

### 6. Further interaction

Tick interventions on the bench → `/api/combine` → household and per-person deltas,
cost, band, and overlap. Tap a person → their breakdown by place.
Scrub the day → the readout follows. **[VERIFIED]**

### 7. Export / share

**None.** No share, no export, no print stylesheet. **[VERIFIED]** — and the README
still claims a print stylesheet exists, which is now false. A documentation defect
to fix.

### Unnecessary friction, ranked

1. **The plan arrives late and silently.** 30–90 s with no visible progress while
   the stream is full of progress. Fix: render tokens.
2. **The bench and the plan are disconnected.** You build a plan, then read a
   different plan below it. **[VERIFIED]** "Show in the ledger" only scrolls.
3. **The household editor is at the bottom.** Setup is a prerequisite for every
   number to be right, yet it is the last thing on the page.
4. **No definition of the central unit.** "Dose" and "µg/day" carry the whole
   product and are never explained in place.
5. **Zero-state is shallow.** With a fresh profile the page looks the same as a
   configured one; nothing signals "these numbers assume a household you did not
   describe". **[VERIFIED]**

---

## Existing functionality inventory

### Backend — 10 routes, all verified live

| Route | Method | Returns |
|---|---|---|
| `/` | GET | the single-file UI |
| `/api/health` | GET | `{ok, model:{name, available}}` |
| `/api/geocode` | GET | place search (Open-Meteo) |
| `/api/ambient` | GET | raw pollutant field for a lat/lon |
| `/api/brief` | POST | full computed brief + 14 ranked options |
| `/api/simulate` | POST | one intervention, before/after, band, per-person |
| `/api/combine` | POST | several at once + overlap + conflicts |
| `/api/plan` | POST | SSE stream + assembled plan |
| `/api/factors` | GET | 12 groups / 56 constants with source and kind |
| `/api/sources` | GET | source apportionment |

### Frontend — one file, 65,041 bytes, no dependencies

42 ids, 16 CSS custom properties, two themes (`html[data-theme]`), zero external
requests. Structure: masthead → verdict + ladder → 24-hour surface with scrubber →
bench (14 picks + live tally) → plan → people → ledger → evidence → editor.

### GenAI pipeline — verified end to end

```
build()           brief + ranked, pure Python
  ↓
skeleton()        decides the 5 actions, times, order     ← Python owns this
fact_sheet()      every permitted figure as a token       ← the allowlist
generate()        qwen3:4b, stream, JSON, temp 0.5        ← prose only
parse_plan()      JSON or None
tokens()          figure → {{TOKEN}} map
enforce()         delete numerals, tokens, "safe", futures, invented policy
assemble()        pair prose with the engine's figures
```

### Tests — 250 checks, all passing

`test_model.py` 86, `test_narrator.py` 70, `test_security.py` 51, `test_ui.py` 43.

**Known limitation of the suite itself:** it has twice passed a broken build.
171 checks passed while the fact sheet shipped `None` doses; 250 passed while the
plan panel printed a "cleanest hour" that had already passed. Both were found by
looking at the running app. The tests are a floor, not evidence.

---

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `SAANS_OLLAMA` | `http://localhost:11434` | inference endpoint |
| `SAANS_MODEL` | `qwen3:4b` | model tag |
| `SAANS_LLM_TIMEOUT` | `180` | seconds |

No API keys anywhere. **[VERIFIED]** The only outbound calls are Open-Meteo (no key)
and localhost. `language` is plumbed through `generate()` but only `en` exists;
there is no i18n. **[VERIFIED]**

---

## Documented defects found during this inspection

1. **Streamed tokens are discarded by the client** — the AI looks static. **[VERIFIED]**
2. **README claims a print stylesheet; there is none.** **[VERIFIED]**
3. **README test counts are stale** (says 48 security / 41 UI; actual 51 / 43).
   **[VERIFIED]**
4. **Zero-state indistinguishable from configured state.** **[VERIFIED]**
5. **`/api/ambient` and `/api/sources` appear unused by the frontend.**
   **[VERIFIED by grep]** Dead surface area, or intended for clients that do not exist.

---

## What I am still uncertain about

- **Does anyone open this twice?** I have no usage data; this is a local app. Every
  retention claim in this document is reasoning, not measurement. **[ASSUMED]**
- **Is 4B good enough?** Three generations of the same input produced three
  different openings, all factually clean. Whether the prose is *good* is a taste
  judgement I should not make alone.
- **Is the household editor's three-step model actually one-handed on a phone?**
  Not tested with a real thumb. **[ASSUMED]**

---

## The one sentence I would put on the screen

> **Your family breathes different air from your city. Here is what each of you
> takes in today, and what changing one thing would do.**
