# UX_ARCHITECTURE — Saans

**Author:** Agent 2, UI/UX Architect. **Status:** normative. This document specifies the
interface; it does not contain application code.
**Binding constraints:** one `index.html`, no build step, no framework, no CDN, no web
fonts, CSP `default-src 'none'`, WCAG 2.2 AA, dark mode first-class,
`prefers-reduced-motion` and `prefers-contrast` honoured, 390×844 target device.

Where this document names an API field it means the field the current server already
returns. Where it asks for a field that does not exist, it says **NEW FIELD** and the
reason. There are exactly two such requests in the whole document, and neither is a
dependency: the UI is correct without both.

---

## 0. The thesis, in one paragraph

Saans is not a dashboard and not a chat. It is **one argument, read top to bottom**:
*this is your family's air → this is the hour it turns → this is what you can change →
this is your plan → this is who pays for it.* Every layout decision below exists to keep
that argument in one uninterrupted column on a 390px screen, and to make the one slow
thing in the product (30–90s of local LLM prose) feel like the app is working rather than
hanging. The architecture is therefore a **single scroll with a chapter spine and two
modal sheets** — not tabs, not a wizard, not a feed.

---

## 1. The one-screen contract

### 1.1 The device, stated honestly

390×844 is the CSS viewport in a device emulator. On a real entry-level Android in Chrome
the URL bar and the system nav eat **~104px**, so the *visible* height at 06:40 is
**≈740px**, not 844. **The fold is designed for 740px.** Anything that only works at 844
is a bug. I therefore place the 740px line explicitly in the wireframe and treat
740–844px as a bonus band that must never contain a *required* element.

Device assumptions that change the design:

| Assumption | Consequence |
|---|---|
| ~360–390 CSS px wide, DPR 2–3 | One column, always. No side-by-side until 720px. |
| Thumb reaches the bottom 55% comfortably, the top 12% awkwardly | Destructive and frequent controls live low; the verdict lives high because it is read, not touched. |
| Cold hands, 06:40, one hand, possibly gloves | Minimum target 44×44px, 8px minimum gap, no swipe-only gesture, no long-press, no hover-only affordance. |
| Screen at 30% brightness in a dark kitchen | Dark theme is the default; light theme is the opt-in. Contrast floor 7:1 for body text, not 4.5:1. |
| Slow 3G-class network, 2–6s for the first `/api/brief` | No skeleton-to-content flash. The page paints its own frame in the first 200ms with real labels and `—` for every figure, then fills. |
| Font rendering on cheap panels | System stack only. No weight below 400. Minimum 12.5px for secondary text, 15px for anything a user must act on. |

### 1.2 What is above the fold, in order, with pixel heights

Content column is 358px wide (390 − 16px padding each side). All heights are CSS px,
measured from the top of the viewport with the page at scroll 0.

| # | Element | Height | Type | Ends at |
|---|---|---|---|---|
| 1 | Masthead (sticky) — place chip, live dot, clock, theme | 44 | 13/16 medium | 44 |
| 2 | Kicker — `DELHI · PM2.5 · AQI 322` | 18 | 11/14, +0.08em, uppercase | 70 |
| 3 | **Verdict** — `h1`, max 2 lines, ≤ 96 chars | 62 | 25/31, −0.01em | 138 |
| 4 | **Do-now strip** — one imperative, one hour, one effect | 52 | 15/20 + 12/16 | 202 |
| 5 | **Exposure ladder** — 4 rungs, one line each | 144 | 12.5/16 labels, 19/16 tabular values | 358 |
| 6 | **24-hour surface** — header 22 + plot 140 + axis 16 + readout 42 | 224 | 12.5/16 header, 14/18 readout | 594 |
| 7 | Bench header `What could you change?` + subline | 40 | 17/22 + 12.5/16 | 642 |
| 8 | Gap + **one complete pick row** — the invitation to act | 98 | 15/20 | 740 |

**740px exactly.** Items 1–8 are fully visible on a real Android; the fold lands in the
gutter between pick row 1 and pick row 2. One whole interactive row above the fold is the
minimum evidence that this page does something, and it is a stronger invitation than a
"scroll for more" chevron at a third of the height.

### 1.3 Why each survivor is on the fold, by the decision it enables

| Element | The decision it enables | What breaks if it moves down |
|---|---|---|
| Verdict `h1` | **"Does today need a decision at all?"** A single sentence naming one person and one number tells a parent in 2 seconds whether to keep reading. | If it is not the first thing, the user's first act is to interpret a chart, which they cannot do without the sentence. |
| Do-now strip | **"What do I do in the next sixty minutes?"** This is the only action that is time-critical; the situation is already happening at 06:40. | The most urgent output becomes the last thing found. Users leave with the number and no act. |
| Ladder | **"Is the danger outside my door or inside my kitchen?"** This is the product's single most consequential correction. A family that assumes outdoor air will open windows at the worst hour. | The chart becomes a weather report. The entire indoor-attribution claim disappears below the fold. |
| 24-hour surface | **"When?"** Opening a window is a *timing* decision, not a yes/no. The chart is the only element that answers it. | The verdict's "open at 12:00" becomes an unsupported instruction. |
| Bench peek | **"This is a thing I can change, not a thing I am told."** The product's verb is selection. | The page reads as a report — the exact failure mode of the city AQI apps this replaces. |

### 1.4 What is deliberately below the fold, and why

| Pushed down | Where | Why it is not on the fold |
|---|---|---|
| The other 11 of 14 interventions | Bench, behind `All 14 options` | Choice overload is the enemy of acting. Three options that fit *this* household, then the catalogue. Ranked, so the three are the right three. |
| The generated plan (30–90s) | Immediately after the bench | It cannot be on the fold because it does not exist yet. It must not block the fold either. See §5. |
| The full per-person table | Section 4 | The `h1` and the ladder's 4th rung already name the worst person and their share. The table is for the follow-up question "and what about me?" |
| The 14-row option ledger | Section 6 | It is a decision *audit*, read after choosing, not before. It is also the researcher's surface. |
| All 56 evidence constants | Sources sheet | Trust is served *after* the claim, in the drawer the claim points at. Presenting it first converts a 20-second visit into a 4-minute read. |
| Household editor | Setup sheet | It is a prerequisite, not a destination. As a section it was the last thing on the page and nobody found it (§9, friction 3). |
| Sources / methodology | Sources sheet | Same reason as the ledger. |
| Theme toggle | Masthead (kept, but 32px) | Cheap to keep, used once, and it is the only control a user might need before they can read anything in a dark kitchen. |

**Rule:** no element above the 740px line may require data that arrives after
`/api/brief` resolves. The fold must be *structurally* complete at first paint — labels
present, values `—`.

---

## 2. Navigation model

### 2.1 The decision

**One scroll. One column. A sticky chapter spine. Two modal sheets. No tabs, no views,
no router.**

Formally:

- The document is a single vertical sequence of **ten regions (R1–R10, §3)** in a fixed
  order.
- The masthead is 44px sticky and doubles as a **chapter marker**: its right side shows
  the name of the region currently occupying the top third of the viewport
  (`Today` → `Your plan` → `Who carries it` → `Every option` → `Sources`). Tapping the
  label opens a 5-item popover that scrolls to a region. It is a table of contents, not
  a tab bar: the label never implies "you are in a different place", it says "you are
  at this point in one page".
- Exactly **two sheets**, both `<dialog>`: **Setup** (`Your household`) and **Sources**
  (`The arithmetic and its sources`). They are the only two things in the product that
  are *tasks you leave the reading to do*, and the only two that can be entered from more
  than one place.

### 2.2 Why a scroll, and what it buys

The product is a **causal chain**: street air → indoor air → kitchen plume → one person's
daily dose → the effect of a change. That chain is an argument, and arguments are read in
sequence. A scroll preserves adjacency: the ladder sits directly above the chart that
explains it, which sits directly above the bench that changes it. The user can point at
two things at once — "outside 205, my kitchen 91, Amma 1,791" — which is impossible when
those three live in different views.

It also costs nothing. There is no router to write, no view-state to persist, no
transition to get wrong, no back-button lie, and no re-render on tab switch. The browser's
own scroll restoration, find-in-page, and deep-link-by-fragment all keep working. Every
one of those is a real accessibility and resilience feature that a hand-rolled view
switcher would have to reimplement and would get wrong.

### 2.3 Why not tabs (the alternative I rejected)

A 4-tab bottom bar — `Today · Plan · Act · Home` — is the conventional answer and it is
wrong here for four specific reasons:

1. **It hides the comparison that is the product.** The bench's whole value is watching
   the household number fall while the ladder is still on screen. Tabs force an
   eye-memory task.
2. **The back button starts lying.** With no router, tab switches either push history
   (back walks through tabs the user did not navigate) or do not (back exits the app from
   a tab the user believes is a page). Both are wrong, and neither is fixable without a
   router.
3. **It multiplies state.** Each tab needs its own loading, empty, error, and stale
   treatment, and each must survive a tab switch mid-stream. That is 4× the state machine
   in a 65KB file.
4. **It prices the fold.** A 56px bottom bar over a 740px viewport is 7.6% of the screen,
   permanently, to navigate 6 screens of content that a thumb-flick already traverses in
   under two seconds.

### 2.4 Transition, focus, and the back button — exact rules

| Event | Behaviour |
|---|---|
| Tapping a spine item | `scrollIntoView({block:'start', behavior: reducedMotion ? 'auto' : 'smooth'})`, then focus the region's `h2` with `tabindex="-1"`. Scroll only — **never** `history.pushState`. |
| Opening Setup or Sources (user-initiated) | `history.pushState({saans:'setup'}, '')`, then `dialog.showModal()`. The URL gains `#setup` / `#sources` via `replaceState` on the same entry so it is shareable, but the *entry* exists so back closes rather than exits. |
| Opening Setup on first run (automatic) | `history.replaceState({saans:'setup'}, '')` — **no new entry**. Back must leave the app, not re-open a sheet the user did not ask for. |
| Browser back while a sheet is open | `popstate` closes the sheet. The page does not navigate. This is the single most important rule in the model: back is never a trap. |
| Closing a sheet with its button or `Esc` | Call `history.back()`; the `popstate` handler performs the close. One code path, so the stack can never desynchronise. The close button is `history.back()`, not `dialog.close()`. |
| Back with no sheet open | Normal browser behaviour — leaves the page. Never intercepted. |
| Scroll position | **Never** written to history. `history.scrollRestoration = 'manual'` is not used; default restoration is correct because there is only one document. |
| Returning from a sheet | Focus returns to the element that opened it. If that element no longer exists (the household was edited and the page re-rendered), focus goes to the region `h2` it belonged to. |
| Reduced motion | `behavior:'auto'` everywhere; no cross-fade on the dialog — `showModal()` only, with `@media (prefers-reduced-motion: no-preference)` adding a 120ms opacity fade. |

**Anchor rule:** the page contains **exactly one** in-page `<a href="#...">` — the skip
link. Every other jump is a `<button>` calling `scrollIntoView`. Reason: a fragment link
creates a history entry, which breaks the back-button contract above, and with
`default-src 'none'` the only other legitimate links in the product are the external
source citations (`<a target="_blank" rel="noopener noreferrer">`). The skip link is the
exception because it is the one thing a keyboard user needs before the page has painted,
and because its history entry is the browser's expected behaviour.

---

## 3. Page and component breakdown

Region order, top to bottom, is fixed. `R1…R10` are the ten scroll regions; `S1`, `S2`
are the sheets. Every component states its data source (**API field**), its states, and
its **absent rule** — what it does when the data is missing.

### 3.0 Global rules that apply to every component

1. **A missing number is never zero.** Absent → `—` in a `muted` span with
   `aria-label="not available"`. `0` is a real value and is printed as `0`.
2. **A container with no data collapses.** Header, rule, and padding go with it. No empty
   bordered boxes, no "No data" placeholders inside a card that pretends to be full.
3. **Numbers are tabular.** `font-variant-numeric: tabular-nums` on every figure, so the
   tally and the readout do not jitter when they change.
4. **Every async region has four named states** — `loading`, `ready`, `empty`, `error` —
   plus `stale` and `partial` where §5 says so. No component may ship with three.
5. **No component owns a second copy of the truth.** The bench tally reads from
   `/api/combine`; the ladder reads from `/api/brief`; the plan reads from `/api/plan`.
   Where they disagree, the later response wins and says so.

### R1 · Masthead — 44px, sticky, `position: sticky; top: 0; z-index: 30`

| Sub-component | Purpose | Data | States | Absent |
|---|---|---|---|---|
| Place chip | Shows and changes the location the whole model is anchored to | `brief.place` (NEW FIELD — see below), else local `household.lat/lon` label | `ready` / `pending` (chip shows last known place + spinner dot) / `error` (chip keeps last place, `aria-describedby` says "showing last known location") | Falls back to `Delhi` and the chip is visibly marked with a dotted underline. |
| Live dot + clock | Confirms the page is live and tells the user which hour the verdict is about | local `Date`, updated every 30s; dot is `live` only if `/api/health` returned `ok` and `model.available` within 10 min | `live` / `offline` (hollow dot) | Hollow dot, no text change. A dead model must not look like a dead app. |
| Chapter label | The spine (§2.4) | `IntersectionObserver` on the 7 region headings | 5 labels | Hides at scroll 0; the masthead is just the place chip. |
| Theme toggle | Dark → light. Default dark | `saans.theme` in localStorage | `dark` / `light` | `prefers-color-scheme` on first run, then persisted. |

**NEW FIELD:** `brief.place` (string, the resolved display name). Today the client keeps
the place name only in DOM text after a geocode, so a reload with a stored lat/lon shows
a stale label. One string on the brief fixes it. If declined, the chip shows `Your area`
and the design still works.

### R2 · Verdict — `h1` + kicker

| Property | Value |
|---|---|
| Purpose | Answer "does today need a decision" in one sentence and one person |
| Data | `brief.aqi.aqi`, `brief.elevated_now`, `brief.next_trough.hour`, `brief.next_peak.hour`, `brief.ambient_pm25`, `brief.indoor_pm25`, `brief.household.people[].dose_ug`, `.name` |
| Copy rule | Imperative + one named person + one figure. Never `worst_hour` (a max over 0–23, usually in the past). Always `next_trough` / `next_peak`. |
| States | `loading` — the sentence is replaced by a real placeholder line `Reading the air…` at the same 25px size, so there is no reflow; `ready`; `empty` (no people) — falls back to the concentration-only sentence `Outside air is 205.4. Inside is 123.4.`; `error` — `Could not read the air. Check the connection.` in the same slot, plus a `Try again` button. |
| Absent | `aqi` null → the kicker drops the AQI segment rather than printing `AQI 0`. `next_trough.hour` null → copy says `now`, not `00:00`. |

### R3 · Do-now strip — 52px, bordered, one row

| Property | Value |
|---|---|
| Purpose | The single time-critical instruction, extracted from the plan so it exists at 0ms |
| Data | `brief.elevated_now`, `brief.next_trough.hour`, `brief.ranked[0].key`, `.pct` |
| States | `derived` (built client-side from `brief`, no wait) / `confirmed` (replaced by `plan.today[0]` when the plan lands) / `error` (the strip is still derived; the plan error never touches it) |
| Absent | `ranked` empty → strip shows the ventilation instruction only, no `%`. |
| Note | This is the only element that is *derived before the plan it duplicates*. It exists because the plan takes 90s and the hour does not wait. |

### R4 · Exposure ladder — 4 rungs, 144px

| Property | Value |
|---|---|
| Purpose | Show the chain street → room → kitchen → a person, so the user attributes the dose correctly |
| Data | `brief.ambient_pm25`, `brief.indoor_pm25`, `brief.kitchen_pm25`, `brief.household.people[]` → max `dose_ug` |
| Rungs | 1 `Outside 205.4`; 2 `Inside 123.4`; 3 `Your kitchen 91.3`; 4 `<worst person> 1,791 µg a day · 28.5% of the household` |
| States | `loading` — 4 rungs present, bars at 0 width, values `—`; `ready`; `partial` — if `kitchen_pm25` is null (electric induction, no plume) the rung is **omitted entirely** rather than shown at 0, and a 5th line appears: `No stove plume — this kitchen does not burn fuel.` |
| Absent | `indoor_pm25` null → rungs 2–4 hidden, one line: `Indoor estimate unavailable for this home.` The ladder never partially scales: the three concentrations share one bar scale, and if one is missing the scale is recomputed from those present. |
| A11y | The 3 concentration bars are `aria-hidden`; the rung text carries the value. The 4th rung is not on the same bar scale (µg/day, not µg/m³) and is typeset as a statement, never a bar. |

### R5 · 24-hour surface — 224px

**Purpose:** answer *when*. Ventilating is a timing decision, not a yes/no, and this is the
only element in the product that can answer it.

| Sub-component | Data | States | Absent |
|---|---|---|---|
| Header `Next 24 hours` + aside `AQI 322 · low 12:00 · peak 23:00` | `brief.aqi.aqi`, `next_trough`, `next_peak` | `ready` / `stale` (`Updated 06:40` appears if the brief is older than 45 min) | Aside shows only the parts that exist. |
| Plot, 24 bars, 358×150 | `brief.hourly[].hour/.pm25` (outdoor, light) and `brief.household.hourly[].pm25` (indoor, filled) | `loading` — 24 flat bars at 6% opacity, axis present; `ready`; `partial` — missing hours render as a 1px baseline gap and the axis marks them `·`; `error` — whole block replaced by the error line, chart hidden, not an empty frame | If `hourly` is shorter than 24 the chart ends at the last hour with `to 18:00` in the aside. |
| Cursor (`.cursor`) | local `HOUR`, default = current hour | `idle` / `dragging` / `keyboard` | Always present. |
| Readout | `brief.hourly[HOUR].pm25`, `brief.household.hourly[HOUR].pm25` | `ready` / `partial` (one of the two missing → shows one) / `empty` (`—`) | Never blank: `22:00 · no reading for this hour` |
| Band description `#bandDesc` (`.sr`) | the same numbers, one sentence | always | — |

The chart is `role="img"` with an `aria-labelledby` pointing at `#bandDesc`; the scrubber
is a separate `role="slider"` wrapper (§7.2). The chart itself is not focusable.

### R6 · Bench — `What could you change?`

| Sub-component | Purpose | Data | States | Absent |
|---|---|---|---|---|
| Header + subline | Names the verb | static | — | — |
| `visible picks` (3) | The three highest dose-removed-per-rupee options that are *applicable* to this household | `brief.ranked[]` → `.key .title .pct .cost_inr .worst_person .worst_pct .effort .unquantified` | `loading` — three ghost rows at 44px, real text `Working out your options…`; `ready`; `error` — one row: `Could not rank the options.` + `Try again` | `ranked` empty → the whole bench collapses and is replaced by the static line `No change we model applies to this home yet.` |
| `All 14 options` toggle | Reveals the remaining 11 | same array | collapsed (default) / expanded | Hidden when `ranked.length <= 3`. |
| Pick row | The unit of selection. 44px minimum, checkbox glyph 18px, title 15/20, meta 12.5/16, effect right-aligned | as above | `off` / `on` / `busy` (during combine: 2px left rule pulses, row stays enabled) / `disabled` (`pct <= 0` and no cost — row rendered at 45% opacity, `aria-disabled`, still focusable so the reason is readable) | `pct` missing → the right slot shows `n/c` if `unquantified`, else `n/a`. Never `0%`. |
| Tally | The answer to "what does my selection do" | `/api/combine` → `effect.pct`, `effect.dose_before`, `effect.dose_after`, `effect.cig_before`, `effect.cig_after`, `band_pct`, `cost_inr`, `runtime_inr_yr`, `applied`, `overlap_pct`, `naive_sum_pct`, `conflicts`, `per_person[].name/.before/.after/.pct` | `empty` (0 picks) → `Nothing chosen yet.`; `loading` → `Working it out…` under a stale-but-labelled figure; `ready`; `error` → `Could not work that out. The numbers above are unchanged.` + `Try again`; `conflict` → separate row `These cannot both be true: household.fuel. Kept the first.` | `per_person` empty → the small bar list is omitted, the headline % stays. |
| Sticky tally bar (mobile) | Keeps the total visible while scrolling the 14 options | same | appears only when `picks.length > 0` **and** the tally is scrolled out of view | Hidden. |
| `Clear` | Undo the whole selection | local | `disabled` at 0 picks | — |
| ~~`Show in the ledger`~~ | **Removed.** It only scrolled. Replaced by the plan bridge (§7.1). | — | — | — |

### R7 · Plan — `Today's plan`

**Purpose:** turn ranked numbers into five dated actions in a register a tired parent will
finish reading. The prose is decoration on decisions Python has already made; the rail is
the substance and exists before the prose does.

| Sub-component | Purpose | Data | States | Absent |
|---|---|---|---|---|
| Header + `planby` | Attribution: who wrote the words | `plan.generated_by` | `streaming` → `Drafting`; `deterministic` → `built-in wording`; else `worded on this device` | `—` |
| Skeleton rows (0–90s) | The 5 actions, times and figures, available before any prose | `brief.ranked` top 3 + `next_trough` (**and** `plan.facts` if the server emits actions in it — see §5.4) | `provisional` (dotted left rule, label `from your numbers`) → `confirmed` | Fall back to 3 rows; if `ranked` is empty, no skeleton. |
| Opening prose | Register, not reasoning | `plan.opening` (SSE `token` chunks) | `waiting` / `streaming` (caret) / `ready` / `failed` (figures-only) | Prose slot collapses to 0 height; figures and rail remain. |
| Figures strip, 5 cells | The numbers the plan is anchored on | `plan.figures[].label/.value/.unit` | `ready` / `partial` (fewer than 5) | Cells absent are omitted, grid auto-fits. Never a blank cell. |
| Children paragraph | The sentence aimed at the 7-year-old | `plan.for_children` | `ready` / absent | Omitted silently. |
| Action rail, 5 rows | What to do, when, why, the effect, for whom | `plan.today[].time/.action/.why/.effect/.who/.who_pct/.effort`; `plan.the_one_thing.action` | `ready` / `top` (one row emphasised with a 3px left rule and `The one thing` pill) / `isdone` (checkmark, text at 60% with strikethrough **only** on the time) | `today: []` → `No actions for today.` — a legitimate state (clean day), not an error. |
| `mark done` per row | Turns a plan into a record | local `saans.done.v1`, key = `time|action` slug | `off` / `on` / persisted-across-reload | — |
| Limit paragraph | Honesty: what the model cannot see | `plan.limit`, `plan.dropped` (count) | `ready` / absent | If `dropped > 0`, one line: `3 sentences were removed because they carried a number we could not verify.` |
| Error / timeout | §5 | — | — | — |

### R8 · People — `Who carries it`

**Purpose:** answer *who pays for this*. Four people in one flat breathe different air; this
is the only surface that shows the distribution rather than the average.

| Sub-component | Data | States | Absent |
|---|---|---|---|
| Person card ×N (button, `aria-pressed`) | `p.name`, `p.age`, `p.conditions`, `p.dose_ug`, `p.attributed_risk_share` | `ready` / `selected` (2px focus ring + `sel`) / `loading` (name + `—`) | `dose_ug` null → `— µg/day`, card still focusable, detail explains why. |
| Detail panel (one at a time) | `p.blocks[].place/.hours/.pm25/.dose_ug` | `collapsed` / `open` / `open-empty` (`No hour-by-hour breakdown for this person.`) | Panel hidden; card remains. |
| Note | static | — | — |

### R9 · Ledger — `Every option, by dose removed per rupee`

**Purpose:** the audit surface. Every option with its arithmetic, cost and band, for the user
who wants to check the ranking instead of trusting it — and the only place `/api/simulate`
is reachable.

14 rows, each a button that reveals the full arithmetic and a `Simulate` control.
Data: `brief.ranked[]` (all fields) plus per-row `/api/simulate`. States: `collapsed` /
`expanded` / `simulating` (row-level `Working it out…`, other rows stay interactive) /
`simulated` / `error` (row-level line). Absent: `cost_inr` null → `no cost` not `₹0`.

### R10 · Footer — provenance strip

**Purpose:** provenance, and the two doors out of the reading (Sources, Your household).

Three spans: `Air: Open-Meteo/CAMS · 06:40`, model name from `/api/health`, and two
buttons: `The arithmetic and its sources` (opens S2) and `Your household` (opens S1).

### S1 · Setup sheet — `Your household`

Three steps in one `<dialog>`, 100dvh on mobile, 560px max on desktop.

| Step | Question | Controls | Data written |
|---|---|---|---|
| 1 | `Who lives here?` | 1–12 person rows: name (text, 24ch), age (number, stepper), condition (select: none / asthma / copd / heart / diabetes), pregnant (checkbox) | `household.people[]` |
| 2 | `How do you cook?` | Fuel: `LPG · PNG · Biomass · Kerosene · Electric`; exhaust: `Chimney · Exhaust fan · Window · None` | `household.fuel`, `household.chimney` |
| 3 | `How do you get around?` | `Two-wheeler · Car · Bus/metro · Walk/cycle · Mostly indoors` | `household.commute` |
| — | Location | Place search via `/api/geocode` → `results[].name/.lat/.lon` | `household.lat/lon` |
| Footer | — | `Save and re-run` (primary) · `Just show me today` (ghost) | `saans.household.v1` |

States: `step` 1–3 with a 3-segment progress rail; `saving` (button label
`Recomputing your day…`, disabled, 800ms typical); `error` (`Saved on this phone, but the
new numbers did not load.` + `Try again` — the save is local and must never be reported
as failed because the network failed).

### S2 · Sources sheet — `The arithmetic and its sources`

`/api/factors` → 12 groups × 56 constants (`name`, `value`, `unit`, `kind`:
measured/literature/standard/estimate, `source`, `url`), plus a "what this model cannot
see" paragraph. States: `loading` (group headers + `—`), `ready`, `error`, `stale` (cached
from the last successful load, labelled `Cached · 2 days old`). This is the only place in
the app with `<a>` elements.

---

## 4. Primary workflows

Each step names the **exact UI response**, not the intent.

### (a) First-ever open — no `saans.household.v1`, no picks, no theme

1. Page paints in ≤200ms: masthead `Delhi ▾` · `● 06:40` · `Dark`; kicker
   `DELHI · PM2.5 · AQI 322`; `h1` = `Reading the air…`; ladder present with `—`;
   chart present as 24 flat bars; bench header `What could you change?` and three ghost
   rows; plan region shows its skeleton status. **Nothing is blank and nothing is
   replaced later at a different height.**
2. `POST /api/brief` with `DEFAULTS`. ~1.8s. The `h1` swaps in place to
   `Amma takes in 1,791 µg today. Most of it is your own kitchen.` Do-now strip appears
   (`Shut the windows. Open at 12:00. −18% today`). Ladder fills. Chart draws in
   (`prefers-reduced-motion` → instant).
3. **Setup sheet opens** via `showModal()` 600ms after the brief lands (not before — the
   user must see the page succeed first), `replaceState` so back exits the app. Step 1 is
   **pre-filled with the example family**: `Anil 41 · Meera 38 · Aarav 7 · Amma 68
   (heart)`. Primary button reads `Continue` and is enabled.
4. A first-run-only line above the steps: `These four are an example family. Change the
   names, or skip and use them as-is.`
5. `Just show me today` in the sheet footer closes it and sets
   `saans.example=true`. The page then shows a persistent 36px amber strip under the
   masthead: `Using an example family. Your numbers will be wrong. Set up yours →`.
6. The plan begins streaming at load regardless (it was requested in step 2's wake). If
   the user is still in the sheet at 90s, nothing is lost: the plan is rendered behind it.
7. On `Save and re-run`, the sheet closes via `history.back()`, focus returns to
   `Your household` in the footer, a 2.4s toast at the bottom reads
   `Numbers updated for 4 people.` (`aria-live="polite"`), and `brief` + `plan` refetch.

### (b) Daily check-in, 06:40, returning user, one thumb

1. Cold open. localStorage restores household, theme, picks, done markers. The `h1`,
   ladder, and chart are correct on first `/api/brief` (~1.5s warm cache).
2. Above the fold in this order: `AQI 322` → `Amma takes in 1,791 µg today. Most of it is
   your own kitchen.` → `Do now · Shut the windows. Open at 12:00.` → ladder →
   chart with the cursor already parked on `06:40`.
3. **Decision A (2 seconds):** act now or not. The `h1` and the strip answer it.
4. **Decision B (5 seconds):** *when* to ventilate. The user drags the chart to 12:00.
   Readout: `12:00 · outside 96.2 · inside 58.1 · cleanest hour`. The aside already said
   `low 12:00`; the drag confirms it. The do-now strip's second clause is a button:
   `Set a 12:00 reminder` → no notification permission exists in this build, so the
   button is **not** rendered. Instead the strip ends with `Open at 12:00.` and nothing
   pretends to remind.
5. **Decision C (10 seconds, optional):** tick `Run the exhaust fan while cooking`
   (`−6.1% · best for Amma · ₹0`). Tally fires after a 180ms debounce:
   `−6.1% · 6,283 → 5,899 µg a day`. The per-person bars show Amma's bar drop the most.
6. Scroll one flick. Two done-markers from yesterday are struck through. The user taps
   `mark done` on `Shut the windows before 07:00` → becomes `done ✓`, `aria-pressed=true`.
7. Leaves. Total time 25–40s, no sheet, no wait, no scroll past 900px.

### (c) "What if I change this" — exploring

1. From the bench, tap a 4th option inside `All 14 options`:
   `Replace the LPG stove with induction · −11.8% · ₹4,200`.
2. Row goes `on` immediately (optimistic); `pickCount` reads `4 chosen`; tally enters
   `loading` and shows the **previous** percentage at 45% opacity with `Working it out…`
   beneath — never a blank where a number was.
3. ~600ms. `−23.4% · 6,283 → 4,813 µg a day · from 3.4 to 2.6 cigarettes' worth`.
   Band line: `band 18–27% · ₹4,200 to set up · ₹1,900/yr`.
4. Because ≥2 picks, the overlap row appears: `One at a time these would claim 26.9%;
   together they give 23.4%. They overlap by 3.5 points, because each is worth less once
   the other is in place.`
5. A 5th pick that contradicts the 4th (both `fuel`) returns `conflicts`: `These cannot
   both be true: household.fuel. Kept the first.` The offending row is *not* silently
   unticked — it stays ticked with a 2px warning rule and `not counted` in its meta, so
   the user can see what the app refused and untick it.
6. User taps `Clear`. Tally returns to `Nothing chosen yet.` in one frame; picks are
   cleared from localStorage in the same tick.
7. The plan does **not** regenerate on every tick. Instead the plan card gains one line at
   its top: `You changed 3 things — −23.4%. That is your plan; the five below are the
   defaults.` (§8, ALT-6.)

### (d) Setting up a household for the first time (non-first-run)

1. Trigger: `Your household` in the footer, or the `Set up yours →` strip, or the place
   chip. Sheet opens with a 120ms fade, focus lands on `Who lives here?`'s `h2`.
2. Person rows are prefilled from localStorage or `DEFAULTS`. `+ Add a person` appends
   `Person 5, age 30, no condition` and focuses the name input, selecting its text so a
   keystroke replaces it.
3. Removing a person: a `Remove` button inside each row after the first, 44px, with
   `aria-label="Remove Amma"`. No confirmation dialog — the whole sheet is cancellable
   and the save is explicit.
4. Age input: `inputmode="numeric"`, `min=0 max=110`, stepper buttons ±1 at 44px. Typing
   `6` then leaving the field does not silently become `06`.
5. Step 2 has a live consequence line under the fuel radios, updating on selection:
   biomass → `A biomass chulha puts about 180 µg/m³ in the room you cook in.`
   LPG → `An LPG flame with no chimney still adds about 91 µg/m³ where you stand.`
6. Step 3 sets `commute`. Two-wheeler → `A two-wheeler commute is roughly 1.6× the
   roadside concentration for the minutes you ride.`
7. Location: typing 3+ characters calls `/api/geocode` after 300ms. Results in a
   `role="listbox"`; arrow keys move the active option; `Enter` selects; the input's
   `aria-activedescendant` follows. No results → `No place called “Dwarka Sec 23”. Try
   the district name.`
8. `Save and re-run` → button label `Recomputing your day…`, disabled. On success:
   sheet closes, toast `Numbers updated for 4 people.`, `brief` refetches, **and the old
   numbers stay on screen at 55% opacity until the new ones arrive** — never a blank page
   for a re-run.
9. If the refetch fails: toast `Your household is saved. The new numbers did not load.`
   plus a `Try again` in the same toast. The old numbers return to full opacity with a
   `stale` marker `As of 06:41 · before your edit`.

### (e) The household burns biomass

This is a different product for this household and the UI must say so within one screen.

1. `household.fuel = "biomass"`. `brief.kitchen_pm25` ≈ 180. The ladder's third rung is no
   longer smaller than the second — it is the largest number on the page:
   `Outside 205.4 · Inside 158.7 · **Your chulha 180.0** · Amma 3,940 µg a day`.
2. The `h1` changes subject: `The chulha is the biggest source you control. Amma takes in
   3,940 µg a day.` — attribution first, blame nowhere. Copy rule enforced: no `should`,
   no `why don't you`, no `harmful`.
3. The do-now strip's primary becomes the *free* action, never the expensive one:
   `Cook with the window open and the fan on. −9.4% today.` If `exhaust = none`, the
   second clause is `No chimney — a window and a fan still cut it.`
4. The bench's first three, by construction of `dose removed per rupee`, are the cheap
   ones: `Cook outside or on a balcony when you can · −12.1% · ₹0`,
   `Box fan with a cloth filter · −8.8% · ₹800`, `Switch to LPG · −31.2% · ₹4,200 +
   ₹900/yr`. **The expensive option never occupies the first slot** even though it has the
   largest percentage — ranking is dose-per-rupee, and the UI must not re-sort by pct.
5. Cost is printed as a range when uncertain: `₹800–1,200`, never a bare point estimate.
6. The evidence drawer, opened from the `180` rung, states the constant's `kind`
   (`literature`) and that it is not a measurement of *their* kitchen.
7. No shame surfaces: the plan's opening is checked against the banned-phrase list; the
   `limit` paragraph is the only place the word `biomass` may be repeated.

---

## 5. States, exhaustively

### 5.1 The state matrix

| Surface | loading | ready | empty | error | stale | partial |
|---|---|---|---|---|---|---|
| `/api/brief` | Labels + `—` everywhere, `Reading the air…` as `h1`, ghost bench rows | Full render | n/a (a household always yields numbers) | `h1` = `Could not read the air.` + `Try again`; ladder/chart/bench collapsed to zero height; masthead dot hollow | Brief older than 45 min → 28px bar under the masthead: `Air data from 06:40. It is now 07:31.` + `Refresh` | Some hours missing → chart draws those as baseline gaps; aside reads `partial` |
| `/api/plan` | See §5.2 — the whole point | Prose + figures + rail | `today: []` → `No actions for today. Nothing here needs changing.` | Figures stay; prose slot shows `The wording did not arrive. Your numbers are unchanged.` + `Try the wording again` | Plan older than the brief's household (user edited, plan not refetched) → plan header gets `for the previous household` and a `Rebuild` button | `plan.figures` < 5 → cells omitted; `opening` present but `today` empty → prose + `No actions.` |
| `/api/combine` | Tally shows previous value at 45% + `Working it out…` | Value + band + overlap + per-person | `Nothing chosen yet.` | `Could not work that out. The numbers above are unchanged.` + `Try again`; picks stay | Result for a stale household (edited since) → `Recalculate` chip on the tally | `per_person` missing → headline % only; `band_pct` missing → band line shows cost only |
| `/api/simulate` (ledger row) | Row-level `Working it out…`, 400ms, other rows interactive | Before → after + band | — | Row-level `Could not simulate this one.` | — | `per_person` missing → household delta only |
| `/api/geocode` | 3 dots in the results list | Listbox | `No place called “X”. Try the district name.` | `Search is not available. You can still use the current location.` | — | < 3 results → list renders what exists, no "more" affordance |
| `/api/factors` | 12 group headers + `—` | Table | — | `The sources did not load.` + `Try again` | `Cached · 2 days old` | Fewer groups than 12 → render present groups, no gaps |
| `/api/health` | Silent | Dot filled | — | Dot hollow, no copy | > 10 min → hollow | — |
| localStorage | n/a | Read on boot | First run → sheet | Corrupt JSON → **discard silently, boot with `DEFAULTS`, and set `saans.example=true`** so the user is told the numbers are an example rather than shown a crash | — | Household present but `people: []` → treated as first run |
| Offline | — | — | — | Global 38px bar under masthead: `Offline. Showing 06:40.` + `Retry`; all values dim to 70%; every action still works on cached brief | — | — |

### 5.2 The 30–90 second plan — the single worst wait, solved

**Governing principle: the plan's *content* is available in 40ms; only its *wording* is
slow.** Never show a spinner for something whose substance you already have. The panel is
therefore fully populated with the five actions, times, effects, and the one marked
action before a single token arrives. What the 4B model adds is three paragraphs of
register — genuinely valuable, and never allowed to be load-bearing.

Placement: the plan region sits directly under the bench, and while streaming its header
is **duplicated as a 40px sticky status strip at the bottom of the viewport** on mobile
(`Writing your plan · 12s`), so a user who scrolls away from it still knows it is
happening. The strip is `aria-live="off"`; only milestones are announced.

#### Timeline

**0s — the panel exists, complete.**
Rendered synchronously from the `brief` already in memory:

```
Today's plan                                   from your numbers
────────────────────────────────────────────────────────────────
 06:40  Shut the windows before cooking                     −18%
 07:00  Run the exhaust fan for 30 minutes                  −6.1%
 12:00  Open the east windows for 40 minutes              −11.2%
 18:30  Keep the bedroom door shut while cooking            −4.0%
 21:00  Run the fan for 20 minutes before bed               −3.1%
────────────────────────────────────────────────────────────────
Drafting the wording · 0s          ▓░░░░░░░░░░░░░░░░░░░░░░
```

The five rows carry a **dotted left rule** and the header reads `from your numbers`,
signalling provisional but true. No shimmer, no skeleton grey — the rows are real text
from `brief.ranked`, and they will not move when the plan lands (same source, same order).

**0–75s — the progress rail.** A single 2px rail under the panel fills
`92 × (1 − e^(−t/26))` percent: 10% at 3s, 40% at 15s, 63% at 30s, 83% at 60s, 89% at 90s.
It is asymptotic to 92 and never reaches it, so the bar can never complete before the text
does.
It **never resets and never loops**. A looping indeterminate bar is a lie about progress
and, on a 90s wait, reads as a hang. The elapsed seconds are printed beside it
(`· 12s`) because a number that increases is the cheapest proof of life available.

**3s — first tokens.**
The moment the first SSE `token` arrives (§5.4), the status line changes to
`Writing · 2 of 3` and text begins to appear in the prose slot at a **capped reveal of
45 characters/second**, which is slower than the model emits. The cap is deliberate: it
converts a stuttery token drip into a legible typewriter, and it means the last token
never lands before the eye. A 2px caret (`▍`) blinks at 1Hz. The five rows and figures
stay exactly where they are; only the prose slot grows, and its box has
`min-height: 3 lines` reserved from 0s so **there is no layout shift**.

If tokens arrive *before* 3s, this state is simply reached earlier — the timeline is a
floor, not a schedule.

**15s — the honesty line.**
If no token has arrived by 15s, the status gains a second line:
`Still working. The numbers above are final; only the wording is waiting.`
and a `Read the numbers instead` button appears, which collapses the prose slot to zero
and expands the figures strip. This is a real escape hatch: a user who does not care about
prose gets a complete plan at 15s and stops paying for the wait.

**60s — the second honesty line, and the local fallback.**
Status reads `This can take up to 90 seconds on a household device.` and a new button
appears: `Skip the wording`. Pressing it — or reaching **100s** without a `plan` event —
renders the **local deterministic plan** built from the `brief` already in memory: the same
five actions, `planby` reads `built-in wording`, and the prose slot shows the three
sentences the server would have templated (the client already holds every figure needed).
The SSE request is aborted. This state is **indistinguishable in content** from success,
only in attribution — which is exactly what `generated_by: "deterministic"` already means
server-side.

**Failure — any non-2xx, network drop, or timeout.**
The figures, five rows, done markers and one-thing marker are **untouched**. Only the
prose slot changes, to:

```
The wording did not arrive. Everything above is still your numbers.
                                                    [ Try the wording again ]
```

One line, muted, 13px, no icon, no red — a failed paragraph is not an error state for the
product. `Try the wording again` re-POSTs `/api/plan` and returns to 0s with the *same*
five rows (idempotent by construction). A second failure prints
`Still no wording. The numbers are the plan.` and removes the retry, so the UI cannot
become a retry loop.

#### 5.3 What must never happen during the wait

| Anti-pattern | Why it is banned here |
|---|---|
| Full-panel spinner | Replaces content the client already has with nothing. |
| Skeleton grey boxes in the shape of prose | Promises a paragraph of a specific length, then shifts when the real one is shorter. |
| Indeterminate looping bar | Lies about progress on a 90s wait; reads as a freeze. |
| "Estimated time remaining" | The model has no honest ETA; a wrong number is worse than a counter. |
| Blocking the bench until the plan arrives | Inverts the product: the user can act at 0s. |
| Token-by-token into an `aria-live` region | Floods a screen reader with 400 announcements. Prose streams into a plain region; only `Plan ready` / `The wording did not arrive` are announced. |
| Auto-scrolling to the plan | Steals the user's position mid-read. The sticky status strip is the notification. |

#### 5.4 Three client changes and one optional server field

The current client keeps only SSE events carrying `today` and **discards every `token`
chunk** (`index.html`, the `if (obj && obj.today) finalObj = obj;` line). The fix is three
changes, two of them purely client-side:

1. On `token`: append `obj.text` (or the chunk's field) to the prose buffer, honouring the
   45 char/s cap.
2. On `facts`: if it carries the five actions and times, replace the provisional rows with
   them. **NEW FIELD (optional, 0.5 day):** have the server put `today: [{time, action,
   effect, who}]` into the `facts` event. Without it, the client derives the same five
   from `brief.ranked`; the UI is correct either way, so this is an optimisation, not a
   dependency.
3. On `plan`: reconcile — if the server's action strings differ from the provisional
   ones, cross-fade the row text over 160ms rather than swapping instantly, so the change
   is perceivable but not jarring.

---

## 6. Wireframes

390px viewport ≈ **74 monospace columns** at 13px (5.13px/char), i.e. the boxes below are
≈380px wide. They are drawn to that scale. Real content, real numbers: outdoor 205.4,
indoors 123.4, stove 91.3, Amma 1,791 µg, AQI 322, low 12:00, peak 23:00.

### 6.1 The fold — 740px on a real Android (844 emulated)

```
┌────────────────────────────────────────────────────────────────────────┐ 0
│ Delhi ▾        ● 06:40                              Dark    · Today    │ 44
├────────────────────────────────────────────────────────────────────────┤
│ DELHI · PM2.5 · AQI 322                                                │ 70
│                                                                        │
│ Amma takes in 1,791 µg today.                                          │
│ Most of it is your own kitchen.                                        │ 138
│                                                                        │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ DO NOW    Shut the windows till 12:00.            −18% today       │ │ 202
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ Outside                    205.4  ██████████████████████████████       │
│ Inside                     123.4  ██████████████████                   │
│ Your kitchen                91.3  █████████████                        │
│ Amma              1,791 µg a day · 28.5% of the household dose         │
│                                                                        │ 358
│ Next 24 hours              AQI 322 · low 12:00 · peak 23:00            │
│                                                                        │
│  ▁▁▂▃▅▇█▇▆▅▄▃▂▁▁▂▃▄▆▇█▇▅▃                                              │
│  ░░░░▒▒▒▓▓▓▓▓▒▒░░░░░░▒▒▓▓▓                                             │
│  ┊        ▲                                                            │
│ 06  09  12  15  18  21  00  03                                         │
│                                                                        │ 594
│ 06:40 · outside 198.2 · inside 121.7 · not the cleanest hour           │
│                                                                        │
│ What could you change?                                                 │ 642
│ Tick anything you could actually do.                                   │
│                                                                        │
│ ☐ Cook with the window open and the fan on          −12%     ₹0        │
╭─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ 740px · real Android fold ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─╮
│ ☐ Box fan with a cloth filter                        −9%   ₹800        │
└────────────────────────────────────────────────────────────────────────┘ 844
```

The dashed rule is where the fold actually lands on a cold phone: the bench header and
one whole pick row are visible, the second row is not. The user has seen a checkbox they
can press before they have scrolled once.

Reading of the fold, left to right, top to bottom: *whose air → what to do now → where it
comes from → when it turns → this is changeable*.

### 6.2 The plan arriving — t = 15s, first tokens, five rows provisional

```
┌────────────────────────────────────────────────────────────────────────┐
│ Delhi ▾        ● 06:40                              Dark   · Your plan │
├────────────────────────────────────────────────────────────────────────┤
│ Today's plan                                     from your numbers     │
│                                                                        │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Amma carries 28.5% of the household's dose, and the                │ │
│ │ largest share of it comes from the hour you cook▍                  │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  6,283 µg   1,791 µg    91.3    205.4    −18%                          │
│  household  Amma        kitchen outdoor  today                         │
│ ────────────────────────────────────────────────────────────────────── │
│ 06:40  Shut the windows before cooking                        −18%     │
│        The morning peak is outside, not in.                            │
│ 07:00  Run the exhaust fan for 30 minutes                    −6.1%     │
│        Best for Amma at 41%                                            │
│ 12:00  Open the east windows for 40 minutes                 −11.2%     │
│        Cleanest hour of the day.                                       │
│ 18:30  Keep the bedroom door shut while cooking              −4.0%     │
│ 21:00  Run the fan for 20 minutes before bed                 −3.1%     │
│ ────────────────────────────────────────────────────────────────────── │
│ Writing · 2 of 3                                                       │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░ 15s                   │
│ Still working. The numbers above are final; only the wording waits.    │
│                         [ Read the numbers instead ]                   │
└────────────────────────────────────────────────────────────────────────┘
```

Top row of the plan region is the *prose that does not exist yet*, holding a reserved
3-line box from 0s. The figures strip and the action rail never move.

### 6.3 The bench — 3 visible, 14 available, tally live

```
┌────────────────────────────────────────────────────────────────────────┐
│ What could you change?                                                 │
│ Tick anything you could actually do.                                   │
│                                                                        │
│ ☑ Cook with the window open and the fan on          −12%     ₹0        │
│   best for Amma · free                                                 │
│ ☑ Run the exhaust fan while cooking                −6.1%     ₹0        │
│   best for Amma · free                                                 │
│ ☐ Shut the windows at 18:00                         −4%      ₹0        │
│   free                                                                 │
│                                                                        │
│ ▸ All 14 options                                        +11 more       │
│ ────────────────────────────────────────────────────────────────────── │
│ Your household                                       3 chosen          │
│                                                                        │
│  −18.1%                                                                │
│  Household dose 6,283 → 5,146 µg a day                                 │
│  from 3.4 to 2.8 cigarettes' worth                                     │
│  band 15–21% · ₹0 to set up                                            │
│                                                                        │
│  One at a time these would claim 22.1%; together they                  │
│  give 18.1%. They overlap by 4.0 points, because each is               │
│  worth less once the other is in place.                                │
│                                                                        │
│  Anil    −17%  ███████████████░░░                                      │
│  Meera   −16%  ██████████████░░░░                                      │
│  Aarav   −19%  ████████████████░░                                      │
│  Amma    −24%  ███████████████████                                     │
│                                                                        │
│  [ Clear ]                                                             │
└────────────────────────────────────────────────────────────────────────┘
```

Note the honesty row: `−18.1%` is **less than** the naive `−12 − 6.1` because the app
computes the overlap. The UI must never print a sum the engine did not produce — that
single decision is most of the product's credibility.

---

## 7. Interaction patterns

### 7.1 Selection

| Rule | Value |
|---|---|
| Control | `<button role="button" aria-pressed="true|false">`. Never a custom div, never a checkbox input (styling a native checkbox across 3 Android WebView versions is a losing battle; `aria-pressed` carries the same semantics). |
| Target | Whole row, 44px minimum height, 358px wide. The checkbox glyph is decoration and is `aria-hidden`. |
| Response | Optimistic and instant: the glyph fills and `aria-pressed` flips in the same frame as the tap. There is no "saving" state on a toggle. |
| Recompute | Debounced **180ms** after the last tap. Rapid ticking of three options fires one `POST /api/combine`, not three. |
| Race | Monotonic `combineToken`; a response whose token is not the latest is discarded silently. Without this, ticking fast leaves the tally showing the result of an earlier selection — the most common bug in this class of UI. |
| Tally during load | The previous value stays, dimmed to 45%, with `Working it out…`. It is never zeroed. |
| Deselect | Identical path. `Clear` empties the array in one tick and repaints the empty state synchronously — no request. |
| Conflicting picks | Not auto-removed. The row is marked `not counted` with a warning rule and the conflict line names the field (`household.fuel`). Silently undoing a user's tap is worse than explaining a refusal. |
| Persistence | `saans.picks.v1` written on every change. But picks whose `key` no longer exists in a fresh `ranked` are dropped on next brief (the household may have changed fuel). |

### 7.2 The scrubber

| Rule | Value |
|---|---|
| Hit area | The entire 358×140 plot + 16px axis band. Not a 12px thumb. |
| Pointer | `pointerdown` → `setPointerCapture` → `pointermove` maps x to hour with `floor((x/358)*24)`, clamped 0–23. Works identically for touch, pen, mouse. |
| Threshold | No drag threshold. A tap anywhere on the plot jumps to that hour. There is no hover-only preview. |
| Visual | 1px vertical rule + a 6px caret at the top; no animation on move (a tween would lag the finger). |
| Readout | Updates on every move, but the `aria-live` region is **throttled to 120ms** and only fires on hour *change*, not pixel change. |
| Keyboard | Container `tabindex="0"`, `role="slider"`, `aria-valuemin=0`, `aria-valuemax=23`, `aria-valuenow=HOUR`, `aria-valuetext="12:00, 96.2 micrograms outdoor, 58.1 indoors, cleanest hour"`. `←/→` ±1, `PageUp/PageDown` ±6, `Home` 0, `End` 23. |
| Initial position | Current hour, not hour 0. The cursor sits at 06:40 on open. |
| Coupling to the verdict | The verdict's `next_trough` copy does **not** follow the scrubber. Dragging is exploration; the `h1` is today's standing advice and must not chase the finger. The readout is where exploration lives. |
| Labelling | The aside `AQI 322 · low 12:00 · peak 23:00` is the always-visible summary so a user who never drags still gets the timing answer. |

### 7.3 Done markers

| Rule | Value |
|---|---|
| Control | `<button aria-pressed>` inside the action row's footer, label `mark done` → `done ✓`. |
| Effect | Local only. No request, no sync, no account. `saans.done.v1` maps `actionKey → 1`, where `actionKey = (time|action).toLowerCase().replace(/[^a-z0-9]+/g,'-').slice(0,48)`. |
| Appearance when done | The row's time is struck through at 60% opacity; the action text stays fully legible. Struck-through body text is an accessibility failure — the user still needs to read what they did. |
| Expiry | Cleared at **04:00 local**, not midnight. The engine's day runs cooking-to-cooking; resetting at midnight would erase a `21:00` action four hours after it was done and before the morning read. A stored `saans.done.day` stamp compares against `now - 4h`. |
| Reversal | Same button toggles back. No confirmation. |
| Copy | Never `completed`, never a percentage ring. One word and a mark. |

### 7.4 Focus order

Tab sequence, top to bottom, skipping anything `aria-hidden`:

1. `Skip to today's numbers` (visible on focus, 44px, top-left) → `#main`
2. Place chip → Theme toggle → Chapter label (the region-menu button; `hidden` at scroll
   0, so it enters the order only after the first scroll, in the position it occupies)
3. Chart slider (`role=slider`)
4. `What could you change?` — each pick button in DOM order, then `All 14 options`, then
   the tally's `Clear`
5. Plan: `Read the numbers instead` / `Skip the wording` (when present), then each
   `mark done`, then `Try the wording again` (on failure)
6. Person cards → the open detail's `Close`
7. Ledger rows (buttons) → each expanded row's `Simulate`
8. Footer: `The arithmetic and its sources` → `Your household`

Focus is never moved by data arriving. A response that lands while the user is typing or
tabbing must not steal focus — this is why the plan never auto-scrolls and the toast is
not focusable.

**Rejected: roving tabindex on the 14 picks.** It saves 11 tab stops and costs screen
reader users the ability to hear the full option set with `Tab` alone. A toggle group is
not a listbox; `Tab` through each is the predictable behaviour, and a `Skip the list` link
after the third row recovers the cost for keyboard-only users.

### 7.5 Button vs link

| Looks like | Is a | Why |
|---|---|---|
| Any state change in place (pick, done, theme, clear, retry, expand) | `<button>` | No navigation, no URL, no history. |
| Any in-page jump (chapter menu, `Your household` in the footer) | `<button>` + `scrollIntoView` | A fragment `<a>` creates a history entry and breaks §2.4. |
| Opening a sheet | `<button>` | It changes the document's modal state, not its location — though it *does* push a history entry, handled in JS. |
| A source citation (56 of them, in S2) | `<a href>` `target="_blank" rel="noopener noreferrer"` | The only real navigation in the product. |
| `Skip to today's numbers` | `<a href="#main">` — **the one exception** | Skip links are the canonical fragment use; the history entry it creates is the browser's expected behaviour and is consumed by the next scroll. |

That is the complete inventory: **56 links, 1 skip link, and everything else is a button.**

### 7.6 Accessible names and live regions

- Exactly **three** `aria-live` regions: `#readout` (polite), `#tally` (polite), and one
  hidden `#announce` (polite) for milestones. The plan prose is **not** live.
- Milestones announced: `Plan ready.` / `The wording did not arrive. Figures shown.` /
  `Numbers updated for 4 people.` Nothing else.
- Every icon-only control has a text alternative; there are no icon-only controls except
  the theme toggle, which has `aria-label="Switch to light appearance"`.
- `prefers-contrast: more` → all `--muted` text darkens to the body colour, all rules go
  to 1px solid at `--rule2`, and the ladder's bar fills gain a 1px outline so they are
  distinguishable without colour.
- `prefers-reduced-motion: reduce` → no smooth scroll, no caret blink (static `▍`), no
  cross-fade, no typewriter cap (text appears in full chunks; motion is the problem, not
  latency).

---

## 8. What I rejected, and why

### ALT-1 · Tabs / bottom navigation (`Today · Plan · Act · Home`)

**Loses on:** the comparison. The bench's entire persuasive mechanism is watching the
household number fall while the ladder is still visible above it. Tabs put the ladder and
the tally in different rooms. Secondary losses: the back button becomes either a history
walk through tabs the user never navigated or an app exit from a page they believe they
are on — unfixable without a router, and a router is 4KB of state machine that this
product does not need. Also 56px of a 740px viewport permanently spent to navigate six
screens. Rejected.

### ALT-2 · A wizard (Step 1 of 3 → your result → your plan)

**Loses on:** the honesty that is the product. A wizard promises "answer these and we will
tell you your family's risk" before it has computed anything, then delivers a number whose
entire credibility rests on showing its working. Wizards also make every return visit
re-enter the flow — fatal for a daily 06:40 check-in, which is the only retention
mechanism this app can have under a no-service-worker constraint. And it hides the
example household, so the first-run user cannot see a *working* product before being asked
for input. Rejected — replaced by one auto-opened sheet over an already-rendered page.

### ALT-3 · A card feed / dashboard grid (the city-AQI-app pattern)

**Loses on:** equal weight. A grid says these six things are equally important; they are
not. The chain street → room → kitchen → person is a *ranked causal* relation, and a
2-column grid at 390px destroys both the ranking and the relation. It also trains scanning
rather than deciding, which is precisely the failure of the apps Saans is positioned
against. Rejected.

### ALT-4 · Chat-first ("ask about your air")

**Loses on:** latency and truth. The numbers are computed by Python; a chat box invites
questions the engine cannot answer (school policy, tomorrow, "is my landlord liable"), and
each turn would cost 30–90s on a 4B local model. A single misfire destroys the credibility
that took 56 sourced constants to build. Chat is also the worst possible surface for a
90-second wait: a blank bubble with three dots. Rejected.

### ALT-5 · Sheet-per-section (an iOS-style stack of modals)

**Loses on:** the back stack. Nested `<dialog>`s opened from a page with no router produce
a history stack that no longer corresponds to what the user sees after a reload, a
deep-link, or a mid-sheet refresh. It also cannot show the chart and the bench
simultaneously, which is requirement zero. Rejected — sheets are used for exactly two
tasks that are genuinely modal, and nowhere else.

### ALT-6 · "Regenerate the plan on every tick"

**Loses on:** 90 seconds per tap. The tempting way to fix "bench and plan are
disconnected" is to re-run the LLM for the user's selection. It would make the bench feel
like a slot machine with a 90s spin. Rejected in favour of a one-line bridge: the tally is
authoritative for *your* selection, the plan is explicitly *the defaults, worded*, and the
plan card says so in one sentence when picks exist.

### ALT-7 · A separate "results" view for the plan, opened on completion

**Loses on:** interruption. Pushing a new view when a background job finishes moves the
page under a user who is reading the bench, and it is the classic way AI features feel
possessed. Rejected — the plan lives where it will live forever, fills in place, and
announces itself once.

---

## 9. Friction budget

**Cost index** = seconds lost on the critical path, multiplied by abandonment risk (1–5)
and by how often the friction recurs. It is an ordinal, not a measurement — it exists to
rank, and the ranking is the argument. Abandonment is weighted heaviest because an
abandoned first visit has no second visit, which is the only visit this app can rely on.

| # | Friction | Time lost | Risk | Cost | Who pays |
|---|---|---|---|---|---|
| 1 | Plan takes 30–90s with a static "Reading your numbers" and the stream discarded | 30–90s | 4 | **102–190** | Every visit |
| 2 | Household editor is the last section; zero-state is indistinguishable from configured | 20–60s (or never) | 5 | **75–180** | First visit, and every visit after a wrong setup |
| 3 | Bench and plan are disconnected; `Show in the ledger` only scrolls | 8–15s of confusion | 3 | **33–54** | Every selection |
| 4 | "Dose" and "µg/day" are never defined in place | 10–25s | 3 | **40–85** | First visit |
| 5 | The plan is below the bench, so a user who acts first never reads it | 0 (lost content) | 2 | **20** | Every visit |
| 6 | 14 options shown at once with no applicability filter | 5–12s | 2 | **21–46** | Every exploration |
| 7 | No share/export; a family decision cannot leave the phone | 30s + a rebuild | 2 | **30** | Occasional |
| 8 | The verification surface (56 constants) is one tap from nowhere | 0–15s of hunting | 1 | **15** | Researcher only |

### The three this architecture removes

**1. The silent 90-second wait → removed by §5.2.**
Content at 0s, text at 3s, an exit at 15s, a full local fallback at 60s/100s.
*Regression risk:* **layout shift and reading churn.** Streaming prose into an
auto-height box is the classic CLS bug, and on a 740px screen a paragraph that grows
pushes the entire bench down mid-read. Mitigation is structural, not cosmetic: the prose
slot has a reserved `min-height` of 3 lines from 0s, the action rail is *below* the prose
and therefore must never reflow more than that reserve, and the reveal cap (45 char/s)
keeps the growth monotonic. The second risk is **screen-reader flooding** — solved by
keeping the prose region non-live and announcing only two milestones. The third is
**over-promising progress** — the rail is asymptotic and unlooping precisely so it can
never "finish" before the plan does.

**2. The buried, silent household editor → removed by the first-run sheet + the example-
family banner + the `Your household` button in the footer.**
*Regression risk:* **the blocking interstitial.** An auto-opened modal on first visit is
the single most reliable way to lose a mobile user, and this app's promise is "no account,
instant". Mitigations: the sheet opens *after* the page has visibly succeeded (600ms after
the brief paints), it is never empty of a default (the example family is pre-filled and
`Continue` is enabled), `Just show me today` is always visible in its footer, `Esc` and
back both dismiss it, and dismissal leaves a persistent, dismissible amber strip that keeps
the "these numbers are not yours" fact visible for as long as it is true. If the strip is
dismissed, the footer button remains the permanent affordance. The residual risk is a user
who taps `Just show me today` and never returns to set up — accepted, because a wrong
number they know is wrong is better than no number at all.

**3. Bench and plan disconnected → removed by the bridge line + the shared action keys.**
When picks exist, the plan card's first line reads
`You changed 3 things — −18.1%. That is your plan; the five below are the defaults.`
and any plan action whose key is in `picks` gains a `your pick` pill.
*Regression risk:* **two competing "plans" on one screen.** A user may read the five
defaults as their selection and act on the wrong rows. Mitigation is typographic and
unmissable: the bridge line sits above the plan's opening, the default rows keep a
muted header (`from your numbers` → `the defaults, worded`), the picked rows carry a pill,
and the tally remains the only place a *combined* percentage is printed. The second risk
is **stale reconciliation** — a pick removed after the plan rendered leaves an orphan
pill. Handled by recomputing pills from `PICKS` on every tally response, never from the
plan payload.

### Accepted, not removed

- **#5, the plan sits below the bench.** Moving it above would invert the verb: the user
  would read five instructions before learning they can choose their own. The cost is paid
  once per visit, and the sticky `Writing your plan · 12s` strip makes the plan's existence
  known from the fold. Accepted.
- **#7, no share or export.** A print stylesheet is a 20-line addition and the README
  already promises one; it is in scope for whoever implements §3, but it is not an
  information-architecture problem and this document does not solve it. Named, not fixed.
- **#8, the evidence surface.** It is one tap from the footer and one from any `kind`
  chip in the ladder. That is the correct depth for a researcher surface. Accepted.

### What this architecture deliberately does **not** fix

- **Retention.** There is still no trigger, no notification, no digest — a single-file,
  no-service-worker constraint forbids it. A better IA cannot manufacture a reason to
  return; it can only make the 25 seconds of a voluntary return cheap. This document
  optimises for that and claims nothing more.
- **The 90 seconds itself.** Local 4B inference is the cost of no cloud and no key.
  The architecture hides the wait; it does not shorten it.
- **Language.** `language` is plumbed but only `en` exists. Every string in this document
  is written to survive translation: short sentences, no idiom, no concatenation into
  grammar (`−18%` is never glued into a sentence by string concatenation; it is a
  separate span with its own label).
- **Measurement.** The app models; it does not sense. Nothing in this IA may imply a
  sensor reading. The word `measured` is reserved for `factors[].kind`, and every home
  figure carries `estimated` in its accessible name.

---

## Appendix A · Type and spacing tokens (the whole scale)

| Token | Value | Used by |
|---|---|---|
| `--fs-11` | 11/14, +0.08em, uppercase | kicker, sheet step labels |
| `--fs-12` | 12.5/16 | meta, aside, captions, rung labels |
| `--fs-13` | 13/18 | chips, status lines, body secondary |
| `--fs-15` | 15/20 | pick titles, action rows, inputs |
| `--fs-17` | 17/22 | section `h2` |
| `--fs-25` | 25/31, −0.01em | verdict `h1` |
| `--fs-34` | 34/34, tabular | the tally percentage only |
| Space | 4 / 8 / 12 / 16 / 24 | 16px page gutter; 12px between stacked cards; 24px between regions |
| Radius | 10px cards, 8px controls, 999px chips | — |
| Tap target | ≥44×44, ≥8px apart | every interactive element |

## Appendix B · Region anchors (for the chapter spine)

`#today` · `#change` (bench) · `#plan` · `#people` · `#options` (ledger) · `#sources`
(footer trigger) · and the two sheets `#setup`, `#sources-sheet`.

Chapter labels shown in the masthead, in order: `Today` → `What you can change` →
`Your plan` → `Who carries it` → `Every option`.

## Appendix C · Copy rules that constrain the UI

1. Imperative, second person, ≤ 9 words per instruction.
2. No `safe`. No `harmful`. No `should`. No future-tense claims about behaviour.
3. No moralising: the stove is a *source you control*, never a *mistake*.
4. Every number carries its unit in the same line — `1,791 µg a day`, never `1,791`.
5. A percentage is always prefixed with its direction: `−18%`, never `18%`.
6. `dose` is glossed once, in place, on the ladder's fourth rung: `µg a day is how much
   PM2.5 one person actually breathes in.`
7. Money is `₹` with a range when uncertain; `free` when `cost_inr === 0`; `no cost` when
   the field is absent — those are three different facts and must not share a string.



