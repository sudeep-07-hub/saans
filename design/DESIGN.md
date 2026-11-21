# DESIGN.md — approved direction

Written by the orchestrator after the delegated planning round failed to deliver
(both children spent their budget reading the codebase and never produced a
plan). The design decision is therefore mine, made with the full system context
and recorded here with its rejections so it can be argued with.

Supersedes nothing in `CONTRACT.md`; must satisfy all of it.

---

## The single idea

**The app's thesis is that your exposure is not your city's AQI — it is where
you are, when.** Every other air app shows a city number. This one can show
*your household's* day: the ambient curve outside, your indoor line, and your
cooking times sitting on top of it.

That is the signature element, and it is currently buried as a 24-bar chart in
a sidebar with no axis meaning.

```
                    KITCHEN 218 at 08:00
                          │
   indoor 98 ─────────────┼──────────────
                    ╱▔▔▔╲ │
   outdoor ╱▔▔▔╲▁▁▁╱     ╲▁▁▁╱▔▔▔╲▁▁▁▁
         06:00    11:00   16:00   21:00
              ▲
             now
```

## The one-screen answer (Level 1)

390 × ~700px, no scroll, at 06:40.

```
┌──────────────────────────────────────┐
│ Saans                 Delhi · 06:40  │  40px  mono 10.5/11
│                                      │
│  Keep them shut                      │  verdict
│  until about 11:00.                  │  34px serif, -0.02em, 1.15
│                                      │
│  ▁▂▃▅▇▇▆▄▃▂▁▁▂▂▃▄▅▆▇▇▆▅▃▂         │  72px  next 24h area
│  now                    low 11:00    │  9px mono axis
│                                      │
│  outside      inside     kitchen     │  11px caps labels
│  151          98         218         │  22px mono numbers
│                                      │
│  Amma carries the most of it —       │  13px, 1 ch of accent rule
│  she is in the kitchen at both meals │
│                                      │
├──────────────────────────────────────┤
│ Today's moves                    5 › │  56px tap target, full width
├──────────────────────────────────────┤
│ The numbers behind this           › │
└──────────────────────────────────────┘
```

**What is deliberately absent from Level 1:** the AQI number, the GRAP label,
the generated plan prose, the ranked interventions, source shares, emissions,
the evidence drawer, the date, the household editor. Every one of those is
reachable in one tap. None earns a place on the first screen.

**Why the verdict and not the AQI.** A household cannot act on "324, Very
Poor". It can act on "keep them shut until about 11:00". The AQI is a
*category*; the verdict is an *instruction*, and it is derived from the same
numbers. Showing the category and leaving the reader to derive the instruction
is the exact failure the whole product exists to fix.

**Why three numbers and not one.** The gap between them *is* the product. When
outside is 151 and inside is 98, the envelope is doing work. When kitchen is
218 while both are lower, the app has found the household's own source — the
single most valuable thing it can say. One number cannot show a gap.

**Why the person.** "Amma carries the most of it" is specific to this household
and no weather app can say it. It is the emotional hook, and it is also the
action: protect her.

## The loop

The honest mechanism is **zero-input return**, not gamification.

- **First open:** the household editor is a 60-second one-time setup, then
  never again (localStorage).
- **Every open after:** no input. The verdict is computed before paint.
- **The return hook:** a one-line comparison against the same hour yesterday —
  *"178 at this hour yesterday. 151 now."* Real stored data, no invented
  progress, no streaks, no badges.
- **A "did it" acknowledgement** on each action, stored as
  `done:<date>:<key>`. It changes the action's presentation, nothing else.

**Declared uncertainty:** I do not know whether the daily comparison changes
behaviour. It is cheap, honest, and non-manipulative, so the downside is a waste
of 40px. A streak counter would likely retain better and I am rejecting it —
this is a health product and I will not make illness into a scoreboard.

## Three levels, and the rule

| Level | Content | Rule for entry |
|---|---|---|
| 1 | verdict, day band, 3 numbers, worst-off person | Would a household change what they do in the next hour based on it? |
| 2 | today's 5 actions, the generated plan, school advice | Is it a decision whose time is not now? |
| 3 | ranking, sources, emissions, per-person table, 56 constants | Is it evidence rather than instruction? |

**The rule:** if it changes what you do *in the next hour*, Level 1. If it
changes what you do *today*, Level 2. If it only changes what you *believe*,
Level 3. Everything is reachable; nothing is props.

## Time-awareness

Driven by `elevated_now`, `next_trough`, `next_peak` (added in `2b6a9d6`).

| Now | Verdict leads with | Because |
|---|---|---|
| elevated_now = true, AQI ≥ 201 | "Keep them shut until about {next_trough.hour}:00" | We are at the peak; the useful fact is when it ends |
| elevated_now = false, AQI ≥ 201 | "Open up at {next_trough.hour}:00" | Easing, and there is a real window coming |
| AQI < 201 | "A good day to open up" | No instruction owed |
| `next_peak` within 3h | append "then it climbs again by {hour}" | Prepares for the evening build-up |

**The bug this fixes:** `worst_hour` is a maximum over 0–23 and at 21:00 returns
07:00, so the old copy said "keep windows shut until the late-morning lull" at
night. Advice about the past.

## Household editor

Not a tax form. Three steps, one question each, thumb-sized:

1. **Who lives here** — 4 chips already populated (You / Partner / Child /
   Amma). Tap a chip to change age or conditions. Add one if needed.
2. **How you cook** — 4 large radio cards: gas · piped gas · wood/dung ·
   electric.
3. **Your commute** — 5 icon-ish cards.

Everything else (incense, sweeping, hours) lives behind "More detail" in Level 3
and has a sensible default. The full 8-dropdown form stays available but is not
the default path.

## Plan presentation

The day, not a list. Actions are rendered on a vertical time rail with the hour
in the gutter, in the order the family will live them. The top-ranked action
gets a thin accent rule in the gutter and the words "the one thing" — no badge,
no confetti, no colour block.

The model's prose appears *above* the actions as an opening paragraph and
*below* as the honest limit, never interleaved, because the actions are
Python's and must not be confused with prose.

## Rejected alternatives

1. **A gauge / dial dashboard** (the obvious weather-app move). Rejected: a
   gauge shows one number, and the entire product thesis is the *gap* between
   three numbers and the shape of the day.
2. **Card-at-a-time wizard** (the "ritual" direction). Rejected as the primary
   architecture: it makes the second open feel like an onboarding flow and
   punishes a user who just wants the number. Salvaged as the *plan*
   presentation, where sequence is genuinely natural.
3. **Map with a monitor overlay.** Rejected: the input is a 1–11 km gridded
   model, so a map would imply street-level accuracy the data does not have.
   False precision is worse than a plain number.
4. **Chat interface** ("ask Saans anything"). Rejected: the arithmetic is
   deterministic and the model is forbidden from computing. A chat box invites
   questions the system cannot honestly answer and would put the 4B model in a
   position where it must improvise.
5. **Push notifications / daily digest.** Genuinely the strongest retention
   lever and rejected here only because it needs a service worker and a
   permission prompt, which this single-file, no-account constraint rules out.
   Noted as the first thing to add if the constraint ever lifts.

## Failure modes

| Condition | Behaviour |
|---|---|
| No network | Labelled climatology; verdict still computed; a quiet "offline" chip |
| Model absent / slow | Plan renders with built-in wording; the prose area shows the deterministic text and says so |
| localStorage throws | Memory features silently off; core still works |
| Clean city (AQI 20) | Verdict "a good day to open up"; the kitchen card becomes the lead, since the household's own source now dominates |
| Desktop | Same content, max-width 1100, two columns at ≥ 900px |
| 320px | Numbers shrink, labels wrap; no horizontal scroll |
| Screen reader | Day band exposed as a sentence; every action in a real list |
| One-person household | "Amma carries the most" becomes "you carry all of it"; copy degrades honestly |

## Signature details (what stops it being generic)

- The day band, with cooking markers. Unique, and it argues the thesis.
- Per-person dose expressed as **"X µg today"**, plus the cigarette analogy in
  Level 3 only — visceral numbers belong behind a tap, not on the first screen.
- The verdict is a **sentence in the imperative**, not a metric with a label.
- Typography does the hierarchy: serif for the verdict, mono for figures,
  sans for labels. No boxes, no cards beyond the two entries.
- The accent colour is the AQI category, so the page *is* the air.
