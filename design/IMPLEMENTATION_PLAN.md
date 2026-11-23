# IMPLEMENTATION PLAN — approved by the orchestrator

Written from `PRODUCT_UNDERSTANDING.md` (mine), `UX_ARCHITECTURE.md` (Agent 2),
and the still-arriving `PRODUCT_RESEARCH.md` and `DESIGN_SYSTEM.md`.

This is the authorisation document. Nothing in the frontend gets rewritten before
this file exists, and every item here traces to a finding in Phase 1.

---

## What is already correct and must not be touched

I am listing this first, because the largest risk in this phase is an agent
"improving" something that is load-bearing.

- **The arithmetic.** `engine.py` + `advisor.py` + the 56 cited constants. Verified
  by 86 model checks. Not a design concern.
- **The prose boundary.** Python decides every action, time, order and cost; the
  model writes three paragraphs and may not write numerals. 70 narrator checks.
- **The API surface.** 10 routes, all live-verified. `MUST NOT BREAK` in
  `design/CONTRACT.md`.
- **The constraints.** One HTML file, no framework, no CDN, no web fonts, strict
  CSP, WCAG AA, dark mode, reduced-motion and high-contrast honoured.
- **The editorial type direction.** Serif for the verdict, tabular mono numerals,
  paper tones, an accent derived from the CPCB category. Rejected twice as
  "generic", never as "bad taste" — the palette is not the problem.

## What is actually wrong (from Phase 1, re-ordered by impact)

| # | Defect | Status |
|---|---|---|
| 1 | The plan's 30–90 s wait shows nothing while the server streams every token | **FIXED** (5e45ca3) — but only partly: see task P1 |
| 2 | "Your 7-year-old child stays home." shipped beside "the school says outdoor play is fine" | **FIXED** (5e45ca3) |
| 3 | Zero-state is indistinguishable from a configured household | open |
| 4 | The household editor is the last thing on a page it governs entirely | open |
| 5 | The bench and the plan are two different plans, unconnected | open |
| 6 | "Dose" and "µg/day" carry the product and are never defined in place | open |
| 7 | README claims a print stylesheet that no longer exists; test counts stale | open |
| 8 | `/api/ambient` and `/api/sources` are unused by the frontend | open |

## The design direction I am approving

From `UX_ARCHITECTURE.md` §0–2, and I accept its reasoning:

> **One scroll, one column, a sticky chapter spine, two modal sheets.** Not tabs,
> not a wizard, not a feed.

Why I am accepting this over the alternatives:

- The product is a **causal chain** (street air → indoor air → stove plume → one
  person's dose → the effect of a change). Adjacency *is* the argument, and a
  scroll is the only model that preserves it. Tabs would put "your kitchen is 91"
  and "outside is 205" in different places.
- A **wizard** was rejected by both of us: it re-teaches itself every morning and
  punishes the user who wants one number.
- A **dashboard** was rejected in Phase 1: gauges show one value, and the product's
  whole thesis is the gap between four values.

And I am accepting Agent 2's central insight, which is better than my own fix:

> **The plan's content is available in 40 ms; only its wording is slow. Never show
> a spinner for something whose substance you already have.**

My 5e45ca3 made the wait *visible*. This makes it *disappear*, by rendering the
five actions and their effects immediately and letting the prose arrive into a slot
that was already the right size. That is the correct fix and it supersedes mine.

## Prioritised tasks

### P1 — Plan panel: content first, prose after (Agent 4)

The backend already returns everything except the prose from `/api/brief`: the
ranked interventions and their effects are in the initial payload. So:

1. Render the plan region on first paint with the five actions, times, effects and
   the marked one — **filled from `/api/brief`, no waiting**.
2. Reserve the prose slot with the correct min-height so nothing jumps.
3. When `/api/plan` streams, fill the prose slots in place.
4. Keep the streamed-token visibility as a secondary strip (it is now proven to
   work and shows the GenAI honestly), but it must never be the only thing shown.

**Accepts:** the plan is useful at 0 s. **Regression risk:** the deterministic
fallback and the model path must both fill the same DOM slots; test both.

### P2 — First-run state, honestly signalled (Agent 4)

`saans.example=true` when the household is `DEFAULTS`. A 28px bar under the
masthead: `These numbers assume a household you did not describe.` + `Set up`.

**Accepts:** no user is misled by the four sample people. **Risk:** must not show
for a user who *has* saved a household.

### P3 — The exposure ladder becomes the spine (Agent 4)

Already exists. Promote it to the first thing after the verdict, and give each rung
an anchor so the evidence drawer can be opened from the stove figure (Agent 2's
`180` rung detail).

### P4 — Connect the bench to the plan (Agent 4)

Today: "Show in the ledger" only scrolls. Instead: picked interventions mark the
corresponding plan rows, and the tally states the difference between *your* picks
and *the engine's* picks. If they are the same, say so.

**Risk:** this is the most complex task. It must not break `/api/combine`.

### P5 — Define the unit in place (Agent 4)

One line under the ladder, using the engine's own cigarette equivalence:
`1,791 µg a day is about 1.0 cigarette's worth.` Both figures already exist in the
payload. No new arithmetic.

### P6 — Documentation truth (me)

Fix the README: print stylesheet claim, test counts, and the `/api/ambient`,
`/api/sources` status.

### P7 — QA pass (Agent 5)

Independent. Must verify, not trust.

## Sequencing, to prevent agents overwriting each other

Agent 4 is the **only** agent that writes `index.html`. Agent 5 writes only
`UI_QA_REPORT.md`. Agents 1–3 write only their own markdown. No two agents touch
the same file at any point, so no isolated branches are needed and none will be
created (the repo must stay on one branch — a submission rule).

Order: P1 → P2 → P5 → P3 → P4 → P6, with a QA pass after P4 and again at the end.

## Explicitly NOT doing

- No framework, no build step, no router library, no icon package.
- No gamification. No streaks, badges, or scores for a health outcome.
- No second model, no new dependency, no new service.
- No changing the arithmetic, the constants, or the prose boundary.
- No "generic AI dashboard" tells: no gradient hero, glassmorphism, icon tiles,
  left-accent cards, oversized rounded rectangles, indigo accent, emoji.
