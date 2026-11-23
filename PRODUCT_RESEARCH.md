# PRODUCT RESEARCH — Saans
### Agent 1: Product Discovery & UX Research
Independent UX research document. No app code was written or modified. Sources: `PRODUCT_UNDERSTANDING.md` and a full read of `saans/static/index.html` as it stood at 65,041 bytes.

Tagging convention: **[EVIDENCE]** = read in the source or observed in the markup. **[ASSUMPTION]** = inference I have not proven. Where I am unsure I say so in the sentence rather than hedging the whole document.

### Build note — read this before quoting a line number

I analysed `index.html` at **65,041 bytes**. While this document was being written, the working tree changed to **66,681 bytes (mtime 20:23:51)** — a concurrent agent fixed one of the defects below. Line numbers here refer to the revision I read; symbol names (`loadPlan()`, `verdictText()`, `.pick .pt`) are stable and should be preferred.

Status of the five known defects **in the working tree at the time of writing**:

| # | Defect | Status now |
|---|---|---|
| B2 | streamed tokens discarded | **Fixed mid-research** — see B2 for a critique of the fix |
| M7 | README claims a print stylesheet | Claim removed; `@media print` still absent (0 occurrences) |
| m6 | README test counts stale | **Fixed** — README now says 51 / 43 |
| B1 | zero-state indistinguishable from configured | **Still present** — no banner, no chip, no demo flag |
| m1 | `/api/ambient`, `/api/sources` unused | **Still present** — zero references in the client |

The document keeps all five in place, because a severity-ordered audit that deletes a fixed item loses the reasoning that produced the fix. Each entry states which build it describes.

---

## 1. What the product is and does

Saans is a one-page web app that answers a question a city AQI app cannot: **how much fine particulate matter each person in one household actually breathes in a day, and what would change it.**

The page opens on a verdict written as an instruction — *"Keep them shut until about 06:00"* (`#verdict`, 27–38px serif) — over a four-rung ladder (`#ladder`) that walks the chain the engine computes: **outdoor → indoors → at the stove → breathed today**, in µg/m³ for the first three and µg/day for the last. **[EVIDENCE — `renderLadder()`, lines 493–530]** Beside it is a 24-hour bar chart (`#plot`) with an outdoor bar and an indoor bar per hour, a draggable cursor, and a readout (`#readout`) that updates as you scrub. **[EVIDENCE — `#plotwrap` is `role="slider"`, `aria-valuemin=0`, `aria-valuemax=23`]**

Below that is the only real verb on the page: **"Build your plan"** — a 14-row tick list (`#picks`) of interventions, and beside it a sticky tally (`#tally`) that shows household percentage cut, the µg before→after, a band, cost in rupees, an overlap note, and per-person bars. Ticking a row does not add percentages; it re-runs the whole day via `POST /api/combine`, because two actions on the same source are worth less together than alone. **[EVIDENCE — bench copy, line 337: "The combination is re-run, not added up"]**

Then a generated plan (`#plan`): an opening paragraph, five figures, a paragraph for children, actions on a time rail with the top one marked, and an honest limit. A local 4B model writes the prose; Python decides every action, time, order, cost and figure, and any sentence carrying a numeral the model was not given is deleted and the deletion is reported. **[EVIDENCE — `#planfoot` counts "sentence(s) removed for carrying a figure the model was not given"]**

Then **"Who carries it"** (`#people`): four cards, sorted by share, each with a dose in µg/day, and a tap reveals where that person's dose comes from by place. Then a full ranked ledger of all 14 options with expandable rows, then an evidence drawer of 56 constants tagged measured / literature / standard / estimate, then — folded shut at the very bottom — **"Your household"** (`#ed`). **[EVIDENCE — section order: hero 314 → bench 334 → plan 359 → people 364 → ledger 370 → evidence 375 → editor 385]**

The household editor is three steps: *who lives here* (name, age, one condition, cooks, commutes), *how you cook* (4 fuels, 4 exhaust states), *how you get around* (7 modes). Saved to `localStorage["saans.household.v1"]`. **[EVIDENCE — `renderEditor()`, `FUELS`, `EXHAUST`, `MODES`, line 976–982]**

### What is genuinely distinctive, and what is ordinary

**Distinctive, in order of how hard it is to copy:**

1. **The unit.** Not AQI, not concentration — *micrograms inhaled per person per day*. That single choice cascades: it lets the app compare a 68-year-old at the stove against a 7-year-old in a classroom, and it makes "the average" meaningless in a useful way. **[EVIDENCE]** This is a different unit of analysis, not a feature.
2. **The refusal to let effects add.** `/api/combine` re-runs the model for the combination and reports the overlap in points. **[EVIDENCE — `#overlap`: "One at a time these would claim X%; together they give Y%. They overlap by Z points."]** Almost every consumer "what-if" tool multiplies or sums. This one pays the compute cost to be honest, and then shows its work. That is rare and it is the most defensible thing in the repo.
3. **The Python-owns-the-numbers / model-owns-the-register split, with a visible deletion count.** A 4B model that is forbidden numerals, forbidden the word "safe", and whose violations are removed and *counted on screen* is a genuinely unusual piece of applied caution. **[EVIDENCE — `#planfoot`]** Rarer than the dose model, and more transferable.

**Ordinary:** the visual craft. The serif verdict, mono numerals, paper-and-ink palette, 2px radii, two themes, the sticky bar — this is competent editorial design of a kind you can buy as a template. The 24-hour scrubber is a well-executed but standard instrument. The accordion ledger, the localStorage persistence, the card grid: all conventional. **[EVIDENCE]** None of that is a moat; all of it is good taste.

**And the thing that is neither:** the app is **one-shot in its bones**. A city AQI app is a daily habit because the number changes every morning. Saans computes from a household that does not change — same fuel, same commute, same flat — so its answer is near-static across a winter, while the outdoor term moves a few percent. It is built like a daily assistant and it behaves like a diagnostic. That tension is the subject of §7 and it is the product's real problem, not its polish.

---

## 2. User personas

Grounded strictly in what the code accepts. The editor exposes **only** these fields per person: `name` (≤40 chars), `age` (0–120), one `condition` from `{none, asthma, COPD, heart disease, diabetes}`, `cooks` (bool), `commutes` (bool). Household-level: `cooking_fuel ∈ {lpg, png, biomass, electric}`, `kitchen_exhaust ∈ {none, window, fan, chimney}`, `transport.mode ∈ {two_wheeler, metro, bus, auto, car_ac, walk, wfh}`, plus a geocoded location. Up to 12 people. **[EVIDENCE — lines 976–1091]**

Note what the schema accepts but the interface does not expose: `pregnant`, `exercises`, `home.kind`, `windows_day`, `windows_night`, `cleaner`, `mixer`, `incense_per_day`, `mosquito_coil`, `dry_sweeping`, `waste_burning_kg_week`, `exercise_hour`, `cook_hours`, `cook_minutes`. All are fixed at `DEFAULTS`. **[EVIDENCE — `DEFAULTS` lines 437–451 vs `renderEditor()`]** This matters for every persona below: the model is more configurable than the product.

---

### Persona A — "The configured default": a two-earner Delhi flat with a child and a grandmother

**Who.** 34 and 33, one child aged 7, one parent aged 68 with heart disease. LPG cylinder, no chimney, two-wheeler commute, Delhi. This is literally `DEFAULTS`. **[EVIDENCE — lines 444–449, `Amma` has `conditions:["heart"]`, `cooks:true`]**
**Primary need.** *Which of my four people is worst off, and what single change moves it most.* **[EVIDENCE — `worst_person`, `worst_pct`, "best for Amma" appears in `.pick` meta and ledger `.who`]**
**Technical proficiency.** Moderate. **[ASSUMPTION]** — no usage data exists; inferring from the design target ("a cheap Android phone in a cold kitchen") and from the tappable-card input model.
**Expectation.** An instruction they can execute this morning, not a dashboard to interpret. **[ASSUMPTION]**
**Likely frustration.** The app already tells them "Keep them shut" before it knows whether they have windows open, a purifier, or a chimney — and the control that would fix that is folded shut at the bottom of the page. **[EVIDENCE — advice is derived from `windows_day`/`windows_night`, which are fixed defaults and not editable]**
**What would make it useful.** *"Amma carries 34.8%, and 73% of it is from the home"* — person + place + share, in one line. **[EVIDENCE — `#personNote` produces exactly this sentence shape]** That converts an ambient worry into a specific, arguable household decision.

---

### Persona B — "The chulha household": biomass, no exhaust, one room used for everything

**Who.** 4–6 people, wood or dung, `kitchen_exhaust: none`, often no separate kitchen. **[EVIDENCE]** — `biomass` is a first-class fuel with kitchen PM2.5 at 180 µg/m³ vs 35 for PNG; `clean_fuel` and `kitchen_exhaust` are modelled interventions; and the UI card reads "Wood or dung — chulha, crop waste". **[EVIDENCE — `FUELS`, line 977]**
**Primary need.** To be told, without shame, that the stove is the largest source they control, and what the cheapest real alternative costs. **[EVIDENCE — ₹800 box-fan filter exists as an option in the ranked set]**
**Technical proficiency.** Low. **[ASSUMPTION]** — grounded only in the app's own copy rule (plain sentences, local words like *chulha*, *autowala*), which is evidence of intent, not of the user's skill.
**Expectation.** Advice they can afford and execute without a landlord's permission. **[ASSUMPTION]**
**Likely frustration.** Two structural ones, both visible in the markup: **(a) the page is English-only** — `language` is plumbed through the backend but only `en` exists, so the audience with the highest exposure reads a second language; **(b) every cost is displayed but there is no affordability filter**, so a household that cannot spend ₹9,000 must scan 14 rows to find the ₹800 one.
**What would make it useful.** A rupee ceiling as an input — "what can you spend this month" — that re-ranks. Cheap to build (a filter over `ranked`), and it would do more for this persona than any prose improvement.

---

### Persona C — "The one with a body in it": asthma, COPD, cardiac, or pregnant

**Who.** Someone whose dose matters more per microgram — either the patient or the adult managing them. **[EVIDENCE]** — `conditions` enum, a sensitivity multiplier that reweights household share, `attributed_risk_share`, and the `worst_person` field on every ranked option.
**Primary need.** Their own number and *which action is for them specifically.* **[EVIDENCE — "best for Amma at X%" in `.rmeta`]**
**Technical proficiency.** Any. **[ASSUMPTION]** — illness does not predict device skill; I refuse to pretend otherwise.
**Expectation.** That the tool will not pretend to be a doctor. It doesn't: "Not medical advice" sits in `.colophon`. **[EVIDENCE]**
**Likely frustration.** **`pregnant` is in the schema and has no control anywhere in the UI.** **[EVIDENCE — `DEFAULTS` has `pregnant:false`; `editPerson()` builds only name, age, condition, cooks, commutes]** A pregnant user cannot tell the app she is pregnant, in a product whose entire premise is that individual susceptibility changes the arithmetic. That is the sharpest single gap between the model's ambition and the interface's reach.
**What would make it useful.** A one-tap "this is for me" lens that filters the 14 options to the ones that move *that person's* dose most — the data (`r.per_person`) already exists and is only rendered inside an expanded ledger row. **[EVIDENCE — `renderOptions()` builds per-person before→after bars inside `.ob`]**

---

### Persona D — "The evaluator" (secondary, but the one who decides if this ships)

**Who.** A judge, reviewer, or engineer checking whether the arithmetic is honest. **[EVIDENCE]** — 250 automated checks, a frozen contract, 56 constants across 12 groups with `source` and `kind` per constant, `#evi` drawer, `#factors` fetch.
**Primary need.** To see sources, uncertainty bands, and an explicit statement of what the model cannot see. **[EVIDENCE — `.kind.estimate` / `.kind.measured` badges; "nothing to change" vs "not counted" distinction in `renderOptions()`]**
**Technical proficiency.** High. **[ASSUMPTION]**
**Expectation.** That a number with a band is never printed without the band. Mostly met.
**Likely frustration.** That honesty is buried: the band only appears in `#cutBand` after a tick, and the evidence drawer sits below eight screens of content. **[EVIDENCE]** The product's differentiator is its epistemics, and its epistemics are the least visible thing in it.
**What would make it useful.** The band on the *first* number, not the fourth. If the headline dose came with "±30%, modelled" attached, the evaluator's job would be done in five seconds.

---

## 3. The value proposition, tested

**One sentence:** *Saans tells a household how many micrograms of PM2.5 each of its members actually inhales in a day, which of them is worst off, and what a specific change would remove — computed, banded, and never guessed at by the model that words it.*

### The strongest case against it

A household rationally declines this product for five reasons, and four of them are good.

**1. The number is unfalsifiable, so precision is a claim, not a fact.** Nobody can check 6,283 µg/day. A city AQI of 341 is at least corroborated by three other apps and a government bulletin. Saans asks for trust in a 56-constant mass-balance model whose inputs — infiltration rate, deposition, plume dispersion — the user will never see. "Computed, not guessed" is a *provenance* claim. It is not verification. For a household making a ₹9,000 purchase, an unfalsifiable number and a plausible guess have the same decision weight.

**2. The output is high-resolution and the decision space is low-resolution.** Whether Amma's dose is 4,000 or 9,000 µg, the correct action in Delhi in December is: keep windows shut at peak, get the stove vented, run a filter in the room she sleeps in, don't let her sweep dry. Four actions. A household that already believes this gains nothing from a percentage; a household that doesn't is not persuaded by a model it cannot audit. **This is the killer argument: the product's precision exceeds its decision space, so most of its resolution is decorative.** The `/api/combine` honesty is intellectually admirable and practically irrelevant to someone deciding whether to buy a purifier.

**3. The real constraint is money and agency, not information.** For Persona B the answer is a ₹800 fan filter — but a household that can afford ₹800 often already has one, and a household that can't is not moved by a percentage. For a renter, "install a chimney" is not an option at any price. The app prices interventions but does not model *permission*, which is the binding constraint for half its audience.

**4. The advice is unenforceable at the resolution it is given.** "Open up at 04:00" is correct and useless: nobody sets an alarm for 4am to open a window. The scrubber produces an intention, not an action. The one genuinely habitual behaviour in the product — window opening — is governed by a fixed `windows_day: "mixed"` default the user cannot even edit, so the app's most actionable advice rests on an assumption it never surfaces. **[EVIDENCE]**

**5. Its answer barely changes, so the second visit has almost no marginal value.** The household is fixed: same fuel, same commute, same flat, same four people. Across a winter the outdoor term moves and the dose moves a few percent with it. The ranking of interventions is effectively stable. **Saans is a one-shot diagnostic wearing a daily-assistant interface.** A rational household uses it two to four times per winter — once at the start, once when someone gets sick, once before a purchase — and then stops, correctly. Everything in §7 follows from this and not from a missing notification.

**Where the case for it survives.** Narrowly and genuinely: at the moment of a purchase, and at the moment of an argument. "Which purifier, which room, is the chimney worth it, is my mother's cooking killing her" are real, recurring, high-stakes household questions that a city AQI app cannot even parse. Saans answers those in one session with arithmetic the user can inspect. That is a real product. It is a **decision aid sold as a companion**, and the honest position is to stop apologising for the second and lean hard into the first.

---

## 4. UX problems in the current implementation

Ordered by severity, not by screen order. Every "fix" is scoped to the single-file constraint.

### BLOCKER

**B1. The zero state fabricates a family and presents it as yours.**
*What's wrong.* With no stored household, `household()` returns `DEFAULTS` — a family named **You, Partner, Child, Amma**, with Amma at 68 and heart disease. **[EVIDENCE — `household()` line 452; `DEFAULTS` lines 444–449]** The page then renders "Amma carries the most of it — 34.8%" and "best for Amma" throughout `#picks`, `#people`, `#plan`, identically to a configured state. There is no banner, no chip, no dimming, no "example" label. A first-time user is shown confident, specific medical-adjacent claims about four people who do not exist, and the only way to discover this is to scroll ~10 screens to a folded `#ed` panel.
*Severity.* **Blocker.** Every number on the first screen is about someone else. This is not a shallow zero state; it is a fabricated one, and it damages trust at exactly the moment trust is being formed.
*Fix.* Three parts, all cheap: (a) a `#firstrun` banner directly under `#verdict` reading "These numbers assume a household of four you have not described. Tell us yours →", which opens `#ed` expanded and scrolls to it; (b) rename defaults to `Person 1–4` with no condition, so nothing false is asserted; (c) keep the demo reachable via `?example=1` for reviewers who want to see a populated page. The third point matters — the demo is genuinely good and should not be destroyed, only labelled.

**B2. The server streams the generation; the client throws every token away. — *fixed mid-research; the fix has three gaps left***
*What's wrong (65,041-byte build).* `/api/plan` emits `facts`, then `token` chunks, then `plan`, then `done`. The reader did exactly one thing: `if (obj && obj.today) finalObj = obj;`. Every `token` event was parsed and discarded. **[EVIDENCE — the reader loop in `loadPlan()`, ~lines 729–743]** The user therefore saw a 6px `pulse` dot and the words "Reading your numbers" for the entire 30–90 s generation. **[EVIDENCE — `.streaming`]** That wasted the single most persuasive signal the product owns: a 4B model thinking out loud is where "this is generated, on this device" stops being a claim and becomes visible.
*Severity.* **Blocker** in the build I read. Longest wait in the product, moment of highest abandonment, and the fix was already paid for on the wire.
*Fix — and what the landed fix still misses.* The working tree now appends streamed text into a `<pre class="rawtext">` (mono 10.5px, muted), counts characters, and updates one status line in place: *"Wording the plan · 1,204 characters in"*. It also uses the `facts` event for a genuine 0-second signal: *"Numbers ready · 5 actions decided · wording now"*. That is the right shape and the right placement. Three gaps remain:
1. **`box.textContent = ""` still runs first** in `loadPlan()`, so the previous plan is destroyed and the reader gets an empty region during the wait. Keep the last plan, badge it `aria-busy`, replace it on arrival.
2. **`raw.textContent = (raw.textContent + obj.t).slice(-420)`** clips from the front, so the visible text begins mid-word and re-flows on every chunk. Use a fixed-height scroll container with `scrollTop = scrollHeight` instead of string truncation — truncating the string also makes the block's height jump.
3. **`factsMeta` is threaded into `renderPlan(p, factsMeta)` and never used inside it.** **[EVIDENCE — the only occurrence of `factsMeta` in `renderPlan` is the parameter]** Dead parameter: either render "numbers ready at 0 s, wording took 41 s" in `.planfoot`, or drop the argument.

The measurement that would settle whether this matters: time to first visible character, and scroll-depth at abandonment. Neither exists.

**B3. The household editor — the input to every number — is the last thing on the page, below the evidence drawer.**
*What's wrong.* Section order puts `#ed` at line 385, after the ledger, after `#evi`, after `.colophon`. It is a `<details>` closed by default whose summary reads "Your household" with a small `edit` badge. **[EVIDENCE]** A user must scroll past roughly 10 screens of output generated from assumptions to reach the only control that makes the output theirs.
*Severity.* **Blocker.** Personalisation *is* the value proposition; burying its input at the bottom means the median session never personalises, and the product's differentiator never fires.
*Fix.* Two surfaces: (a) a persistent chip in `.bar` next to `#placeBtn` reading `4 people · LPG` that opens the editor as a full-width panel directly under the header — the same pattern `#locpanel` already uses successfully **[EVIDENCE — `#placeBtn`/`#locpanel` toggle, lines 1093–1098]**; (b) on first run, the banner from B1 opens it automatically. Do not build a modal wizard; the existing three-step markup is good, it is only in the wrong place.

**B4. Every household edit destroys the plan and re-runs a 30–90 s generation without asking.**
*What's wrong.* Changing one age (`editPerson()` → `Set`, line 1086), one fuel card (via `Save and re-run`, line 1033), or the location (line 1125) all call `await boot(true)` then `await loadPlan()`. `loadPlan()` clears `#plan` first. So the user's readable plan vanishes, the page silently spends up to 90 s, and there is no cancel. **[EVIDENCE]** The tell that this was known and abandoned: all three call sites pass `boot(true)` and `async function boot()` **has no parameters** — the "fresh" flag was intended and never wired. **[EVIDENCE — line 1138]**
*Severity.* **Blocker** in combination with B3: the first edit a user makes is the one that makes the product feel broken.
*Fix.* Stop auto-generating. Recompute `#brief` on edit (fast, pure Python) and mark `#plan` stale with a small "numbers changed — rewrite the plan" button. Then wire the `fresh` flag properly so `boot()` can skip the second round trip. This also fixes the dead-argument smell.

### MAJOR

**M1. The advice depends on a window state the user never supplies, and cannot edit.**
*What's wrong.* `#verdict` is an imperative about windows — "Keep them shut", "Open up at 04:00". **[EVIDENCE — `verdictText()`, lines 472–483]** It is derived from `home.windows_day` and `home.windows_night`, which are fixed at `"mixed"` / `"closed"` in `DEFAULTS` and have **no control anywhere in `renderEditor()`**. **[EVIDENCE]** The headline recommendation of the entire product rests on an assumption the interface never shows and the user cannot correct.
*Fix.* Add a fourth editor step, "Your windows", with three states (open most of the day / only when it's clean / shut all day) and a night state. Two radio groups, existing `radioCards()` helper, no new CSS.

**M2. "Show in the ledger" is mislabelled and implies a commitment the app does not make.**
*What's wrong.* `#applyBtn` — the primary button in the tally — reads "Show in the ledger" but only opens matching `<details>` rows and scrolls. **[EVIDENCE — lines 1179–1186]** "Apply" plus a primary dark fill reads as *commit*. A user who has ticked three actions and pressed the big button believes their plan was saved. Nothing was saved; the ticks were already saved on every click, and the plan above was never touched.
*Fix.* Rename to "Open in the full list ↓" and make it `ghost`, not primary. Then add the button the label is begging for: **"Pin these to today's plan"**, which rewrites `#plan`'s rail from the user's picks. The bench and the plan currently disagree about what the plan is (§M3) and this is where to reconcile them.

**M3. The bench and the generated plan are two different plans, stacked.**
*What's wrong.* `skeleton()` decides five actions in Python, independently of `PICKS`. So a user who ticks "chimney" and "mask" reads a plan below that recommends neither. **[EVIDENCE — bench section 334 is entirely separate from `renderPlan()`; `actionKey()` is built from `t.time`/`t.action`, not from a pick key]**
*Fix.* The plan becomes derived: if `PICKS` is non-empty, `skeleton()` receives them as fixed constraints and fills the remaining slots. Until that ships, label the plan "our suggestion" and the tally "your version" so the duplication is at least legible.

**M4. The central unit is never defined in place, and the intuitive anchor only appears after a second action.**
*What's wrong.* "µg/day" carries the whole product. `#ladder`'s fourth rung prints a number and the unit with no explanation. The cigarette equivalence — the one anchor a lay reader can feel — exists only in `#cutSub`, which is empty until you tick something. **[EVIDENCE — line 672: "from X to Y cigarettes' worth"]** So a first-time user sees `6,283 µg` on the ladder with no referent at all.
*Fix.* One line under the ladder: "6,283 µg a day is roughly 3.4 cigarettes' worth — the dose, not the air." Use `cig_before` that `brief` already returns. And put a `title`/`aria-description` on the rung's unit.

**M5. Intervention titles are truncated on phones, and the truncation eats the personalisation.**
*What's wrong.* `.pick .pt` is `white-space:nowrap; overflow:hidden; text-overflow:ellipsis` and the "best for Amma · low cost" meta is appended *inside* that same span as an `<em>`. **[EVIDENCE — lines 113, 118, 632–636]** At 390px, after an 18px box, an 8px gap and a 48px cost column, the title column is roughly 250px — enough for ~30 characters of 12px text. The meta is clipped first because it comes last. So the *reason this action is for your mother* is the first thing to disappear, on the device the product was designed for.
*Fix.* Two-line clamp (`-webkit-line-clamp:2`) on `.pt`, move the `em` meta to its own grid row spanning columns 2–3, and add `title=` for pointer users. This raises `.pick` from 34px to ~48px; the comment at line 111 says the density was deliberate to avoid a "640px wall", so compensate by grouping the 14 into 3 collapsible source groups (home / travel / person) rather than by keeping the truncation.

**M6. Done-marks are keyed on the clock, so the only retention mechanic in the product silently decays.**
*What's wrong.* `actionKey(t)` = `(t.time + "|" + t.action)` slugified. **[EVIDENCE — lines 711–714]** Plan times are computed per run from `next_trough`/`next_peak`, so tomorrow's "07:00 open windows" is a different key from today's. Yesterday's `saans.done.v1` entries do not match; they accumulate as orphans and nothing renders as done. The one loop the app has — mark done, come back, see progress — breaks on the second day by construction.
*Fix.* Key on a stable identifier. `ranked[].key` already exists and is stable per intervention **[EVIDENCE — `btn.dataset.key = r.key`]**. Store `{key: {date, count}}` and render "done 3 of the last 5 days" instead of a binary tick.

**M7. There is no export, no share, and the print stylesheet does not exist.**
*What's wrong.* No `@media print` block anywhere in the CSS; no `navigator.share`, no copy button, no download. **[EVIDENCE — full CSS read at 65,041 bytes; the working tree still returns 0 matches for `@media print`]** The README used to claim a print stylesheet — that sentence has since been removed, which fixes the *documentation* defect and leaves the *feature* gap exactly where it was. For a household product whose natural distribution is a screenshot to a family WhatsApp group, the absence of any share path is a structural omission, not a polish item.
*Fix.* (a) a real `@media print` block that hides `.bar`, `#picks`, `#evi`, `#ed` and expands `#opts`; (b) a `navigator.share` / clipboard button in `#plan` that emits a 4-line text summary — verdict, worst person, top action, cost. The second is worth more than the first, and both are ~20 lines.

**M8. "Keep them shut" has no antecedent.**
*What's wrong.* The h1 says "Keep them shut until about 06:00". The word *windows* never appears on the first screen. **[EVIDENCE — `verdictText()` returns lead/tail with no noun]** A user arriving cold has to infer the object from a 92px chart.
*Fix.* "Keep the windows shut until 06:00." One word; the verdict is the most-read string in the product.

**M9. The chart nests `role="img"` inside `role="slider"`.**
*What's wrong.* `#plotwrap` is a slider (`aria-valuemin`/`max`/`now`), and `#plot` inside it is `role="img"` with `aria-labelledby="bandDesc"` — a 300-word description read on every arrow key. **[EVIDENCE — lines 324, 618–621]** Screen-reader users get an image inside a slider, and the slider's `aria-valuetext` competes with the image's long description.
*Fix.* Drop `role="img"` from `#plot`; keep `#bandDesc` as `aria-describedby` on the slider so it is read once on focus, not on every value change.

### MINOR

**m1. `/api/ambient` and `/api/sources` are unused by the frontend.** **[EVIDENCE — no `fetch` to either in the script]** Dead surface area: two routes, tests, and contract to maintain for a client that does not exist. Either wire source apportionment into the "Where it comes from" note (it would strengthen M-persona C) or delete them.

**m2. The verdict goes stale while the tab is open.** `setInterval(tickClock, 30000)` updates `#clock` every 30 s but `verdictText()` runs only inside `boot()`. **[EVIDENCE — line 1198 vs 1148]** Leave the tab open overnight and the headline still says "Open up at 04:00" at noon. Fix: recompute the verdict string from `LAST.brief` on the same 30 s tick, no network.

**m3. `pregnant` and `exercises` exist in the schema with no control.** **[EVIDENCE]** Same class as M1 but lower traffic. Add both to `editPerson()` — one select entry, one checkbox — since the model already prices them.

**m4. The single most important concept in the product is 11.5px muted text.** The non-additivity explanation — the thing that makes this different from every other calculator — is `.benchhead .aside`, `font-size:11.5px; color:var(--muted); max-width:46ch`. **[EVIDENCE — line 101]** It is a caption for the product's best idea. Promote it to a first-class line inside `#tally` that only appears once two picks with overlap are selected.

**m5. `#saveNote` says "saved" in 10px mono for 2.2 seconds.** After a 90 s regeneration, that is an inadequate confirmation. Show a persistent "Updated HH:MM" timestamp next to the household chip instead.

**m6. README test counts were stale** (48/41 vs actual 51/43). **[EVIDENCE — `PRODUCT_UNDERSTANDING.md` §Documented defects; the working tree now correctly says 51 / 43, so this is fixed]** Documentation defect; it mattered because the 250-check claim is part of the pitch to Persona D, and a stale count undermines the one audience that will actually count.

---

## 5. User journey map

| # | Stage | What the user does | What they see | Where they get stuck |
|---|---|---|---|---|
| 1 | **Landing** | Opens the URL, possibly from a shared link. | `#verdict` in 27–38px serif — an imperative about windows. `#ladder` with four rungs. `#plot` with two bar series. `#kicker` "Delhi · PM2.5 341 · AQI Very Poor". A sticky `.bar` with place, clock, Dark. | **They are told what to do about a household they never described.** No sentence anywhere says "these four people are an example". The one control that would fix it (`#ed`) is 10 screens down and folded shut. |
| 2 | **Understanding** | Reads the verdict, scans the ladder, maybe drags the chart. | The chain outdoor → indoors → stove → breathed. The readout follows the cursor. | The fourth rung prints `6,283 µg` with no referent. "Dose" is never defined. The cigarette anchor exists only in `#cutSub`, which is empty until a tick. The non-additivity idea is an 11.5px caption. |
| 3 | **Input** | Tries to make it about their family. Hunts for a control. | Eventually a folded `#ed` summary reading "Your household" with an `edit` badge, below the ledger and the evidence drawer. | **Discovery fails before the form does.** If found, the form is good — three steps, tappable cards, labels like "Wood or dung / chulha, crop waste" — but it accepts only 3 household facts and 5 per-person facts, so `windows_*`, purifier, incense, coil, waste burning, cook hours are unreachable. Persona C cannot enter `pregnant`. |
| 4 | **AI processing** | Waits. Scrolls to find the plan. | Was: a 6px `pulse` dot and "Reading your numbers" for 30–90 s. Now: the same line plus a streamed mono tail and a character counter, then *"Numbers ready · 5 actions decided"* at ~0 s. **[EVIDENCE — `rawtext` block]** | **No cancel, and the old plan is still deleted on start.** The stream is now visible (fixed mid-research), but `loadPlan()` blanks `#plan` first, so an edit costs you the plan you had before you see the next one. The plan still sits *below* the 14-row bench, so on mobile the user is often not looking at the progress they waited for. |
| 5 | **Results** | Reads the plan. | Opening serif paragraph, five figures, a children's paragraph, a time rail with the top item accented, "what this does not fix", and a footnote counting removed sentences. | The plan recommends actions that may not include the ones they just ticked (M3). "The one thing" is chosen by Python, not by them. The footnote about deleted sentences — the most trust-building sentence on the page — is 9.5px mono at the bottom. |
| 6 | **Refinement** | Ticks 2–3 interventions; watches the tally. | Big `−16.1%`, µg before→after, cigarettes, band, cost ₹/yr, overlap note, per-person bars. Presses "Show in the ledger". | Numbers move, meaning doesn't: the plan above never changes, so the two halves of the page disagree. `.pick` titles are ellipsised so the "best for Amma" reason is clipped. "Show in the ledger" feels like Save but is a scroll. Ticking again re-posts `/api/combine` with no debounce and no loading state beyond "Working it out…" in `#cutSub`. |
| 7 | **Export** | Looks for a way to keep or send it. | Nothing. No print, no share, no copy, no download. | **Journey ends in a dead end.** The user's only option is a screenshot. The household is persisted; the *result* is not. |

### The single worst moment

**Stage 1, the first three seconds.** Not the wait — the wait is legible friction, the user knows something is loading, and it is recoverable. Stage 1 is worse because it is **wrong quietly**: the product asserts "Amma is 68 with heart disease and carries 34.8% of your household's dose" to a stranger, in a serif headline, with the full confidence of computed output, and offers no signal that this is a placeholder. A slow app is forgiven. An app that appears to have invented your family is closed, and the reason is never verbalised as "zero state" — it is verbalised as "this is fake".

The 30–90 s generation **was** the highest *drop-off* risk and got the bigger engineering fix (B2, now largely landed). But the worst moment is being confidently wrong before you have earned the right to be trusted.

---

## 6. Recommended information architecture

### The rule

> **Level 1 if it changes what the user does in the next hour. Level 2 if it changes what they do this week. Level 3 if it explains why any of it is true.**

Applied honestly, that rule demotes most of the current page. A 14-row ranked ledger sorted by dose-removed-per-rupee is a Level 2 object — it changes a purchase decision, not this morning — yet it currently sits at Level 1, above the plan, while the household editor, which is a precondition for Level 1 being true at all, sits at Level 4.

### Level 1 — first screen, no scroll on a 390×844 phone

1. **Household state chip** in `.bar`: `4 people · LPG` — taps open the editor panel. (New; replaces nothing.)
2. **The verdict**, with its noun: *"Keep the windows shut until 06:00."*
3. **The one thing to do**, as a single line under the verdict: action + time + who it is for + cost. This is the product. It is currently item 5 of 5 inside `#plan`, several screens down.
4. **The people strip**: four compact cards, dose and share, sorted worst-first, scrollable horizontally if needed. Already exists as `#people`; move it up.
5. **The 24-hour strip**, compressed to ~60px, non-scrubbable until tapped. Scrubbing is a Level 2 interaction and does not need 92px of first-screen real estate.

That is one screen, one instruction, one number per person, one time signal. Everything above already exists in the file; this is reordering, not rebuilding.

### Level 2 — one tap away

6. **The bench** (14 picks + tally), moved directly below the first screen. This is where a user who has accepted the instruction goes to ask "what else".
7. **The generated plan prose.** Prose is Level 2: it changes how they feel about the week, not what they do in the next hour. Its *actions* are Level 1 and should be lifted out of it (item 3).
8. **Cost and affordability**: the ₹ figures already in `#cutBand`, plus a "what can you spend" filter — the single highest-value addition for Persona B.

### Level 3 — three taps (or one disclosure) away

9. **The full ranked ledger** of 14, with per-person before→after. This is a research surface.
10. **The evidence drawer** (56 constants), which is correctly built and correctly buried.
11. **The household editor**, *except on first run*, when it is Level 1 and opens automatically (B1/B3).

### Why this beats the current IA

The current order is **output → output → prose → output → output → provenance → input**. It is ordered by how impressive each block is, not by what the user needs next. Mine is ordered by decision latency: act now → act this week → understand. Concretely it fixes three measured problems at once — the editor becomes reachable (B3), the plan's actions stop competing with the bench (M3), and the first screen stops being a report (the density comment at CSS line 111 explicitly worries about "a wall [that] made the old design read as a report"; the current order reproduces that wall one section lower).

### The alternative I rejected

**"Dashboard first": four person-cards and the full 24-hour chart above the fold, AQI-app style, with the verdict as a caption.** Rejected because it re-creates the exact artefact the product exists to replace. A four-card grid of numbers *is* a gauge with more gauges; it asks the user to synthesise, which is the failure mode of every AQI app. The product's claim is that it hands you a decision, not a readout — so the first thing on the screen must be a sentence in the imperative, not a panel of figures.

I also rejected **"wizard first"** (force the three-step setup before showing any number). It front-loads cost before demonstrating value, and it would break the reviewer's ability to land on a populated page. The banner + auto-opened panel in B1 gets the same data without a gate.

---

## 7. The retention problem, honestly

**The diagnosis, stated without comfort.** The app has no reason to be opened tomorrow, and adding a reminder would not fix that, because there is nothing new to see. The household is static; the ranking is stable; the plan re-words the same advice. `localStorage` holds four keys — `saans.household.v1`, `saans.theme`, `saans.picks.v1`, `saans.done.v1` — and **not one of them contains a date**. **[EVIDENCE — line 411]** So the "versus yesterday" line is not a rendering bug: there is no dated snapshot to compare against, and no code path that writes one. The feature requires a data model that does not exist.

Given the constraints — one HTML file, no service worker, no account, no backend cron — there are exactly three levers that do not require lying to the user.

### Fix 1 — A dated local snapshot, and a real "since you last looked" line

Write `saans.snapshot.v1` = `{date, dose, worst, worstPct, topAction}` on each successful `boot()`. On the next open, if the stored date is older than today, render one line under the verdict: *"Last time you looked, on 14 Dec: 6,412 µg — down 2% today, mostly because the air is cleaner."*

**Why it works:** it makes the second visit *informative* rather than repetitive, and it costs about 40 lines and one key. It also finally makes the "versus yesterday" claim true, which is currently a promise the code cannot keep.
**Weakness:** it improves visit 2 but cannot cause it. A snapshot only pays off if the user opens the app, which is the thing that isn't happening. It is a prerequisite, not a solution.

### Fix 2 — Make the output leave the app: a share card

A single `Share` button in `#plan` that emits, via `navigator.share()` or the clipboard:

> **Saans — Amma is worst off today.** 6,283 µg/day for our household. The one thing: shut the windows until 06:00. Chimney would cut 22% for ₹4,500. Computed on our phone, not guessed.

**Why it works:** this is the only mechanism inside the constraints that can generate an *inbound*. The artifact travels to a WhatsApp group where the decision is actually made (a household purchase is a family negotiation, not an individual one), and every recipient is a warm lead with a plausible reason to open the link. It also converts a private readout into a social object, which is what the product is actually for.
**Weakness:** unmeasurable. No analytics, no accounts, no attribution — you will never know if it worked. And a badly-worded card is worse than no card, so the four lines need the same discipline as the model prose.

### Fix 3 — Close the loop on done-marks with a stable key

Fix M6 first (key on `ranked[].key`, not `time|action`), then render a persistent strip: *"3 of 5 done this week. The chimney is still the one you haven't done."* Add a single weekly line on the same snapshot: *"Last week you did 3 of 5. The one you keep skipping is the chimney."*

**Why it works:** it is the only honest habit mechanic available without a server, and it exploits the one thing the app already knows that the user doesn't — which recommendation they keep ignoring. Shame is a stronger retainer than novelty.
**Weakness:** entirely self-reported, and self-report decays fastest among exactly the users who need it. It also risks moralising, which the product's own copy rules forbid.

### What I would ship first, and its weakness

**Ship Fix 1 first.** It is 40 lines, one new key, zero new failure modes, and it is the *precondition* for Fix 3 and for any future claim of the form "since last time". You cannot build a habit loop on a product that has no memory of yesterday.

**Its weakness, stated plainly:** it makes the second visit worth having, and does nothing to cause it. The honest trigger — a morning WhatsApp digest, "today is a 341 day, keep the windows shut until 06:00" — is a server-side cron plus an account, which is precisely what the constraints forbid. So the real finding of this section is uncomfortable and I will not soften it: **the constraint set, not the design, is what limits retention.** Within one HTML file and no backend cron, Saans can be an excellent thing to consult; it cannot be a thing that summons you. The right move is to stop designing it as a daily companion, position it as the decision instrument you open at the four moments that matter — the purifier purchase, the chimney argument, the first bad week of November, the diagnosis — and make each of those sessions fast, shareable, and worth screenshotting. Fix 1 and Fix 2 serve that product. A notification would only serve a product this one is not.

---

## Appendix — what I could not verify

- **Whether any household opens this twice.** No telemetry, local app, no logs. Every retention statement above is reasoning from the data model (no dates stored), not measurement. **[ASSUMPTION]**
- **Whether the default four-person household is a demo or a fallback.** It reads as both; the code offers no way to distinguish, which is itself the defect in B1.
- **How many of the 14 ranked options are permanently inert** because their inputs (`waste_burning_kg_week`, `incense_per_day`, `mosquito_coil`, `cleaner`, `mixer`) are fixed at zero/none and uneditable. I did not trace `advisor.py`; I can only say that any option keyed to those inputs can never return a non-zero effect for a user who cannot set them, and that `renderOptions()` has a dedicated `"—" / "nothing to change"` branch **[EVIDENCE — line 912]** which suggests the author saw this happening often. Worth counting before it is quoted as a number.
- **CSP.** The context states a strict CSP is enforced; there is no `Content-Security-Policy` meta tag in `index.html`, so it must be header-delivered by FastAPI. Not verifiable from the file I read.
