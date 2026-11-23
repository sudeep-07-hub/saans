# Saans

**A household air-quality assistant for severe winter smog.**

Saans (साँस — "breath") answers one question well: *given the air on my street
today and the way my family actually lives, what should we change, and what will
that change do?*

```bash
pip install -r requirements.txt
python run.py                      # http://127.0.0.1:8017
```

Optional, for generated prose rather than built-in wording:

```bash
ollama pull qwen3:4b
```

Without it the app still runs and produces the same plan in plainer prose.

```bash
python test_model.py      # 86 checks — exposure arithmetic and the clock
python test_narrator.py   # 73 checks — the language boundary
python test_security.py   # 51 checks — headers, validation, injection
python test_ui.py         # 43 checks — the served file against the design
```

---

## 1. Chosen vertical

**Climate & Environment — air quality and sustainable daily living.**

Persona: a family in Delhi-NCR during the winter smog season. Four people in a
flat — two commuting adults, a seven-year-old, and a grandmother with a heart
condition; a gas stove with no chimney; a two-wheeler commute. The app also
handles biomass households, single rooms, and cities outside the smog belt,
where the same arithmetic produces different advice.

The problem this addresses: existing air-quality apps report a city-level AQI
and stop. An AQI is not actionable. A family cannot do anything with "341 —
Very Poor". They can act on *their own dose*: which hours, which room, which
stove, which commute, and which of their four members is absorbing the most of
it. That gap between a city number and a household decision is the design brief.

---

## 2. Approach and logic

### The core decision

Model the household's **daily inhaled dose**, not the city's concentration, then
compute the arithmetic of each possible change.

```
C_in    = F_inf · C_out + S                      single-zone mass balance
C_clean = C_in · ACH / (ACH + CADR·coverage/V)   air cleaner, capped at field results
dose    = C · IR · hours                         per person, per block of the day
```

Each person gets their own 24-hour timeline — sleep, commute, school, cooking,
evening — and meets a different concentration in each block, breathing at a
different rate (rest 0.45 m³/h, walking 1.8, cycling 2.6). A grandmother at home
all day and a commuter on a two-wheeler must not receive the same number, because
they do not breathe the same air.

Then each intervention is applied as a *patch* to the household and the whole day
is re-run. No percentage is hard-coded: a mask is worth 40% to a two-wheeler
commuter and 8% to someone who works from home, and the model discovers which.

### Why the ranking is unusual

Ordering by household average hides exactly the interventions that protect the
person carrying the most risk. Switching a wood stove moves a four-person
household total by 6%, but cuts the cook's own dose by a third. So the score is
half household, half worst-affected person, and both numbers are shown.

Cost is divided with a square root and floored at Rs 300, so a free habit that
saves 2% cannot outrank a Rs 400 mask that saves 40%, and no zero-cost item is
treated as infinitely valuable.

### The division of labour

| Python decides | The model decides |
|---|---|
| which actions, their order, their clock times | the opening paragraph |
| every percentage, cost and threshold | the note for the children |
| the mechanism and citation for each action | the paragraph about what none of this fixes |
| who benefits most | |

A 4B model on a family's laptop will invent numbers. It is therefore not allowed
to write any. It writes tokens — `{{OUT}}`, `{{PEAK_HOUR}}`, `{{TOP_PCT}}` — and
Python substitutes the verified value, so attribution cannot drift: the model can
never attach a real number to the wrong claim.

Three narrow shapes are exempt and matched by pattern, not by allow-listing
digits: clock times (`22:00`), an age attached to a named member of *this*
household (`Amma, 68`), and pollutant/product names that contain digits
(`PM2.5`, `N95`). Anything else — `3x`, `87%`, `22 minutes` — destroys its
sentence, and the app reports how many it removed.

Three bans are enforced by deletion regardless of phrasing: nothing may be
called **safe**, no sentence may assert what someone *will* do, and no figure may
come from outside the engine.

The app always states whether the wording came from the model or the built-in
fallback. The actions and every figure are identical either way.

### Why the model does not explain the actions

It was tried, and it was worse. Asked to explain each action, the model re-said
the engine's own cited text, sometimes wrongly, and every legitimate figure in
that text (97% for an N95, 40–70 µg/m³ for cooking) then had to be either trusted
or deleted. Deleting a correct, cited sentence to protect the boundary is its own
failure. So the engine's reasons are printed as written, with their citations,
and the model never touches them.

---

## 3. How the solution works

### The screen

The interface is built around one claim: **your exposure is not your city's AQI,
it is where you are and when.** A city-level number cannot separate a child on
the street from a grandmother at the stove. So the page leads with the household
and answers three questions at three depths.

**Level 1 — the verdict.** One screen, no scroll, on a phone in a cold kitchen.
A single imperative sentence — *keep them shut until about 11:00* — rather than a
metric with a label, because a household can act on an instruction and cannot act
on "324, Very Poor". Below it, **the day band**: the outdoor curve, the indoor
line and the cooking peaks on one 24-hour axis, with a marker at now. The gap
between those lines is the product. Then the three numbers (outside / inside /
kitchen), the one person carrying the most of it, and two ways in.

The verdict is derived from `elevated_now` and the **forward window**
(`next_trough`, `next_peak`), never from `worst_hour`/`best_hour` — those are
extrema over the whole day and are usually in the past. At 21:00 `worst_hour`
returns 07:00, and advice built on it is advice about the past.

**Level 2 — the day.** The generated plan in the order a family will live it,
on a vertical time rail, with the single biggest action marked *the one thing*.
The model's prose sits above and below the actions, never interleaved: the
actions are the calculation's, and must not be mistaken for prose.

**Level 3 — the numbers behind this.** The 15 interventions scored by measured
benefit per rupee with each person's dose before and after; per-person inhaled
dose and sensitivity share; source apportionment; the household's own emissions;
and an evidence drawer listing all 56 constants with source and kind, generated
from `constants.py` so code and documentation cannot drift.

The colour of the page is the CPCB AQI category, so the page looks like the air.
Dark mode is a real palette with the accent re-derived per mode rather than
inverted.

### Live data

Open-Meteo / CAMS for the pollutant field and 48-hour forecast, Open-Meteo
geocoding for place search. No API key, no account; the only thing that leaves
the device is a latitude and longitude. With no network the app falls back to a
labelled seasonal climatology and says so on screen.

### Efficiency

`rank()` — 15 interventions × 3 uncertainty scenarios × every person's full day —
takes 39 ms. A single `evaluate()` is 0.4 ms. Responses are cached 15 minutes.
The whole front end is one HTML file with no dependencies and no build step.

---

## 4. Assumptions

Declared openly, because a model that hides its assumptions is worse than one
that states them.

**Modelling**
- **Single-zone mass balance.** Every dwelling is one well-mixed box. A real flat
  has a kitchen plume and a bedroom, so the model adds a declared cooking-spill
  fraction (35%) to the living space and reports kitchen and living
  concentrations separately — but it is not a multi-zone CFD model.
- **Population medians, not your home.** Kitchen PM2.5 values come from Indian
  field studies (HAPIN Tamil Nadu 2020; Pune 2018). Your kitchen may be better or
  much worse. The app shows the measured range and the uncertainty band.
- **Infiltration factor 0.42** with windows closed (literature 0.28–0.45). The
  ambient value behind it is a 1–11 km gridded model, **not a monitor on your
  street**.
- **Chemical composition is not modelled.** PM2.5 from diesel exhaust and from
  road dust are not equally harmful, and this app cannot tell them apart. It says
  so in the interface.
- **Uncertainty is shown, not hidden.** Every effect is re-run at low and high
  settings of the assumptions that dominate it, and the range is printed beside
  the point estimate.
- **Declared estimates are labelled.** The cooking-spill fraction, workplace and
  school indoor factors, and a few emission factors are engineering estimates,
  tagged `estimate` in the drawer rather than dressed up as measurements.

**Scope**
- **Not medical advice.** No diagnosis, medicine, dose, or probability of
  illness. Sensitivity weights flag who to protect first; they are not a risk
  forecast. The cigarette-equivalent figure is the Berkeley Earth mortality rule
  of thumb (22 µg/m³ ≈ one cigarette/day), labelled as an analogy, not an
  equivalence of harm.
- **Not a substitute for a sensor.** A ₹2,000 indoor monitor will disagree with
  this model, sometimes by a factor of two. The app would rather tell you that
  than be quietly wrong.
- **Geometry, not saturation.** Outdoor PM2.5 is the dominant input; at very high
  outdoor levels the infiltration term dominates and an indoor cleaner earns a
  large modelled reduction. This is arguably optimistic about filtration in
  extreme episodes, and the capped 78% reduction limit is the guard against it.
- **Prices are Indian rupees, 2026**, and editable assumptions.
- **GRAP applies to Delhi-NCR only** and is suppressed elsewhere — named NCR
  towns plus a bounding box, tested at the boundary.

---

## 5. Quality, security, testing, accessibility

### Testing — 253 automated checks

Every number below is a real run, not an estimate. The counts moved as the
defects they described were found and closed.

- `test_model.py` (86): the CPCB index against the published worked examples
  (31→51, 45→75, 60→100 µg/m³), GRAP thresholds, hand-computed mass balance,
  HEPA reduction, 24-hour day closure for every person, biomass emissions against
  field factors, geography boundary tests, and the **clock**: that the forward
  window starts at the observed hour rather than midnight, and that a 48-hour
  series is not averaged into a typical day.
- `test_narrator.py` (73): adversarial input to the language boundary — raw
  digits, invented tokens, reassurance, behaviour claims, invented school policy,
  domain names with digits — asserting none survives and that the legitimate
  shapes do.
- `test_security.py` (51): headers actually received, docs disabled, path
  traversal, 14 validation cases, unknown-intervention 404, SSE termination, and
  that the CSP carries `script-src-attr 'none'` so an injected inline handler
  cannot run.
- `test_ui.py` (43): the **served** file against the design — size limit, no
  external origins, no interpolated `innerHTML`, contrast of the light and dark
  token pairs, a text alternative for the chart, labelled inputs, and that the
  forward-window fields are still in the brief.

There is one honest caveat. Passing tests did not prove the product correct: 171
checks passed while a fact sheet was shipping `None` doses, and 253 passed while
the plan panel printed a "cleanest hour" that had already passed. Both were found
by looking at the running app, not by asserting against it. The tests are the
floor, not the evidence.

### Security

- Strict CSP (`default-src 'none'`, no remote origins, no framing, no forms),
  `X-Frame-Options: DENY`, `nosniff`, `no-referrer`, restrictive
  `Permissions-Policy`.
- All input bounded and enum-constrained at the schema: coordinates, ages, string
  lengths, list lengths, numeric ranges. An unbounded `people` list is a cheap
  denial of service, so it is capped at 12.
- API docs and the OpenAPI schema are disabled in the served app.
- No third-party script, no build step, no dependency tree to audit.
- **XSS verified, not assumed.** A household name is hostile input from a shared
  device. The client renders every API string with `textContent`; a payload of
  `<img src=x onerror=...>` was pushed through the real path and produced zero
  `img` elements and no execution.
- Nothing about the household leaves the device except a latitude and longitude.

### Accessibility

- All text meets WCAG AA. The palette was contrast-measured, and three colours
  failed on the first pass (`muted` 4.27:1, `poor` 4.12:1, `moderate` 2.94:1);
  they were recomputed to 4.74, 4.61 and 4.78:1.
- Every control is keyboard-reachable with a visible focus ring; skip link to the
  main content; `Esc` closes the search list; combobox ARIA on the search.
- The two charts are decorative geometry — the hour series is repeated as a
  screen-reader sentence, and each person's bar has a text equivalent.
- `aria-live` on the headline and the options so a change is announced;
  `role="alert"` on errors; `prefers-reduced-motion`, `prefers-contrast: more` and
  `prefers-reduced-transparency` all honoured.
- Responsive from 320px to 1440px with no horizontal overflow.

### Code quality

Every constant lives in one file with its source and a `measured` / `standard` /
`estimate` tag — the drawer in the UI is generated from it, so code and
documentation cannot drift. The exposure model is stdlib-only and free of side
effects, so it is testable without a server. The front end is a single
dependency-free file.

---

## 6. What it refuses to do

- **No medical advice.** No diagnosis, no medicine, no dose, no "safe".
- **No fake precision.** Every effect carries a range; the coarseness of the
  input is stated; what the model cannot see is listed in the interface.
- **No recommendation that moves a household backwards.** Interventions can only
  ascend their own ladder: a box-fan filter is never offered to a house that
  already runs a HEPA, and a gas stove is never "switched" to wood.
- **No Delhi regulation outside Delhi.** GRAP is suppressed outside NCR.
- **No shaming.** A household burning wood is told plainly, with the arithmetic,
  that its stove is the biggest source it controls — and then left alone.

---

## 7. Layout

```
saans/
  constants.py   every factor, with source and kind (measured/standard/estimate)
  aqi.py         CPCB AQI breakpoints, GRAP stages, NCR test, WHO bands
  engine.py      mass balance, per-person day model, dose, emissions
  advisor.py     15 interventions, patched and re-run, then ranked
  sources.py     source apportionment profiles
  data.py        Open-Meteo / CAMS, geocoding, labelled offline fallback
  narrator.py    fact sheet, token boundary, enforcement, fallback prose
  server.py      FastAPI: /api/brief, /api/simulate, /api/combine, /api/plan,
                 /api/factors, /api/sources
  static/
    index.html   the interface — one file, no build step, no framework
test_model.py    86 checks: arithmetic, the clock, and the forward window
test_narrator.py 73 checks: adversarial tests of the generative boundary
test_security.py 51 checks: headers, validation, traversal, injection
run.py           launcher
```

---

## 8. Evidence

- WHO Global Air Quality Guidelines 2021 — PM2.5 guideline and interim targets
- CPCB National Air Quality Index — breakpoints, sub-index formula, health categories
- CAQM Graded Response Action Plan — Delhi-NCR stage thresholds and measures
- TERI/ARAI 2018 — Delhi-NCR source apportionment (Ministry of Heavy Industries)
- HAPIN pilot, Tamil Nadu 2020; Pune 2018 household study — kitchen PM2.5 by fuel
- EST 2022, *Environ. Sci. Technol.* — Indian cookstove RCT, chimney effectiveness
- PLoS ONE 2024; Clapp 2021, *JAMA Intern. Med.* — fitted filtration efficiency
- Goel et al. 2015, *Atmos. Environ.* — Delhi transport microenvironments
- US EPA Exposure Factors Handbook Ch.6 — inhalation rates
- US EPA *Residential Air Cleaners* 3rd ed.; NCCEH field review — PAC effectiveness
- CEA CO₂ Baseline Database v21.0 — Indian grid emission factor
- Poore & Nemecek 2018, *Science* — food emission factors

Full list with values, units and provenance: `GET /api/factors`, or the "Where
the numbers come from" drawer in the interface.

## License

MIT — see `LICENSE`.
