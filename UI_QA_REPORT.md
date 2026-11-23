# Saans — Independent QA, Accessibility & Design Review

**Reviewer:** Agent 5 — QA / Accessibility / Design Review (read-only on application code)
**Build reviewed:** `saans/static/index.html` 92,111 bytes; `saans/server.py` (478 lines) — served at `http://127.0.0.1:8017`
**Method:** live browser (CDP), real Tab/Arrow/Enter keypresses, real pointer clicks, computed-style sampling, direct API probes.
**Date of run:** 2026-11-23, ~22:18–22:40 IST

## Verdict up front

**Ship after fixing the six MAJOR items in §7.** The core product is sound and the arithmetic is honest: the household genuinely reaches the server (the headline bug is fixed), the verdict sentence never contradicts itself, the exposure ladder is real, the scrubber works, the evidence drawer still carries all 56 constants, and done-markers are correctly date-scoped. Nothing is broken in a way that makes the numbers wrong.

What is wrong is **a cluster of honesty and labelling defects in the bench and the people cards** — the two places where a user interprets their own numbers. Three of them are the kind that make a reader stop trusting the rest of the page: a share labelled as dose-share that is actually sensitivity-weighted risk share (§F-J1), a "dropped the rest" message while both options stay ticked (§F-H2), and a percentage that changes depending on the order you clicked the checkboxes (§F-H3). None is a maths error. All are reporting errors on top of correct maths, and all are cheap to fix.

**No BLOCKERs.** The brief's named catastrophic regression (config silently replaced by the default family) is **confirmed fixed** at both the API and UI layers.

---

## 1. Functional

### F1a — App starts, GET / is 200, zero console errors on load — **PASS**
- `GET /` → `200`. `performance.getEntriesByType('navigation')[0].responseStatus` → `200`. DOMContentLoaded 27 ms, load 39 ms.
- Installed a console/`window.onerror`/`unhandledrejection` hook via `Page.addScriptToEvaluateOnNewDocument` *before* navigation, then reloaded and waited 6 s: `window.__consoleLog` → `[]` (empty).
- Resource failures: `0`. Only 3 resource entries total (the page is genuinely one file plus two API calls).

### F1b — All 10 API routes answer — **PASS**, with one documentation mismatch (see F-R3)
| Route | Probe | Status |
|---|---|---|
| `GET /` | `curl` | 200 |
| `GET /api/health` | `curl` | 200 → `{"ok":true,"model":{"name":"qwen3:4b","available":true}}` |
| `GET /api/geocode?q=Delhi` | `curl` | 200, 6 results, first `Delhi, NCT of Delhi, India` @ 28.65195,77.23149 |
| `GET /api/ambient?lat=28.6139&lon=77.209` | `curl` | 200, pm25 71.5, AQI 137 Moderate |
| `POST /api/brief` | `@/tmp/sita.json` | 200 |
| `POST /api/simulate` | `{household, key:"clean_fuel"}` | 200, band `[27.3, 34.3]` |
| `POST /api/combine` | flat body + `keys` | 200 |
| `POST /api/skeleton` | flat body | 200, 45 ms |
| `POST /api/plan` | flat body | 200, SSE stream (`event: facts` first) |
| `GET /api/factors` | `curl` | 200, 12 groups / 56 constants |
| `GET /api/sources` | `curl` | 200 |

Note: `/api/ambient` with no query params returns 422 (`lat`/`lon` required) — correct behaviour, not a defect. `/api/simulate` is the one route still on the wrapped `{household:{...}}` shape (deliberate, documented in `server.py:150`); a flat body returns 422. Since the UI never calls it, this is a latent inconsistency, not a live bug — logged as F-R4 (NIT).

### F1c — Household reaches the server (Sita / Baba / biomass) — **PASS** (the headline bug stayed fixed)
API layer:
```
POST /api/brief  (@/tmp/sita.json, people Sita 34 + Baba 72, cooking_fuel biomass, single_room)
→ HTTP 200
→ people: ['Sita', 'Baba']
→ ambient 71.5 · indoor 49.8 · kitchen 197.9
→ doses: Sita 1932, Baba 920
```
Kitchen is **197.9**, not ~57 — the biomass kitchen constant is being applied.

UI layer, end-to-end (set `localStorage['saans.household.v1']` to the same household, reload):
```
people:  Sita | age 34 | 1932 µg/day | share 51.7%
         Baba | age 72 |  920 µg/day | share 48.3%
ladder:  OUTDOOR 71.5 → INDOORS 49.8 → AT THE STOVE 197.9 → BREATHED TODAY 1932
verdict: "Sita carries the most"  (correct: 1932 > 920)
editor:  shows Sita / Baba, not You/Partner/Child/Amma
```
"No You/Partner/Child/Amma" requirement satisfied. Frontend sends a flat body at `index.html:1614` (`post("/api/brief", h)`), matching `def brief(h: Household)`.

### F1d — Verdict is one coherent sentence — **PASS**
Live: *"Open up now, while it is at its best. It rises again around 00:00."* — two clauses, same tense, same direction; no "open up … it climbs" contradiction.

I exercised `verdictText()` directly across nine synthetic payloads to hunt for the contradiction and for "calm" mislabel:

| Case | Output |
|---|---|
| AQI 420, elevated, trough 4 h out | "Keep them shut. It is near today's worst, and the next clear hour is 14:00." |
| AQI 420, elevated, trough soon | "Keep them shut. It is near today's worst, and the next clear hour is 02:00." |
| AQI 420, elevated, no trough | "Keep them shut. It is near today's worst." |
| AQI 420, not elevated | "Open up at 14:00, the clean window, before it climbs at 23:00." |
| AQI 137 (real), peak soon | "Open up now, while it is at its best. It rises again around 01:00." |
| AQI 137, peak far | "Windows open. Better than it has been, still 4.8× the WHO guideline." |
| AQI 60, ratio 0.9 | "Windows open. Under the WHO guideline." |

The word "calm" never appears (source comment at the `ratio` branch explicitly forbids it). The AQI≥201 branch never says "open up" while also saying it climbs — the climb clause only fires inside legitimately-open branches. **No contradiction found.** Minor: the AQI-137 "peak far" branch drops the imperative and returns a bare "Windows open.", which is a statement, not an instruction; logged as U-N2 (NIT).

### F1e — Exposure ladder: four rungs, real numbers, bars — **PASS**
Rungs at 390 px (default household): `OUTDOOR 71.5 µg/m³` · `INDOORS 43.7 µg/m³` · `AT THE STOVE 57.9 µg/m³` · `BREATHED TODAY 1096 µg`.
- Track fills computed from real values (`fill.style.width = val/concMax*100%`); verified inline `--a:` values across the 24 columns.
- The fourth rung deliberately has **no** bar ("a different quantity, so a shared scale would be a lie" — correct).
- Unit line agrees with the rung: "your **1,096** µg a day is about 2.2 cigarettes' worth". (A screenshot appeared to show 1006 vs 1,096; DOM re-read at rest confirmed 1096 in both places — the mismatch was a count-up animation caught mid-frame, not a bug.)

### F1f — 24 h chart: 24 bars, cooking marks, now cursor, text alternative — **PASS**
- `#plot` has exactly **24** children; 2 carry `class="col cook"`; each column holds an `.amb` and an `.in` bar (72 `<i>` total = 24×3 including marks).
- `#cursor` present at `left: 93.75%` (22:00 of 24 h) — the "now" position.
- `role="img"` + `aria-labelledby="bandDesc"` confirmed on `#plot`. Full text alternative read:
  > "Outdoor fine particles by hour, micrograms per cubic metre: 00:00 130.9, 01:00 129.5, … 23:00 70.1. Indoor-weighted household exposure: 00:00 52.4 … 21:00 46.8. Low point 14:00 at 46.9; next peak 00:00 at 130.9. The stove is lit around 08:00 and 20:00."
- This is a genuinely good alternative: all 24 outdoor values, 8 indoor samples, the trough, the peak, and the cooking marks in words.

### F1g — Scrubber: pointer + arrow keys move the readout — **PASS** (with a gap)
- `role="slider"`, `tabindex="0"`, `aria-valuemin=0`, `aria-valuemax=23`, `aria-valuenow=22`, `aria-valuetext="22:00, 72.4 micrograms outdoor, 37.1 indoors"` — all present and honest.
- Real `ArrowRight` ×3 from 22:00 → readout "AT 01:00 / OUTDOOR 129.5 / INDOORS 52.4". `ArrowLeft` → 00:00. Readout never showed "—".
- **Gap:** `Home`, `End`, `PageUp`, `PageDown`, `Escape` are all no-ops (`bindScrub` only handles `ArrowRight`/`ArrowLeft`). `End` in particular is expected on a slider. Logged **A-S1 (MINOR)**.

### F1h — Bench: tick → /api/combine → % changes, per-person bars, overlap reported — **PASS**, with three honesty defects
Working parts:
- 14 picks render; ticking `clean_fuel` + `kitchen_exhaust` → `#pickCount` "2 chosen", `#cutPct` −4.4%, `#cutSub` "Household dose 3963 → 3789 µg a day", `#cutBand` "band 3.3–5.3% · ₹7,500 to set up · ₹-900/yr".
- `#ppl` renders 4 per-person rows with before/after bars: Amma −16.6%, Child −0.8%, You −0.5%, Partner −0.5%.
- `#overlap` un-hides and reports: *"One at a time these would claim 5.4%; together they give 4.4%. They overlap by 1 points…"*.
- API agrees: `naive_sum_pct 39.4`, `effect.pct 33.0`, `overlap_pct 6.4` for the Sita pair.

Defects found here:
- **F-H1 (MINOR)** — *"They overlap by 1 points"* — plural not inflected. `index.html:865` concatenates `Math.abs(r.overlap_pct)` with a hard-coded "points". Reproduce: tick `clean_fuel` + `kitchen_exhaust`.
- **F-H2 (MAJOR)** — conflict says "dropped the rest" but nothing is dropped in the UI. Ticking `diy_filter` + `cleaner` → `#cutPct` −36.3% (identical to `diy_filter` alone), both checkboxes still `aria-pressed="true"`, `#pickCount` reads "2 chosen", and `#conflict` reads *"These cannot both be true: home.cleaner. Kept the first, dropped the rest."* The second action is silently ignored while the UI says it was chosen. Also leaks a raw field path (`home.cleaner`) to the user.
- **F-H3 (MAJOR)** — order-dependent answer. `POST /api/combine {keys:["induction","clean_fuel"]}` → **37.1%**; `{keys:["clean_fuel","induction"]}` → **31.3%**. Same two ticks, different total, decided by click order (`conflicts.kept` flips `electric`↔`lpg`). The bench is the app's centrepiece; a household that ticks the same two boxes in a different order gets a different number.
- **F-H4 (MINOR)** — `₹-900/yr` renders a negative rupee amount (`inr()` at `index.html:437` is `v ? "₹"+round(v) : "free"` — no negative handling). Reproduce: tick `clean_fuel` whose runtime saving exceeds setup.

### F1i — Plan: actions ~1 s before prose; rail unchanged — **PASS** on mechanism, **FAIL** on the brief's "5 actions"
Actions-before-prose is genuinely correct. Measured on the default household (`localStorage` cleared):
```
t=0.5s  planby="from your numbers"   rows rendered, #plan text 1121 chars, head "WRITING IT / 16 characters in"
t=3s    planby="from your numbers"   progress "148 characters in"
t=15s   planby="worded on this device"   msg "Plan wording ready. The actions have not changed."
t=60s   identical to t=15s
```
Rail row count at t=2 s: **3**; at t=25 s: **3**. The rail does not change when prose lands — verified by comparing `.ract` innerText before and after. The three `.slot.pending` paragraphs reserve height and fill in place; the progress line is `zero-state → "Choosing what to say" → token counter → done`, all inside `aria-live` `#planMsg`.

**But the count is wrong vs the brief:** the plan never renders 5 actions on real data. Measured rail rows:
- default household, AQI 137 → **3** rail rows (2 actions + THE ONE THING), `#plan .doneBtn` = **2**
- Sita/Baba biomass → **2** actions, `doneBtn` = **2**
- Kanpur, AQI 211 → **4** rail rows, `doneBtn` = **3**

`skeleton()` gates nearly every action behind `aqi >= 201` or `aqi >= 301` (`narrator.py:195–232`). At today's actual AQI of 137, only `keep_cooker_out` (+ `exercise_time` when someone exercises) survives. **F-I1 (MINOR — brief mismatch, not a runtime error):** the "five actions" claim in the brief only holds on a severe-air day; the shipped default state shows 2–3. Either lower the gates or restate the claim.

### F1j — People cards: 4 people, tap → breakdown by place — **PASS**, with a mislabelled percentage
- 4 cards render (`#people > *` = 4), each `role=button` with `aria-pressed`.
- Tapping Amma → `#personNote`: *"Amma takes 931 µg a day — 37.6% of the household's total. Where it comes from: home 68%, kitchen 32%."*
- No `0.348%` artefact — `pctOf()` at `index.html:1312` correctly multiplies a 0..1 fraction by 100. **The old bug is fixed.**
- **F-J1 (MAJOR)** — the 37.6% is **not** a share of household dose, but the copy says it is. Amma's dose share is 931/3963 = **23.5%**; You 27.7%, Partner 27.7%, Child 21.2%. The 37.6% is `attributed_risk_share` = `dose × sensitivity / Σ`, and Amma's sensitivity is **1.96** (`engine.py:520–523`). Verified arithmetic:
  ```
  weighted: You 1096·1.00, Partner 1096·1.00, Child 840·1.00, Amma 931·1.96
  → 22.6%, 22.6%, 17.3%, 37.6%   ← matches the UI exactly
  unweighted dose share → 27.7%, 27.7%, 21.2%, 23.5%
  ```
  The card label is `share 37.6%`, the note says "37.6% of the household's total", and `#personNote` in its default state says *"Amma carries the most of it — 37.6% of the household's inhaled dose."* **That last sentence is false as written**: Amma carries 23.5% of inhaled dose; she carries the most *risk*. Two visible statements on the same page ("You carry the most" in the ladder vs "Amma carries the most" in the note) disagree because one ranks by dose and the other by weighted risk. Reproduce: default household, read rung 4 of the ladder, then read `#personNote` under "Who carries it".

### F1k — Theme toggle changes theme and persists — **PASS**
- `data-theme="dark"` → click → `"light"`; `body` background `rgb(14,16,18)` → `rgb(238,237,234)`; button label `LIGHT`↔`DARK`; `aria-pressed` flips; `aria-label` swaps between "Switch to dark/light appearance".
- Stored as `saans.theme` = `"light"`; after reload `data-theme` = `light` and background = `rgb(238,237,234)`. **Persists correctly.**

### F1l — First-run banner — **PASS**
- `localStorage` cleared → `#samplebar.hidden = false`, text: *"These numbers are for a sample household — four people, gas stove, two-wheeler. Nothing below is about you yet."* with a "Describe yours" button.
- Clicking "Describe yours" opens the editor: `#ed.open = true`, 4 person chips (You/Partner/Child/Amma), 4 fuel radios, 4 exhaust radios, 7 mode radios, "Save and re-run".
- With a saved household → `#samplebar.hidden = true`. **Both directions verified.**

### F1m — Done-markers persist and are date-scoped — **PASS**
- Click first MARK DONE → `aria-pressed="true"`; storage key: **`2026-11-23|early-afternoon-walk-or-train-between-13-00-and-`**. Today is 2026-11-23 — the date prefix is correct (`actionKey()` uses local date, not UTC).
- After reload → `["true","false"]`, and the `aria-label` correctly became "Mark not done: Walk or train between 13:00…".
- Rollover simulated by rewriting the key's date to `2026-11-22` and reloading → `["false","false"]`, proving a yesterday-marked action does **not** read as done today.

---

## 2. UI / UX

### U1 — Does the fold answer the three questions? — **PASS at 390/1440, FAIL at 320**
Above the fold at 390×844: verdict (full), all four ladder rungs, and 22 px of the chart. At 320×760: verdict + ladder, **chart entirely below the fold** (`chartPx: 0`). At 1440×900: verdict, ladder, full chart, readout, and the top of the bench.
- "Can I open the window?" — **yes**, the verdict is the H1 and answers it in the first sentence.
- "Can the child go out?" — **partly**. The school line ("The school says normal outdoor play is fine") lives inside the plan, which at 390 px is ~2 screens down. The `#school` payload exists in `brief.school` and could be surfaced in the hero for one line.
- "What is the one thing?" — **no, not in the fold.** "THE ONE THING" sits at the bottom of the plan, roughly 2,000 px down at 390 px. The single most important answer is the furthest thing from the first screen. **U-1 (MAJOR, design):** promote THE ONE THING above or beside the ladder.

### U2 — Visual hierarchy — **PASS**
Serif display verdict (44 px desktop / 34 px mobile) against 10–13 px mono/sans labels is a strong, non-generic hierarchy. The plate is the only dark block in light theme — correctly the focal point. Numerals are consistently tabular. No competing gradients.

### U3 — "Generic AI-dashboard slop" — **PASS, notably clean**
Measured in source: `linear-gradient`/`radial-gradient` = **0**; `backdrop-filter`/`blur(` = **0**; icon tiles = 0; oversized rounded cards = 0 (`--rad: 2px`, used 21×; the only `50%` radii are the 4 person-card avatars). No emoji anywhere in the file (the one emoji I initially saw in `document.title` turned out to be injected by my own browser harness — the served HTML has a clean `<title>Saans — what the air costs your household</title>`; **discarded as a false positive**). This does not read as AI slop; it reads as a printed instrument.

### U4 — Spacing consistency — **PASS with one exception**
Font sizes cluster tightly (10 px ×29, 10.5 px ×25, 13 px ×17) — a deliberate type scale, not drift. Spacing is consistent within sections. Exception: **U-4 (MINOR)** the ladder row at 320 px breaks into a 3-column grid with the `why` text landing in a second row under the number, which reads as misalignment (`gridTemplateColumns: "72px 124px 58px"`, `rows: "45px 27.67px"`).

### U5 — 1440 px dead space — **MINOR**
`.hero` is 627 px tall; the right column (chart) is only **192 px** tall, leaving ~435 px of empty page to the right of the ladder. The chart would benefit from height:100% or the ladder from a 2-column layout at ≥1200 px.

### U6 — Pick labels truncated at mobile — **MAJOR**
At 390 px every one of the 14 intervention titles is ellipsis-clipped (`.pick .pt { white-space:nowrap; text-overflow:ellipsis }`):
```
"Box-fan filter: a MERV13 furnace filter tap…"  shown 266px / full 612px
"Run a HEPA filter in the room you sleep in…"   shown 266px / full 516px
"Shorter, higher-heat cooking: pressure-co…"    shown 266px / full 559px
```
The one place the user chooses what to do hides what the choices are. Allow 2-line wrapping.

### U7 — Raw developer strings leak to users — **MINOR**
`#conflict` prints `home.cleaner` and `home.cooking_fuel` — dotted Pydantic field paths. Should render as "the air cleaner" / "the cooking fuel".

### U8 — Unit consistency in prose — **PASS**
Rendered prose uses `µg/m³` throughout, and `ug/m3` count on the live page is **0**. (An early sighting of `ug/m3` in streaming prose was normalised by `narrator.enforce` before the `plan` event; transient, not a shipped defect.)

---

## 3. Responsive — **PASS**
Measured `document.documentElement.scrollWidth` vs `innerWidth`, both themes, four widths:

| Width | Light | Dark |
|---|---|---|
| 320 | 320 / 320 → **no overflow** | 320 / 320 → no overflow |
| 390 | 390 / 390 → **no overflow** | 390 / 390 → no overflow |
| 768 | 768 / 768 → **no overflow** | 768 / 768 → no overflow |
| 1440 | 1440 / 1440 → **no overflow** | 1440 / 1440 → no overflow |

No element extends past the viewport except `a.skip` (intentionally parked at `left:-9999px` until focused) and the `.pt` children already scoped by `overflow:hidden` on their parent. Screenshots captured at 320, 390, 768, 1440 in both themes.

---

## 4. Accessibility

All Tab tests used real `Input.dispatchKeyEvent` with `windowsVirtualKeyCode`/`nativeVirtualKeyCode`, never `el.focus()`.

### A1 — Tab order — **PASS**
30 documented stops from a cold load, top to bottom, ending in the ledger `<summary>` rows. Order is logical: skip link → place → theme → 4 ladder rungs → scrubber → 14 picks → Show in ledger → Clear → 2 Mark done → 2 person cards → ledger summaries. No trap, no invisible stop.

### A2 — Visible focus ring on every control — **PASS, genuine**
All 30 stops reported `:focus-visible = true` with `outline-width: 2px; outline-style: solid`. Colour is theme-correct (`rgb(17,20,23)` on light surfaces, `rgb(247,246,241)` on the dark applied/clear buttons). This was measured **after real keypresses**, so it is not the `el.focus()` false negative the brief warns about.

### A3 — Skip link works — **PASS**
Cold load: `a.skip` at `rect(-9999, 0)`. After one Tab: `rect(10, 10)` — visible. Enter → `location.hash = "#main"`, `document.activeElement = main`. Skip link is functional.

### A4 — Every input labelled — **PASS**
16 inputs total. `#q` has a real `<label class="sr" for="q">Search for a place</label>`; all 15 radios have `e.labels.length > 0` with descriptive text ("Wood or dung / chulna, crop waste" etc.). Zero unlabelled inputs. Zero unnamed buttons in the accessibility tree (985 AX nodes, 0 buttons without an accessible name).

### A5 — Every chart has a text alternative — **PASS**
`#plot` is `role="img" aria-labelledby="bandDesc"`, and `#bandDesc` is a complete `<p class="sr">` with all 24 outdoor values, indoor samples, low point, peak, and cooking hours. Best-in-class. (The ladder is `role="group"` with a label; each rung is a labelled button.)

### A6 — aria-live on changing regions — **PARTIAL FAIL**
Present and correct: `#readout` (`aria-live="polite"`, the scrubber readout), `#planMsg` (`role="status" aria-live="polite"`, plan progress and completion).
**A-L1 (MAJOR)** — the entire bench result panel is silent. `#cutPct`, `#cutSub`, `#cutBand`, `#overlap`, `#ppl`, `#pickCount`, `#conflict` all have `aria-live = null` and no live ancestor (walked every ancestor to `body`: `[]`). A screen-reader user ticks an intervention and hears nothing — no percentage, no per-person row, no overlap explanation. This is the app's centrepiece interaction and it is unannounced.
**A-L2 (MINOR)** — `#readout` is a sibling of the slider, not referenced by it; the slider has no `aria-describedby`. Screen readers get `aria-valuetext` (good), but the richer readout is unreachable.

### A7 — Heading order — **FAIL (MINOR, structural)**
Sequence: `H1, H2, H2, H2, H2, H2, H4 ×15, H2, H5 ×13`.
- **15 × `H4` with no `H3` anywhere in the document**, all reading `each person, before → after` inside the 14 ledger `<details>` (plus one inside an open option body).
- **13 × `H5`** inside the collapsed evidence `<details>`, again with no `H4` above them in a valid chain.
- Headings skip levels in both directions — 15 duplicate H4s that are identical in text, so a heading-list navigation is useless there.
Reproduce: `document.querySelectorAll('h1,h2,h3,h4,h5,h6')` and observe the tag sequence. Fix by promoting option titles to `H3` and demoting "each person…" to `H4`, and the drawer group titles to `H4`.

### A8 — Contrast, computed style, both themes — **PASS** (one transient artefact, correctly discarded)
Sampled 76 distinct text/bg pairs per theme with the composited background resolved by walking up to the first opaque ancestor.

**Light: 76 pairs, 0 failures.** Worst pair 4.80:1 (10 px `#5b605e` on `rgb(224,223,218)`) — just over the 4.5 threshold, acceptable.

**Dark: 76 pairs, 0 static failures.** Modal body text 6.14:1 (`rgb(147,154,151)` on `rgb(22,25,28)`), works.

An early sample showed `DELHI`/`LIGHT` chips at **1.74:1** in dark. I reproduced it and traced it to the **90 ms `transition: color`** (`--d1: 90ms`) mid-flight during a theme switch, not a resting state: at rest the chips are `rgb(194,198,196)` on `rgb(14,16,18)` = **10:1**. Confirmed by clean-reload measurement with no toggle. **Discarded as a false positive — do not "fix" it.** (Recorded here because the brief asked me to measure before reporting colour, and the measurement initially looked like a real failure.)

### A9 — Geocode combobox semantics — **FAIL (MINOR)**
`<div role="listbox" aria-label="Matching places">` contains `<button role="option">` children — invalid: `option` is not a permitted child of `button`, and a listbox should own its options. `#q` is a plain textbox with **no** `role="combobox"`, no `aria-expanded`, no `aria-controls`, no `aria-activedescendant`. Real `ArrowDown` after typing "Delhi" left focus on the `INPUT` and `aria-activedescendant` stayed `null` — keyboard users cannot reach the 6 results without tabbing, and will land on 6 unlabelled option buttons in sequence.

### A10 — Tap targets — **PASS with two nits**
`.pick` 44 px, `.rung` 75–90 px, `.pc2` 107 px, `.btn` 40 px — all comfortable. **A-T1 (NIT)** `.doneBtn` is 28 px and `#themeBtn`/`#placeBtn` are 32 px, both under the 44 px iOS / 36 px comfortable minimum. The done button is the app's retention loop; it is also its smallest control.

### A11 — Reduced motion — **PASS**
With `prefers-reduced-motion: reduce`, `.seg.now` reports `animation-name: none`, `animation-duration: 0s`. No transitions fire.

---

## 5. State Handling

### S1 — Plan generation at 0 s / 3 s / 15 s / 60 s — **PASS**
```
0.5 s  "WRITING IT" progress bar, "16 characters in", all 3 action rows already present, prose slots empty but height-reserved
3 s    "148 characters in", same 3 rows
15 s   prose complete; #planby flips to "worded on this device"; #planMsg = "Plan wording ready. The actions have not changed."
60 s   identical — no re-layout, no flicker
```
The reserved-height slots (`p.prose.slot.pending`) mean the page does not jump when prose lands. This is the right architecture, executed correctly. The token counter is arguably developer-facing ("148 characters in") but it is honest about what is happening rather than a fake spinner — acceptable.

### S2 — `/api/plan` returns 500 — **PASS**
Overrode `window.fetch` to return a real `500 {detail:"boom"}` for `/api/plan` and triggered a re-plan:
- `#plan` first line: *"The wording did not arrive. Your numbers are unchanged."*
- `#planMsg`: *"The wording did not arrive. The actions and figures are unchanged."*
- Both MARK DONE buttons still present; the rail, figures, and figures block intact.
Degradation is exactly right: lose the prose, keep the product.

### S3 — Corrupt `localStorage` — **PASS (degrades), NIT (never heals)**
Injected `saans.household.v1 = "{not valid json"`, `saans.picks.v1 = "[[["`, `saans.done.v1 = "nope"`, reloaded:
- No console error, no blank page. Verdict, banner, 4 people, 4 rungs, 2 actions all render.
- Falls back to the sample household and shows the banner — correct.
- **S-1 (NIT):** the corrupt value is left in place (`household after recovery: STILL CORRUPT`). Every subsequent load re-parses garbage. `store.get` should drop the bad key on a parse failure.

### S4 — Stale data — **PASS**
`#liveDot` gets class `off` when `ambient_source` is not Open-Meteo (`boot()` line 1624–1625), and the colophon names the source. Timestamps come from `data.stamp()`. The `surAside` correctly reads the *forward* window ("low 14:00 · peak 00:00") rather than a daily extremum.

---

## 6. Regression — nothing lost for the sake of looks — **PASS**

### R1 — Evidence drawer still lists 56 constants — **PASS**
`GET /api/factors` → 12 groups, **56** constants:
`health reference levels 4, inhalation rate 8, outdoor-to-indoor 3, air changes 3, kitchen PM2.5 5, exhaust modifier 4, indoor sources 5, air cleaner CADR 4, mask fitted filtration 5, transport microenvironment 9, cooking emission factor 5, India grid 1`.
The rendered `#factors` DOM contains **61** `.fr` rows and **13** `.fg` groups — the extra group is "limits" (5 rows), which is prose, not constants. **56 + 5 = 61.** Every constant still carries a `MEASURED / LITERATURE / STANDARD / ESTIMATE` badge. Nothing was dropped.

### R2 — Option ledger shows every intervention — **PASS on behaviour, FAIL on the number 14**
All 15 options render (`#ledgerAside` reads `"15 options"`, `#opts > *` = 15), including the 5 zero-effect ones marked `nothing to change` / `not counted` rather than hidden. Nothing was silently deleted.
**R-2 (MINOR):** the catalogue is **15, not 14** (`len(advisor.CATALOGUE) == 15`; keys include `geotag_burn` and `plant_trees`). `CombineRequest.keys` still documents "14 is the catalogue size" and the brief says 14. Either the two civic actions are new and the comment is stale, or one was meant to go. The count is now inconsistent in three places (brief, `server.py:145` comment, reality).

### R3 — Per-person dose table exists — **PASS**
`#people` renders 4 cards with name, age, `µg/day`, and share; the API exposes the full table (`dose_ug`, `inhaled_m3`, `mean_exposure`, `cigarettes`, `who_multiple`, `by_place`) and `sum(doses) = 3963 = household_dose_ug` exactly. Tapping gives place breakdown. The table survived.

### R4 — Numbers agree across surfaces — **PASS**
`ambient 71.5` in kicker, ladder, plan figures and bandDesc. `kitchen 57.9` (default) / `197.9` (biomass) consistent. `1096 µg` in rung 4 and in the unit line. Household dose 3963 = Σ person doses. No drift found.

---

## 7. Prioritised defect list (worst first)

| # | Sev | ID | Defect | One-line reproduction |
|---|---|---|---|---|
| 1 | **MAJOR** | F-J1 | "37.6% of the household's total/inhaled dose" is actually a **sensitivity-weighted risk share**; true dose share is 23.5%. The ladder says "You carry the most", the note says "Amma carries the most" — both visible, contradicting. | Load default household → read ladder rung 4, then read "Who carries it" → note. |
| 2 | **MAJOR** | F-H3 | Bench result depends on **click order**: same two keys give 37.1% or 31.3%. | `POST /api/combine keys:["induction","clean_fuel"]` → 37.1; swap the array → 31.3. |
| 3 | **MAJOR** | F-H2 | "Kept the first, dropped the rest" while both stay ticked and counted ("2 chosen"); the dropped one is invisible. Leaks raw `home.cleaner`. | Tick "Box-fan filter" + "HEPA filter" → read `#conflict`. |
| 4 | **MAJOR** | A-L1 | Bench results have **no aria-live**; ticking an intervention announces nothing to a screen reader. | `[...document.querySelectorAll('[aria-live]')]` → only `readout`, `planMsg`. |
| 5 | **MAJOR** | U6 | All 14 intervention titles are ellipsis-truncated at 390 px (266 px shown of 612 px). | Load at 390 px, look at "Build your plan". |
| 6 | **MAJOR** | U1 | "THE ONE THING" — the single most-asked answer — sits ~2,000 px down, never in the fold. | Load at 390×844; `#plan` is below `bench`. |
| 7 | MINOR | A7 | 15 `H4` with no `H3`; 13 `H5` orphaned; levels skip both ways; 15 identical H4 texts. | `[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h=>h.tagName)`. |
| 8 | MINOR | F-I1 | Plan renders 2–3 actions at today's AQI 137, not the claimed 5; all gated behind `aqi>=201/301`. | Clear storage, count `#plan .rrow` → 3. |
| 9 | MINOR | F-H4 | `₹-900/yr` — negative rupee rendering. | Tick `clean_fuel` in the biomass household. |
| 10 | MINOR | F-H1 | "overlap by 1 **points**". | Tick `clean_fuel` + `kitchen_exhaust`. |
| 11 | MINOR | A9 | listbox owns `role=option` buttons; no `combobox`/`aria-activedescendant`; ArrowDown does nothing. | Open place search, type "Delhi", press ArrowDown. |
| 12 | MINOR | A-S1 | Slider ignores Home/End/PageUp/PageDown. | Focus scrubber, press End → readout unchanged. |
| 13 | MINOR | U5 | 435 px of dead space right of the ladder at 1440 px (hero 627 px, chart column 192 px). | Load at 1440×900. |
| 14 | MINOR | R-2 | Catalogue is 15, not 14; `CombineRequest` comment says 14. | `len(advisor.CATALOGUE)` → 15. |
| 15 | MINOR | U-4 | Ladder row breaks to an orphaned second grid row at 320 px. | Load at 320 px, look at rung 1. |
| 16 | MINOR | A-L2 | Slider has no `aria-describedby` to `#readout`. | Inspect `#plotwrap` attributes. |
| 17 | NIT | S-1 | Corrupt `localStorage` is never cleared; re-parses on every load. | Set `saans.household.v1="{bad"`, reload twice, inspect the key. |
| 18 | NIT | A-T1 | `.doneBtn` 28 px, chips 32 px — below comfortable tap size. | Measure `.doneBtn` height. |
| 19 | NIT | U7 | Raw field paths (`home.cleaner`) shown to users. | Same repro as #3. |
| 20 | NIT | F-R4 | `/api/simulate` is the only route still on the wrapped shape; a flat body 422s. | `POST /api/simulate` with a flat household → 422. |
| 21 | NIT | U-N2 | Verdict "peak far" branch drops the imperative ("Windows open. Better than…"). | Call `verdictText` with peak 5 h out. |

**False positives I chased and discarded** (recorded so nobody re-opens them): the 1.74:1 dark chip contrast (90 ms transition mid-flight; 10:1 at rest); the 1,006 vs 1,096 µg mismatch (count-up animation frame); `ug/m3` in prose (normalised by `narrator.enforce`); an emoji in `<title>` (injected by my browser harness — the served HTML is clean).

---

## 8. What genuinely works (so the fix list is not read as a verdict on the whole)

- The household→server path is fixed at both layers. Kitchen 197.9 for biomass. Sita and Baba arrive.
- The verdict sentence is coherent across every branch I could synthesise, and it refuses to call 4.8× the WHO guideline "calm".
- The chart's text alternative is better than most commercial accessibility.
- Actions-before-prose is real: rows at ~1 s, prose at 13–25 s, and **the rail provably does not change**.
- Error handling on `/api/plan` 500 and on corrupt storage is graceful and honest ("The wording did not arrive. Your numbers are unchanged.").
- Done-markers are date-scoped and survive reload; yesterday's marks correctly vanish.
- Zero console errors, zero overflow at 320/390/768/1440 in both themes, 56 constants intact, all 15 options listed, per-person table intact.
- Visually it is not AI slop: no gradients, no glassmorphism, no emoji, 2 px radii, a real type scale.

## 9. Verdict

**Not shippable as-is; shippable in one focused pass.**

Fix the six MAJORs — they are all small, local changes:
1. Rename the people-card metric to "share of risk" (or show both), and make `#personNote` and ladder rung 4 rank the same quantity. This is the honesty bug.
2. Make `combine()` order-independent, or sort `keys` canonically server-side before applying patches.
3. Either untick and visibly strike the dropped action, or stop saying "dropped the rest".
4. Add `aria-live="polite"` on `#cutSub` (one attribute).
5. Let `.pick .pt` wrap to two lines.
6. Move "THE ONE THING" into the hero.

Items 1–4 are truthfulness and access defects on the app's centrepiece. None requires redesign. With those closed, this is a strong, unusually honest product — the arithmetic is right, the numbers reconcile across every surface I could cross-check, and the accessibility work is well above the norm. The remaining MINORs are polish.

**Reviewed by:** Agent 5. Read-only throughout: no application file, test, stylesheet, `.py`, or other `.md` was modified. `git status --short` shows only `?? UI_QA_REPORT.md`. Screenshots were captured and inspected at 320, 390, 768 and 1440 px in both themes via the browser harness; they were temporary review artefacts and are not committed.
