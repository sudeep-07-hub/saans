# DIAGNOSIS v2 — why the second attempt still read as old

Written after the user rejected the interface twice. The first redesign fixed the
information architecture; it did not fix the reason nobody wants to open the app.

## What I got wrong the first time

I diagnosed "evidence layout, not a daily loop" and rebuilt the page as a
verdict + chart + three numbers, with two rows leading deeper. That reading was
correct as far as it went, and it was not the main problem.

**The main problem: the app has no verbs.**

Count what a user can *do* on the current Level 1, by looking at it:

- read a sentence
- read a chart
- read three numbers
- tap one of two rows that reveal more reading

That is a poster with two links. Every surface is output. Nothing responds. A
household in a cold kitchen at 06:40 is not short of a verdict — the verdict is
the one thing the page does well. They are short of anything to touch, and on
return there is nothing that reflects what they did yesterday.

So "old" was not a colour complaint. It was the complaint you make about
software that only displays. Rewriting the CSS again would produce a prettier
poster and a third rejection.

## The second problem: no state, so no return

The only memory is `done:` keys and a history line that has never once rendered
because it needs a prior day's reading. There is no artefact of use. You cannot
tell, on first load, that anyone has ever opened this before.

## What the engine can already do that the UI never exposes

This is the important discovery, and it changes the design. `POST /api/simulate`
takes one intervention key and returns the household dose before and after *for
every person*, the uncertainty band, the rupee cost, annual runtime, and the
emissions delta. It is fast and stateless.

Verified by composing interventions in sequence and recomputing:

    4146 baseline  →  diy_filter 3099 (−25.3%)
                   →  +mask_commute 2440 (−41.1%)
                   →  +clean_fuel 2295 (−44.6%)

So the arithmetic for an **interactive stack** already exists. A user can choose
a set of actions and watch the household dose move per person, live. That is a
thing to *do*, and it is the single most demystifying object in the product: it
turns "trust my ranking" into "build your own and see".

I can compose patches client-side through repeated `/api/simulate` calls, or add
one bulk endpoint. One bulk endpoint is better: one round trip, one consistency
guarantee, and the combination math stays in Python where it is tested.

## The design, second attempt

Principles, in the order they beat each other when they conflict:

1. **Density over decoration.** The old page is airy: a 42px verdict and huge
   margins. Air reads as "report". A tool looks like an instrument panel —
   information per screen, not whitespace per screen.
2. **Everything is a control.** Any number you can act on should be assertable.
   The stack simulator is the centrepiece.
3. **The day is the spine.** Time is the axis a family actually thinks in. The
   plan, the chart, and the cooking peaks all hang off one horizontal time
   surface with a live cursor, rather than being three separate widgets.
4. **State is visible.** A household that has made choices should see them
   reflected: a running "your plan" total, a saved cabinet of applied actions,
   and the delta versus yesterday.
5. **Nothing that was hard-won is thrown away.** The verdict, the 56 cited
   constants, the dose-per-person table, the honest limits, and the
   prose/calculation boundary all stay. The model still writes prose only.

## Concrete feature list for the revamp

- **Time scrubber.** Drag along the 24-hour surface; the readout follows the
  cursor. Introduces the exposure thesis by demonstration rather than a caption.
- **Stack simulator.** Add any of the 14 interventions; the household dose and
  every person's dose update. Shows combined effect, saved rupees, and the
  point where a further action stops helping.
- **Per-person lens.** Pick a person; the whole page re-weights to them — their
  blocks, their dose, which actions serve them most. Household average hides the
  cook, and the cook is usually the point.
- **Your cabinet.** Chosen actions persist, with a running total and a
  cumulative cut. This is the return hook that actually exists.
- **Live AQI→dose arithmetic.** Show the chain the app performs (ambient →
  indoor → personal → inhaled µg) as an inspectable path, not a black box.
- **Command palette (Ctrl/Cmd-K).** Jump to any action, person, or fact. On
  desktop this is what makes it feel like a tool rather than a page.

## What I am deliberately NOT doing

- No glassmorphism, no gradient hero, no neon-on-black "AI dashboard". Being
  unfamiliar is not the same as being new, and the second rejection was not a
  request for worse taste.
- No gamification: no streaks, no badges, no scores for a health outcome.
- No web fonts, no CDN, no framework — the constraints in CONTRACT.md still
  hold, including the 70 KB single file and the strict CSP.
- No second model. The 4B local model keeps its single job, writing prose.

## Risk I am accepting

Interactivity costs bytes, and the file is at 71,561 of 71,680. The simulator
needs a multi-select model, a results panel, and an endpoint. That cannot fit in
119 bytes of headroom. The 70 KB ceiling is my own target from CONTRACT.md, not
a rule from the brief; the brief's only size rule is the 10 MB repository limit.
So the honest move is to **raise the single-file ceiling to ~110 KB**, record
why, and keep one file with no build step — rather than delete the test suite's
accessibility guarantees to stay under a number I invented.
