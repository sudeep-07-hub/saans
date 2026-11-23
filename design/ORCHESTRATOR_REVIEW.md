# ORCHESTRATOR REVIEW — Phase 2 deliverables

Three agents delivered. I verified rather than accepted. This records what I
checked, what I rejected, and what I overrode.

## Agent 1 — `PRODUCT_RESEARCH.md` (45.7 KB) — ACCEPTED WITH CORRECTIONS

Verified its five claimed defects against the source. **All five are real:**

| Claim | Verified |
|---|---|
| `boot(true)` passed at 3 sites, `boot()` took no args | true |
| `actionKey` has no date, so done-marks orphan daily | true |
| no storage key contains a date, so "vs yesterday" has *no data model* (not merely unrendered) | true |
| zero-state fabricates a family and presents it as fact | true, and worse than described |
| `.pt` is nowrap+ellipsis, so "best for Amma" clips first on a phone | true |

Its strongest finding was right and I fixed it the same hour: **zero-state was
not "indistinguishable" — the page confidently asserted "Amma carries 37.6% of
the household's inhaled dose" about a woman the user never mentioned.**

Correction I made to its analysis: it reported `/api/brief` "ignores the
household". The real cause was larger than it found — the frontend sent the
wrapped shape `{household:{...}}` while every endpoint declared the flat shape,
so **every user's configuration was discarded for everyone, always.** Neither
Agent 1 nor I had found that until I probed the payload by hand at 26bbdd9.

Its §2 "strongest case against" is the best paragraph in any of the three docs:
the output is high-resolution while the decision space is low-resolution. Whether
the dose is 4,000 or 9,000 µg, the action list is the same. That critique is
correct and I am not going to pretend it is solved by a redesign.

## Agent 2 — `UX_ARCHITECTURE.md` (74 KB, 1,019 lines) — ACCEPTED

Its central insight supersedes my own fix and I have adopted it:

> The plan's content is available in 40 ms; only its wording is slow. Never show
> a spinner for something whose substance you already have.

I verified the premise myself: `narrator.skeleton()` is pure Python over
`brief` + `ranked`, both in the first payload. Measured at **19 ms** against
**13.2 s** for the model path. That ratio is what justifies the architecture.

Also verified: the 740px fold arithmetic (real Android chrome eats ~104px of
844), the seven rejected architectures each carry a specific loss rather than a
vibe, and the state matrix's rule — *"a missing number is never zero"* — which
is the same principle as the rest of the product.

Two API asks, both optional, one I have since built: `today[]` in the SSE `facts`
event is unnecessary because `/api/skeleton` now returns the actions in 19 ms.

## Agent 3 — `DESIGN_SYSTEM.md` (69 KB) — ACCEPTED, MATHS INDEPENDENTLY VERIFIED

Direction: **"Notice & Plate"** — a municipal air-quality notice on instrument
stock, one near-black plate carrying the verdict, edged with a 4 px band in the
day's air colour. Rejected: "Instrument panel" (skeuomorphism implies it
measures) and "Editorial almanac" (the current look; reads as age).

I re-derived its entire CPCB contrast table from the hexes in a separate process.
**All 12 figures reproduce exactly.** Five of six official NAQI colours fail AA
in both directions (Moderate `#ffff00` is 1.07 on white, 1.09 as text). The
document refuses to ship the official palette raw and transposes it into two
tracks that hold each category's hue while moving lightness until it passes. That
is the correct engineering answer and it is proven, not asserted.

The two tokens it added — `--plate-muted` (2.89:1 on the plate) and
`--alarm-plate` (2.01:1) — are real silent bugs it caught by measuring.

## Conflicts resolved

1. **Navigation.** Agent 1 suggested act-now → act-this-week → understand.
   Agent 2 committed to one scroll with a chapter spine. **Agent 2 wins**: they
   are compatible (the spine *is* the act-now-first order), and Agent 2 specifies
   the mechanism.
2. **The zero-state fix.** Both proposed a banner. I implemented it and then
   found it was hiding a much larger defect, which is now fixed properly.
3. **File size.** Agent 3 budgets +1.2 KB CSS. We are at 71.4 KB. The 70 KB
   ceiling was my own target in `CONTRACT.md`, not a rule from the brief — the
   brief's only size rule is 10 MB for the repo. I am raising the single-file
   ceiling to **90 KB** and recording why, rather than deleting accessibility
   guarantees to hit a number I invented.

## Approved direction

**Notice & Plate**, one scroll, a sticky chapter spine, two dialog sheets, and a
plan that renders its actions before its prose.

Adopted from Agent 2: content-before-prose, the 740px fold, the state matrix,
"a missing number is never zero".

Adopted from Agent 3: the transposed AQI tracks, the single-inversion discipline,
hairline rules instead of cards, no gauge, no shadow except one.

**Rejected** from all three: any tab bar, any router, any second model, any
icon set, any gamification.

## Authorisation

Agent 4 is cleared for tasks **P1, P2, P3, P4, P5** in
`design/IMPLEMENTATION_PLAN.md`, in that order, one commit per task. Agent 4 is
the only agent permitted to write `saans/static/index.html`.

P2 and P4 of my original plan are now **done** (26bbdd9) because the zero-state
and the re-generation defects turned out to be the same bug family as the payload
bug. Remaining for Agent 4: P1, P3, P5, plus the design system's token and
component layer.
