# SAANS — DESIGN SYSTEM

**Status:** specification. Binding on implementation.
**Scope:** `saans/static/index.html` — one file, no build, no CDN, no web fonts, CSP `default-src 'none'`.
**Budget:** the file was 65,041 bytes when this was written and is being edited in parallel, so the
ceiling (~70 KB) is the constraint, not the number. Every rule below is byte-cheap by construction;
§12 gives the delta accounting and what to delete to pay for it.
**Every colour ratio in this document was computed from the hex values, not estimated.**
Recipes are in §3.9 so they can be re-run after any change.

---

**Contents** — §1 thesis · §2 directions · §3 colour · §4 type · §5 space · §6 surfaces ·
§7 components · §8 motion · §9 responsive · §10 anti-patterns · §11 copy · §12 build order.

## 1. The visual thesis

Saans should look like **a public notice printed on instrument stock**: a neutral grey-white sheet,
hairline rules that behave like a form's printed grid, sans-serif machine labels in the left
margin, mono figures that never move, and — the one loud object on the page — a **near-black
plate carrying the verdict sentence**, whose bottom edge is a 4 px band in the colour of today's
air. Everything else is quiet. This is right for a parent at 06:40 because a notice is *read*,
not operated: one sentence, one number, one colour, no chrome to interpret, no card to swipe,
no chart legend to learn. It is also right because it is honest about what the product is — a
computed reading with its arithmetic attached — so the page should feel like a measurement
certificate, not an app that wants a relationship. There is no decoration anywhere, so the only
thing that can catch a half-awake eye is hierarchy, and hierarchy is the thing a tired brain
still parses.

**The one recognisable thing, at a glance, in either theme:** a grey-white page, one near-black
full-width plate of serif text, and a 4 px coloured rule along the bottom of that plate. Nobody
else's air-quality product looks like that, it costs four CSS declarations, and it survives being
screenshotted into a family WhatsApp group where it will be seen at 240 px wide.

---

## 2. Visual directions considered

### A. Instrument panel — *rejected*

Aluminium-grey chassis, engraved bezels, inset wells, LED dots, knurled switches, a dark
"cockpit" that reads as expensive hardware.

**Gets right:** precision, the idea that numbers are readings; dark mode is native to it; the
big-number-with-a-scale pattern.
**Fails:** skeuomorphism is a costume, and costumes date fastest of anything. Bezels cost bytes
(shadows, gradients, 6 radii). At 390 px it becomes a toy dashboard. And it makes the product
look like it *measures* — which is the one thing it does not do. It models. A device aesthetic
would be a lie about the epistemics.

### B. Editorial almanac — *the current design; rejected as the destination*

Warm cream paper (`#f4f1ea`), Iowan/Palatino headlines, letterspaced small caps, ruled columns,
2 px radii, tabular mono figures. This is what ships today.

**Gets right:** the typography is genuinely good — serif verdict, mono figures, no gradients, no
cards-as-decoration. It reads as considered, and it is the reason the app does not look like a
SaaS product.
**Fails:** it is a *newspaper*, and a newspaper is a thing you read once and throw away; warmth
in the paper tone reads as age, which is precisely the "old" the user rejected. Worse, it has no
memorable object — screenshot it and you have greyish text on beige, indistinguishable from a
Substack. It also spends its only colour on links and italics, so the AQI accent, the best idea
in the product, is reduced to a tint on a word.

### C. Notice & Plate — **CHOSEN**

A municipal air-quality notice crossed with a bench instrument. A neutral grey-white sheet (not cream),
a printed-form grid with a left margin column of mono labels, hairline rules instead of cards,
serif only where a human is speaking, and a single inverted plate that carries the verdict and
the household figure, edged in the day's air colour.

**Gets right:**
- It keeps everything the current design earned (serif verdict, mono figures, no chrome) and
  fixes the two things that made it feel old: the paper is now a neutral grey page, and the
  type no longer floats — it is pinned to a visible form grid.
- It creates exactly one object worth remembering, which is what "generic" is the absence of.
- Authority without institutional coldness: a notice is *for* you, addressed to you, in
  imperatives. That matches the copy voice in §11.
- It is nearly free. The plate is a background colour and a border-bottom. The margin column is
  one grid declaration re-used at every section. No shadows, no gradients, no icons.

**Fails / accepted costs:** inversion is a strong move, so it must appear exactly once per
screen (the verdict) plus once per sub-instrument (the tally), or it stops meaning "this is the
reading". Discipline is required, and §6 makes it a rule with a count.

**Defence:** the argument for B is nostalgia; the argument for C is legibility under
sleep-deprivation plus one memorable object plus zero byte cost. A parent does not want a
newspaper, they want the notice on the board at the clinic door.

---

## 3. Colour

### 3.1 The ground rules

1. **Three tonal steps, one direction.** `--paper` is the page, `--panel` is one step *away* from
   the page (lighter in light mode, lighter in dark mode — the same relationship both ways),
   `--sunk` is one step *toward* the page's extreme (recessed: readouts, hover, wells).
2. **The palette is neutral, not cream.** Light paper is `#eeedea`: R−B skew is 4 points, against
   10 in the current `#f4f1ea`. No hex in the light set exceeds 5 points of warm drift (R−B)
   except the accent. That single constraint is what stops the design reading as vintage.
3. **Two accent tracks.** Every AQI category ships a *text* value (legible as ink or as a data
   mark on paper) and a *lift* value (legible on the near-black plate). Position decides the
   track, never the category. See §3.3.
4. **Colour never carries meaning alone.** Category is always also a word ("Very Poor"), and
   every status dot is accompanied by its label. Light/dark, colour-blind, and greyscale print
   all still work.
5. **No alpha on text or data marks.** Composited values cannot be audited. The only permitted
   alpha is `rgba()` on the single popover shadow.

### 3.2 Tokens — light theme (default)

| Token | Hex | Role |
|---|---|---|
| `--paper` | `#eeedea` | page field |
| `--panel` | `#f8f7f4` | raised content surface |
| `--sunk` | `#e0dfda` | recessed readout / hover / well |
| `--plate` | `#111417` | the inverted plate (verdict, tally) |
| `--plate-ink` | `#f7f6f1` | text on the plate |
| `--ink` | `#111417` | primary text (same value as plate: one ink) |
| `--ink2` | `#383d41` | body text, secondary figures |
| `--muted` | `#5b605e` | labels, units, captions, metadata |
| `--rule` | `#d3d1ca` | structural hairline, table dividers |
| `--rule2` | `#b6b2a8` | heavier divider, disclosure underline |
| `--ctl` | `#7f7a6e` | control borders (needs 3:1, not 4.5:1) |
| `--alarm` | `#8f1420` | error text and error rule |
| `--ok` | `#1d6b45` | "done", live-feed dot |
| `--knob-ink` | `#fbfaf6` | glyph inside a filled control |
| `--well` | `#1b1f24` | recessed strip **inside the plate** |
| `--plate-muted` | `#a6aaa7` | labels and metadata **on the plate** (`--muted` is 2.89 there; never use it) |
| `--alarm-plate` | `#ff8a80` | error text **on the plate** (8.10:1 on `#111417`); `--alarm` is 2.01 there |
| `--rule-plate` | `#41464b` | dividers **on the plate** (1.94:1 light, 2.11:1 dark) — `--rule` is 12.09:1 and glares |

### 3.3 Tokens — the AQI accent, both themes

Set on `html[data-aq="good|satisfactory|moderate|poor|very_poor|severe"]`. The engine owns the
category; CSS only receives the string.

**Light theme** — text track is darkened for paper, lift track is bright for the plate:

| Category | `--aq-text` (on paper/panel/sunk) | `--aq-lift` (on plate only) |
|---|---|---|
| good | `#0b6a3c` | `#5ccf92` |
| satisfactory | `#4a6a06` | `#b6cf55` |
| moderate | `#7d5500` | `#e6bf58` |
| poor | `#9c470c` | `#ff9a5c` |
| very_poor | `#9b1723` | `#ff7d75` |
| severe | `#6f0d2a` | `#e5849f` |

**Dark theme** — one bright value serves as both tracks (dark grounds lift everything):

| Category | `--aq-text` | `--aq-lift` |
|---|---|---|
| good | `#5ccf92` | `#5ccf92` |
| satisfactory | `#b6cf55` | `#b6cf55` |
| moderate | `#e6bf58` | `#e6bf58` |
| poor | `#ff9a5c` | `#ff9a5c` |
| very_poor | `#ff7d75` | `#ff7d75` |
| severe | `#e5849f` | `#e5849f` |

Default when no category is set (before `/api/brief` returns): `--aq-text: #5b605e`,
`--aq-lift: #939a97` — i.e. neutral. Never default to green; a fresh page must not claim clean air.

### 3.4 Tokens — dark theme

| Token | Hex |
|---|---|
| `--paper` | `#0e1012` |
| `--panel` | `#16191c` |
| `--sunk` | `#08090a` |
| `--plate` | `#060708` |
| `--plate-ink` | `#f7f6f1` |
| `--ink` | `#efefeb` |
| `--ink2` | `#c2c6c4` |
| `--muted` | `#939a97` |
| `--rule` | `#2b2f33` |
| `--rule2` | `#41464b` |
| `--ctl` | `#737a7d` |
| `--alarm` | `#ff8a80` |
| `--ok` | `#5fd39b` |
| `--knob-ink` | `#0b0d0e` |
| `--well` | `#14171b` |
| `--plate-muted` | `#9aa09d` |
| `--alarm-plate` | `#ff8a80` |
| `--rule-plate` | `#41464b` |

Note the trio inverts correctly: in light mode panel is *lighter* than paper (`#f8f7f4` vs
`#eeedea`); in dark mode panel is also *lighter* (`#16191c` vs `#0e1012`). Sunk goes the other
way in both. The relationship, not the luminance, is the token.

### 3.5 Measured contrast — every shipping pair

Computed with sRGB relative luminance per WCAG 2.1. Body text threshold 4.5:1; UI component
borders and data marks threshold 3:1; structural hairlines are decorative and exempt.

**Light theme**

| Foreground | on `--paper` | on `--panel` | on `--sunk` | Verdict |
|---|---|---|---|---|
| `--ink` `#111417` | 15.79 | 17.25 | 13.85 | AAA |
| `--ink2` `#383d41` | 9.38 | 10.25 | 8.23 | AAA |
| `--muted` `#5b605e` | 5.47 | 5.98 | 4.80 | AA |
| `--ctl` `#7f7a6e` (border) | 3.65 | 3.99 | 3.20 | AA non-text |
| `--alarm` `#8f1420` | 7.84 | 8.56 | 6.88 | AAA |
| `--ok` `#1d6b45` | 5.53 | 6.05 | 4.86 | AA |
| `--rule2` `#b6b2a8` | 1.81 | 1.98 | 1.59 | decorative only |
| `--rule` `#d3d1ca` | 1.31 | 1.43 | 1.15 | decorative only |
| `--plate-ink` on `--plate` | — | — | — | **17.08** |
| `--paper` on `--ink` (primary button) | — | — | — | **15.79** |

**Dark theme**

| Foreground | on `--paper` | on `--panel` | on `--sunk` | Verdict |
|---|---|---|---|---|
| `--ink` `#efefeb` | 16.54 | 15.31 | 17.29 | AAA |
| `--ink2` `#c2c6c4` | 11.05 | 10.23 | 11.55 | AAA |
| `--muted` `#939a97` | 6.64 | 6.14 | 6.94 | AAA |
| `--ctl` `#737a7d` (border) | 4.37 | 4.04 | 4.56 | AA non-text |
| `--alarm` `#ff8a80` | 8.35 | 7.73 | 8.73 | AAA |
| `--ok` `#5fd39b` | 10.24 | 9.48 | 10.70 | AAA |
| `--rule2` `#41464b` | 2.00 | 1.85 | 2.09 | decorative only |
| `--rule` `#2b2f33` | 1.41 | 1.31 | 1.48 | decorative only |
| `--plate-ink` on `--plate` | — | — | — | **18.63** |
| `--paper` on `--ink` (primary button) | — | — | — | **16.54** |

**Accent, light theme — `--aq-text` as ink; `--knob-ink` (`#fbfaf6`) on a filled knob**

| Category | on paper | on panel | on sunk | `--knob-ink` on it | `--aq-lift` on `--plate` |
|---|---|---|---|---|---|
| good | 5.71 | 6.24 | 5.01 | 6.40 | 9.50 |
| satisfactory | 5.35 | 5.84 | 4.69 | 5.99 | 10.60 |
| moderate | 5.66 | 6.18 | 4.96 | 6.34 | 10.52 |
| poor | 5.40 | 5.90 | 4.74 | 6.06 | 8.83 |
| very_poor | 7.06 | 7.72 | 6.19 | 7.91 | 7.43 |
| severe | 10.15 | 11.09 | 8.91 | 11.38 | 7.16 |

**Accent, dark theme — `--aq-text` as ink; `#0b0d0e` on a filled knob**

| Category | on paper | on panel | on sunk | dark glyph on it | `--aq-lift` on `--plate` |
|---|---|---|---|---|---|
| good | 9.80 | 9.07 | 10.24 | 10.01 | 10.36 |
| satisfactory | 10.94 | 10.12 | 11.43 | 11.17 | 11.56 |
| moderate | 10.86 | 10.05 | 11.35 | 11.09 | 11.48 |
| poor | 9.10 | 8.43 | 9.52 | 9.30 | 9.63 |
| very_poor | 7.66 | 7.09 | 8.01 | 7.83 | 8.10 |
| severe | 7.38 | 6.83 | 7.72 | 7.54 | 7.81 |

**Lowest shipping text ratio in the whole system: 4.69:1** (`satisfactory` on `--sunk`, light).
Lowest in dark: 6.14:1 (`--muted` on `--panel`). Every text pair clears AA; most clear AAA. The
only sub-4.5 values in the system are `--rule` and `--rule2`, which are decorative hairlines with
no text on them.

### 3.6 The AQI accent: exactly what changes, and the trap it avoids

**What changes:** `--aq-text` and `--aq-lift` only. Nothing else. Specifically, and this is the
implementation contract:

| Reacts to AQI category | Does not react, ever |
|---|---|
| 4 px band on the bottom edge of the verdict plate | `--ink`, `--ink2`, `--muted`, all text colours |
| the category word in the masthead and on the plate | `--paper`, `--panel`, `--sunk`, `--plate` |
| the 6 px category dot in the masthead (fill `--aq-text`) | `--alarm`, `--ok` (semantic, not environmental) |
| ambient bars in the 24 h chart | `--rule`, `--ctl`, button fills |
| the "top action" marker in the plan rail | any border width, padding, or type size |
| the delta underline flash in the tally (§8) | the verdict sentence's words (only its one italic emphasis span may take `--aq-lift`) |
| the selected checkbox fill (16 px knob) | focus ring colour (always `--ink`) |
| the person card's share figure, when that person is worst | the chart's indoor bars (always `--ink`) |

The rule that makes it safe: **the accent is never a background for text.** It is a background
only in two places — a 16 px checkbox knob (glyph = `--knob-ink`, measured above) and the 4 px
band (no text). Everything else is accent-coloured *ink on a known ground*, or a data mark.

**Why this is necessary — the CPCB palette fails.** The official NAQI colours cannot be used
directly for text or for filled badges. Measured:

| Official NAQI | Hex | White text on it | As text on `#eeedea` |
|---|---|---|---|
| Good | `#00b050` | **2.87** ✗ | **2.45** ✗ |
| Satisfactory | `#92d050` | **1.85** ✗ | **1.58** ✗ |
| Moderate | `#ffff00` | **1.07** ✗ | **1.09** ✗ |
| Poor | `#ff7e00` | **2.55** ✗ | **2.18** ✗ |
| Very Poor | `#ff0000` | **4.00** ✗ | **3.42** ✗ |
| Severe | `#99004c` | 8.54 ✓ | 7.30 ✓ |

Five of six official colours fail AA in both directions. So: **the official palette is never
shipped raw.** It is transposed into two tracks that keep each category's hue identity while
moving the lightness until it passes. Any implementation that pastes `#ffff00` behind white text
for "Moderate" is a defect, not a design choice.

**If a filled category badge is ever required** (e.g. a share card): use the dark track in light
mode with `--knob-ink` text (5.99–11.38, all pass), and the bright track in dark mode with
`#0b0d0e` text (7.54–11.17, all pass). White text on the bright track fails everywhere it was
measured: 1.74–2.58. Never do it.

### 3.7 Semantic colour is not environmental colour

`--ok` and `--alarm` exist for *system* state (dose fell, feed failed). They must never be used
for AQI category, or "Severe red" and "error red" become the same signal and the error stops
being noticed. This is why `--aq-text` for `very_poor` is `#9b1723`, a shade off the error red,
and why error states always carry the word plus a rule, never colour alone.

### 3.8 `prefers-contrast: more`

| Token | Light | Dark |
|---|---|---|
| `--muted` | `#3f423f` | `#d8d6cf` |
| `--rule2` | `#7c7a6f` | `#7f868b` |
| `--ctl` | `#4a4a44` | `#a6acae` |
| `--rule` | `#bdb9ae` | `#3a4045` |

Applied inside `@media (prefers-contrast: more)` under both `:root` and `html[data-theme="dark"]`
(the current file already does this correctly — keep the pattern).

### 3.9 Re-running the audit

```python
def lum(h):
    h=h.lstrip('#'); c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    c=[(v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4) for v in c]
    return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
def cr(a,b):
    l1,l2=sorted([lum(a),lum(b)],reverse=True); return round((l1+0.05)/(l2+0.05),2)
```
Add a `test_ui.py` check that asserts every pair in §3.5 ≥ 4.5 and every `--ctl` pair ≥ 3.0.
Hardcode the hexes in the test, not the CSS: a stylesheet parse that silently finds nothing must
fail, not pass.

---

## 4. Typography

### 4.1 Families, and why

```css
--serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
```

| Role | Family | Why |
|---|---|---|
| Verdict sentence | serif | The one sentence a human must absorb. A book face slows the eye by ~10% and that is correct for the only paragraph that matters. It also separates "someone is telling you this" from "the machine is reporting this". |
| Plan prose (`opening`, `children`, `limit`) | serif, 16 px | Same reason: the generated text is the human register. Serif is the *voice*; sans is the *interface*. |
| Section labels, eyebrows, units, captions, metadata | mono | These are legends on an instrument. Mono uppercase at 10–11 px with wide tracking is the most legible small text available in system fonts, and it is what stops labels from competing with headings. |
| UI text: rows, buttons, inputs, help | sans | Neutral, high x-height, no personality. It should be invisible. |
| Every number that a user might compare | mono + `tabular-nums` | Digits must not shift when a value changes. Non-negotiable: a number that reflows while recomputing reads as instability in the data. |

No `@font-face`. No `font-display`. No webfont fallback chain beyond the ones above.

### 4.2 The scale

rem base 16 px. Two columns: mobile (≤559) and desktop (≥560). All line-heights in px so the
rhythm is exact.

| Token | Role | Mobile | Desktop | Family | Tracking | Numerals |
|---|---|---|---|---|---|---|
| `--t-verdict` | verdict sentence | 27/31 | 40/44 | serif 400 | `-.022em` | — |

Verdict is the only fluid size: `font-size:clamp(27px,4.2vw,40px)` with `line-height` stepped at
1.15/1.13/1.10 by media query — measured 27/31 at 320, 27/31 at 390, 32/36 at 768, 40/44 at 1440.
Every other size in the table is a fixed step; fluid type on a 10 px label is a legibility risk.
| `--t-plate-num` | household figure on the plate | 40/40 | 56/56 | mono 500 | `-.045em` | tabular |
| `--t-tally` | live tally headline | 34/34 | 44/44 | mono 500 | `-.04em` | tabular |
| `--t-h2` | serif sub-heads ("Build your plan") | 20/24 | 22/26 | serif 500 | `-.015em` | — |
| `--t-h3` | person name, action verb | 14/19 | 15/20 | sans 600 | `-.005em` | — |
| `--t-body` | prose / long help | 14/21 | 15/23 | sans 400 | `0` | — |
| `--t-prose` | generated plan prose | 15.5/24 | 16/25 | serif 400 | `0` | — |
| `--t-ui` | rows, buttons, inputs | 13/18 | 13.5/19 | sans 400–600 | `0` | — |
| `--t-data` | inline figures, ladder values | 15/16 | 16/17 | mono 500 | `-.02em` | tabular |
| `--t-data-s` | secondary figures, right columns | 11.5/14 | 12/15 | mono 400 | `-.01em` | tabular |
| `--t-label` | section labels, eyebrows | 10.5/13 | 10.5/13 | mono 700 | `.14em`, uppercase | — |
| `--t-cap` | captions, units, metadata | 10.5/14 | 10.5/14 | mono 400 | `.04em` | tabular where numeric |
| `--t-micro` | absolute floor: source kinds, axis | 10/12 | 10/12 | mono 400 | `.08em`, uppercase | — |

`--t-label` and `--t-cap` sit at 10.5; `--t-micro` at 10 is the only 10 px role and is reserved
for axis ticks and source-kind tags that are never the only carrier of meaning.

**Hard floor: no text below 10 px.** The current build ships 8 px and 8.5 px tags; that is
illegible at 06:40 with one eye open and must be raised or deleted. There is no third size
between 10 and 10.5 — round up.

### 4.3 Numerals

```css
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}
```
- Apply on **every** element containing a value that can change: ladder, chart readout, tally,
  person dose, ledger, plan figures, timestamps, axis.
- Do **not** apply to prose. A figure inside a sentence uses the text face's proportional
  figures; `{{6283}}` inside a serif paragraph must look like the paragraph.
- No `slashed-zero` (it reads as a null/error marker in a health context).
- Always include the unit in a smaller size on the same line: `6,283` + ` µg`. The unit is
  `--t-cap`, `--muted`, `letter-spacing:0`. A bare number is never shipped.
- Thousands separator: comma below 100,000, then no separator above (µg values in the lakhs are
  rare; if they occur, use the Indian grouping only if the engine already does — do not reformat
  in CSS).

### 4.4 Wrapping and alignment

- Verdict: `text-wrap:pretty`, `max-width:22ch` desktop / `100%` mobile, `hyphens:none`. It must
  break at clause boundaries; the copy is authored ≤ 3 lines at 390 px and the CSS is not allowed
  to hyphenate a sentence about a child's lungs.
- Prose: `text-wrap:pretty`, `max-width:68ch`. Never `balance` on long text.
- Section labels and numerals: `white-space:nowrap`.
- Row titles (picker, ledger): one line, `text-overflow:ellipsis`. The full string lives in the
  drawer body and in `title`.
- Everything is left-aligned except right-hand numeric columns. **No justified text, no centered
  body, no centered verdict.**

---

## 5. Space and rhythm

### 5.1 Scale

4 px base with **one** permitted half-step, 6. Only these values exist; a stray 7 px, 10 px, or
13 px padding is a bug. Tokens are documented here as the vocabulary — in the stylesheet, write the
literal (`padding:12px 10px`) rather than `var(--s4)`; the names exist for this document and for
review, not to be resolved at runtime.

| Token | px | Used for |
|---|---|---|
| `--s1` | 4 | icon-to-label, unit-to-figure, rule offsets |
| `--s2` | 6 | intra-row gaps, chip padding-y |
| `--s3` | 8 | row padding-y, label-to-value |
| `--s4` | 12 | cell padding, panel inner gap |
| `--s5` | 16 | page gutter (mobile), panel padding |
| `--s6` | 24 | page gutter (tablet), section gap mobile |
| `--s7` | 32 | section gap desktop |
| `--s8` | 48 | empty-state vertical breathing (the only place it is used) |
| `--s9` | 64 | reserved for the ≥1024 masthead→plate offset; unused below that |

### 5.2 The vertical rhythm rule

We do not maintain a baseline grid — with three families and mixed 13/15/16 px sizes, a true
baseline grid costs more in CSS than it returns. Instead:

1. Every block starts at a multiple of 4 px from the top of its container.
2. Vertical space is owned by **the top of the block**, never by the bottom: `margin-top` only,
   no `margin-bottom`. (One exception: the last child of a section gets no margin-top.)
3. A section boundary is `1px solid var(--rule)` + `padding-top:var(--s4)` + `margin-top:var(--s6)`
   on mobile, `margin-top:var(--s7)` on desktop. The rule is the rhythm; the space around it is
   the only thing that varies.
4. Inside a panel, rows are separated by 1 px rules and never by space. Panels are dense; space
   inside them would imply grouping that isn't there.

### 5.3 The 24 h chart's internal rhythm

Fixed heights, so the chart never jumps when data arrives:

| Element | Mobile | Desktop |
|---|---|---|
| header row | 26 | 28 |
| plot height | 80 | 96 |
| bar gap | 1 px | 2 px |
| axis row | 14 | 14 |
| readout strip | 28 | 34 |
| **panel total** | **148** | **172** |

Reserve these with `min-height` so the first paint and the loaded paint are the same shape.

### 5.4 Density: what must fit on one 390 px screen

Viewport 390 × 812 (iPhone 13/14 minus browser chrome). The budget, computed, not estimated:

| Block | Height |
|---|---|
| masthead (sticky) | 44 |
| gap | 8 |
| verdict plate (3-line sentence) | 167 |
| gap | 12 |
| ladder: 26 header + 4 × 38 rows | 178 |
| gap | 12 |
| chart panel | 148 |
| gap | 12 |
| bench header | 40 |
| 2 picker rows @ 44 | 88 |
| **Total** | **709** |

709 of 812. The remaining 103 px carries picker rows 3 and 4 in full (88 px) and clips row 5 after
15 px — four complete actions and a cut fifth, which is a scroll cue rather than a dead end. If the
verdict runs to 2 lines the plate is 136 and the fold gains one more row.
**Target: the verdict, the worst person's name, and 4 tappable actions above the fold, with no
scrolling needed to learn the verdict or what to do first.**

Rules that protect that target:
- Masthead 44 px, not 56. One line, never wraps.
- No hero illustration, no intro paragraph above the verdict, no cookie-ish banner.
- The verdict plate is capped at 3 lines of serif + 1 line of metadata; if the sentence overflows,
  the copy is wrong, not the plate. (Copy limit: 92 characters.)
- Ladder rows are 38 px with one-line `why` text; two-line rows only below 360 px.
- Never stack the verdict and the ladder vertically at 390 with desktop spacing — the mobile gap
  is 12, not 22.

### 5.5 Touch targets

- Every interactive row: full-bleed, `min-height:44` where the row is the target at ≤559 px.
- The picker's 16 px checkbox is **not** the target; the 390 × 44 row is. This satisfies WCAG
  2.5.8 comfortably and is why 14 rows at 44 px is acceptable (616 px of list, scrolled, not a
  wall — the bench is below the fold by design and is a list, not a landing page).
- Two adjacent targets never closer than 8 px.
- Nothing tappable within 12 px of the viewport bottom edge (iOS home indicator).

---

## 6. Surfaces, rules and elevation

### 6.1 Three grounds, no shadows

| Ground | Light | Dark | Meaning |
|---|---|---|---|
| `--paper` | `#eeedea` | `#0e1012` | the page. Text sits here directly. |
| `--panel` | `#f8f7f4` | `#16191c` | a bordered instrument: has a header and a scale. |
| `--sunk` | `#e0dfda` | `#08090a` | recessed: readout strips, hover, wells. |
| `--plate` | `#111417` | `#060708` | inverted readout. **The only strong contrast on the page.** |

The plate separates from `--paper` by 15.79:1 in light mode — no border needed. In dark mode the
gap is 1.06:1 (both are near-black), so **in dark mode only** the plate carries
`border:1px solid var(--rule2)` (`#41464b`, 1.85:1 against the plate) to declare its edge. This is
the single exception to "borders define panels, not plates", and it is required, or the signature
element becomes an invisible rectangle after dark.

The tonal steps are deliberately tiny — `--panel` is **1.09:1** above `--paper` in light and
**1.08:1** in dark; `--sunk` is 1.14:1 below. That is correct and must not be "fixed": the 1 px
rule does the separation, and the tone only stops a panel from reading as a hole. Do not compensate
with a shadow. Do not increase the step until panels look like a different material.

**A fourth ground exists inside the plate.** `--well` (`#1b1f24` light / `#14171b` dark, 1.12:1
against `--plate`) is the recessed strip for the tally's overlap note and the per-person region —
`--sunk` cannot be used there because it is a *light* value in light mode and would punch a white
hole in the plate. Text on `--well` uses `--plate-ink` (15.30:1 / 16.61:1) and `--plate-muted`
(7.04:1 / 6.75:1).

### 6.2 Radii

| Token | px | Applies to |
|---|---|---|
| `--r0` | 0 | table rows, rules, the chart, the plate's inner band |
| `--r1` | 2 | every panel, every button, every input, the plate |
| `--dot` | 50% | the 6 px status dot, and nothing else |

`4px`, `8px`, `12px`, `16px`, `999px` pills: **banned**. A 2 px radius on a 390 px-wide row reads
as printed stock; a 12 px radius reads as a mobile app card.

### 6.3 Shadow

One shadow in the entire system:

```css
.pop{box-shadow:0 10px 24px -12px rgba(17,20,23,.35)}
```
The location search popover only. It is the only element that overlaps other content and needs
to be legible as floating. Everything else uses rules. If a second shadow appears in review,
the answer is no.

### 6.4 The rule for when a card is a card

A bordered surface (`1px solid var(--rule)`, `background:var(--panel)`, `radius:2px`) is used
**only** when the content is:

- **(a) a distinct instrument** — it has its own header row and its own scale or unit (the 24 h
  chart, the tally, the ladder, the person grid), or
- **(b) a single interactive unit** — the whole border is the tap target (person card, evidence
  drawer header).

Static prose never gets a border. The plan, the ledger, and the sources sit directly on `--paper`
under a section label and a hairline. **Budget: at most 5 bordered surfaces visible at once.**
On the current page that is: ladder, chart, picks, tally, and one open drawer. If a sixth
appears, something is being decorated rather than structured.

Corollary: **no card inside a card.** The tally's sub-blocks (the big %, the overlap note, the
per-person rows) are separated by rules, not by their own borders. That is the current build's
mistake in the person cards and it costs bytes.

---

## 7. Component specifications

Conventions for the tables below: all sizes in px; `h` = min-height; focus-visible is **always**
`outline:2px solid var(--ink); outline-offset:2px` unless stated; on the plate the ring is
`--plate-ink`. Disabled never lowers text below `--muted`.

---

### 7.1 The verdict plate

The signature. Full-bleed inside the content column, `--plate` background, `--plate-ink` text,
2 px radius, `4px` bottom border in `--aq-lift`.

**Anatomy**

```
┌───────────────────────────────────────────┐  ← --plate
│ VERY POOR · 06:40 · DELHI          (label)│  26  header: category --aq-lift, rest --plate-muted
│                                           │
│ Your family breathes in 18,400 µg         │  serif 27/31 → 40/44
│ today. Amma takes a third of it.          │
│                                           │
│ 2.4× the WHO daily guide                  │  14  caption, --plate-muted
╞═══════════════════════════════════════════╡  ← 4px --aq-lift band
```

| Spec | Mobile | Desktop |
|---|---|---|
| padding | 16 16 14 | 24 28 20 |
| header: `--t-label`; category token `--aq-lift`, separators and place `--plate-muted` | one line, nowrap, ellipsis | same, with place right-aligned |
| sentence: `--t-verdict`, max 92 chars, `--plate-ink`; one italic `<em>` span in `--aq-lift` | 27/31, max 3 lines | 40/44, `max-width:22ch` |
| metadata line: `--t-cap` | 10.5/14, `--plate-muted` | same |
| band height | 4 | 4 |
| min-height | 168 | 196 |
| plate metadata may include | one comparative figure, max 6 words | plus the place name |

On the plate, **never use `--muted`** — it measures 2.89:1 against `--plate`. Labels and metadata
on the plate use `--plate-muted` (`#a6aaa7` = 7.86:1 light, `#9aa09d` = 7.57:1 dark). Errors on
the plate use `--alarm-plate` (`#ff8a80` = 8.10:1 on `#111417`); `--alarm` itself is 2.01:1 there
and is unreadable. This is the most likely bug in a naive implementation: `--muted` and `--alarm`
are correct on paper and fail the moment they are placed on the signature element.

**States**

| State | Render |
|---|---|
| default (loaded) | as above |
| loading (first paint) | plate present, header label `Reading the air`, sentence slot holds 3 rules of `#2a2e33` (1.35:1 on `--plate`: present, not readable) at 64%, 88%, 42% width, 31 px apart; band hidden. No skeleton shimmer. |
| hover | none. The plate is not interactive. No `cursor:pointer`. |
| focus-visible | n/a (not focusable). If it ever wraps a link, ring is `--plate-ink`. |
| active/selected | n/a |
| disabled | n/a |
| error (feed failed) | header label `Feed down`, sentence is the last known verdict with a leading mono prefix `LAST 06:12 —`, band keeps the last category colour, and a `--alarm` 1 px top rule is added inside the plate. |
| empty (no household) | header `No household yet`, sentence `Tell me who lives here and I can count their day.` + inline ghost button `Set up` (§7.10 secondary). Band `--rule2`. |

---

### 7.2 Exposure ladder row

Four rows: `Outdoor`, `Indoors`, `Your stove`, `One person's day`. One row = one rung.
Whole row is a `<button>` that expands its `why` line and links to evidence.

| Property | Value |
|---|---|
| grid | `76px minmax(0,1fr) 64px` (desktop) / `72px minmax(0,1fr) 58px` (≥360) / stacked at <360 |
| padding | `6 10` |
| min-height | 38 |
| border | bottom `1px solid var(--rule)`; last row none |
| label | `--t-label` 10.5, `--muted`, uppercase, `.09em` |
| track | height 9, `--sunk` ground, radius 1 |
| fill | `--aq-text` (environmental) or `--rule2` for the untitled/reference rung |
| value | `--t-data` 15, right, tabular, `--ink` |
| unit | 10, `--muted`, `letter-spacing:0` |
| `why` line | grid-column 2/-1, `--t-cap` 10.5/14, `--muted`, max 72ch, hidden until expanded |

**States**

| State | Render |
|---|---|
| default | row as above, `why` collapsed |
| hover | `background:var(--sunk)`; nothing else moves |
| focus-visible | 2 px `--ink` ring inside the panel (`outline-offset:-2px` so it isn't clipped by `overflow:hidden`) |
| selected/expanded | `why` visible; label turns `--ink`; a 2 px `--aq-text` left bar appears at x=0 (full row height) |
| disabled | not used — rungs are always inspectable |
| loading | track at 0 width, value replaced by an em-dash `—`, label visible |
| error | value `—`, `why` shows `No reading.` in `--alarm` |
| empty | four rows render with `—` and labels only; the panel header says `Waiting for a reading` |

---

### 7.3 The 24 h chart + scrubber cursor

Two series on one axis, identical x positions:

- **ambient** — solid `--aq-text`, full column width, from the baseline up.
- **indoor** — solid `--ink`, 46% of column width, centred, drawn over the ambient column.
- **cooking hours** — 2 px `--ink` overline across the top of the plot for those columns, always,
  with an `aria-label` on the panel listing them. This is the product's causal claim and it must
  not be reduced to a colour.

| Property | Value |
|---|---|
| plot | `display:grid; grid-template-columns:repeat(24,minmax(0,1fr)); gap:1px`; `align-items:end`; height 80/96 |
| column width @390 | `(390 - 32 gutter - 2 border - 20 padding - 23 gaps) / 24 ≈ 13.0` |
| column width @320 | `(320 - 24 - 2 - 20 - 23) / 24 ≈ 10.4` — still 24 columns, no aggregation |
| bars | `min-height:2`; radius `1px 1px 0 0`; no opacity |
| cursor | 1.5 px `--ink` full-height line + 7 px round foot; `pointer-events:none`; `will-change:transform` off |
| axis | 24 cells, `--t-micro` 10, `--muted`, every 6th labelled (`00 06 12 18`), rest `aria-hidden` |
| readout strip | `--sunk`, top rule, padding `8 10`, one line of mono `11.5`, wraps to 2 lines max at 320 |
| header | `--t-label` left, `--t-cap` right (`µg/m³ indoors`), 26/28 tall |
| hit area | the plot wrapper, `touch-action:pan-y`, `cursor:crosshair` desktop only |

**States**

| State | Render |
|---|---|
| default | cursor parked at the current hour |
| hover (pointer, ≥768) | cursor follows x; readout updates; bar under cursor gets a 1 px `--ink` outline (not a fill change) |
| focus-visible | the panel is a single tab stop with `role="slider"`-like keyboard: ←/→ move one hour, Home/End to 00/23. Ring on the plot wrapper. Readout announces via `aria-live="polite"` **only on keyup**, not per pixel. |
| dragging | `--sunk` readout strip stays put (no reflow); no transition on the cursor; `user-select:none` |
| active hour = current | the cursor foot becomes 9 px; the readout adds the word `now` |
| disabled | not used |
| loading | 24 empty tracks (1 px `--rule`) + axis + `Reading…` in the readout |
| error | empty tracks + `No hourly reading.` in `--alarm` + a `Retry` ghost button in the readout strip |
| empty | as loading, header right label reads `no data` |
| reduced motion | identical; the only motion (cursor) is already user-driven, so it is exempt |

---

### 7.4 Intervention picker row

14 rows, the densest thing on the page, deliberately — at 44 px the list is 616 px, which scrolls
as a list; at 46 px it is 644 px and starts to read as a wall, and a wall is what made the old
design feel like a report.

| Property | Value |
|---|---|
| grid | `18px minmax(0,1fr) 52px`, gap `8`, padding `4 10`, min-height **44** at ≤559 / 38 desktop |
| checkbox | 16×16, `border:1.5px solid var(--ctl)`, radius 2 |
| title | `--t-ui` 13, one line, ellipsis |
| qualifier | `em` inline after title, `--t-cap` 10.5, `--muted`, `margin-left:6`, e.g. `free`, `₹8,400` |
| right | `--t-data-s` 11.5, `--aq-text` = % removed; if a rupee figure is shown it goes on a second line at 10, `--muted`, plain (no strikethrough — strike-through on a price reads as a discount, which this is not) |
| separator | bottom `1px solid var(--rule)`; none on last |
| group headers | none. Order is by dose-per-rupee from the engine and the list must not be visually regrouped. |

**States**

| State | Render |
|---|---|
| default | unchecked box, `--panel` |
| hover | `background:var(--sunk)`; box border `--ink` |
| focus-visible | ring **inside** the row (`outline-offset:-2px`), never clipped |
| selected (`aria-pressed="true"`) | `background:var(--sunk)`; box filled `--aq-text` with a `--knob-ink` tick drawn as a rotated border, not an SVG; title `400→600` (no layout shift: reserve weight with a `text-shadow`-free trick, i.e. set the row to 600 always and rely on colour); right figure stays visible |
| the one already done | a 2 px `--ok` bar at x=0 and the title at `--muted`; still selectable (un-ticking it is how you undo) |
| disabled | box border dashed `--rule2`; title `--muted`; right column shows `—`; `aria-disabled="true"`; **no** opacity on text |
| loading (bench recomputing) | right column shows `…` in `--muted`; row stays interactive; the button that triggered it is `aria-busy` |
| error (combine failed) | right column keeps the last figure; a single 10.5 px `--alarm` line appears under the row: `Couldn't recompute. Tap again.` |
| empty (no interventions available) | one row: `Nothing to change from what you told me.` + ghost button `Edit household` |

---

### 7.5 Live tally block

The second plate. Sticky at ≥1024 only.

| Property | Value |
|---|---|
| ground | `--plate` (+ `1px solid var(--rule2)` in dark only, per §6.1), `--plate-ink`, 4 px `--aq-lift` band at the **top** edge (the verdict's band is at the bottom — they read as a matched pair, one leading, one trailing) |
| header | `--t-label`, `--plate-muted`, plus right-aligned mono `3 changes`; bottom rule `--rule-plate` |
| headline | `--t-tally` 34/44 mono, `−16.1%` with the minus as U+2212 and the `%` at 13 px |
| sub | `--t-ui` 13, `--plate-ink`, 2 lines max: `18,400 → 15,430 µg/day across 4 people` |
| band line | `--t-cap` 10.5, `--plate-muted`: `13,600–17,900` |
| overlap note | `--t-ui` 12, `--plate-ink`, on `--well`, 1 px top rule `--rule-plate`: `Together these remove 16.1%, not 19.3%. They overlap.` |
| per-person rows | 4 rows, name `--t-ui` 12, figure right mono 11.5, 5 px bar under each (`--rule2` = before, `--aq-lift` = after); separated by `--rule-plate` |
| padding | `12` cells, `10` header |
| sticky | only at ≥1024, `top:52px`; `max-height:calc(100vh - 72px); overflow:auto`; not sticky below 1024 |

**States**

| State | Render |
|---|---|
| default (nothing selected) | headline `0%`; sub `Nothing chosen yet. Tick what you could do.`; overlap hidden |
| hover | no row hover on the plate (it's a readout, not a menu); the person rows are links and get a 1 px `--plate-ink` underline |
| focus-visible | ring `--plate-ink`, offset 2 |
| selected/changed | the % swaps instantly and a 2 px `--aq-lift` underline beneath it flashes for 220 ms, then fades. **The digits never count up.** |
| disabled | n/a |
| loading | headline `…`; sub `Recomputing 3 changes`; band `—` |
| error | headline keeps last value; band line becomes `Couldn't recompute` in `--alarm-plate` (8.83:1 on `#060708`) |
| empty | as default |

---

### 7.6 Plan action row

A vertical rail, not cards. 2 px `--rule` vertical line at x=5; each row hangs off it.

| Property | Value |
|---|---|
| rail | `border-left:2px solid var(--rule)`, `margin-left:5` |
| dot | 8×8 at `left:-5`, `background:var(--paper)`, `border:2px solid var(--rule2)`, radius 50% |
| top action dot | filled `--aq-text`, border `--aq-text`, plus a 6 px `--aq-text` ring at 2 px offset |
| padding | `0 0 14 16` |
| when | `--t-label` 10.5, `.08em`, `--muted`; top action `--aq-text` |
| verb | `--t-h3` 13.5, 600, `--ink` |
| why | `--t-ui` 12/17.5, `--ink2`, `max-width:62ch` |
| meta | `--t-cap` 10.5, `--muted`: `₹0 · removes 22% · for Amma` |
| done button | `--t-micro` 10, `.09em`, uppercase, `1px solid var(--ctl)`, padding `4 8`, min-height 28, radius 2 |

**States**

| State | Render |
|---|---|
| default | as above |
| hover (row) | verb underlined `1px` `--rule2`; no background change (the rail is on paper) |
| focus-visible | ring on the row's primary interactive element, not the row |
| done (`aria-pressed="true"`) | button `background:var(--ok)` (`#1d6b45`) with `--knob-ink` text (`#fbfaf6` = 6.2:1 ✓); verb and why drop to `--muted`; dot becomes filled `--ok` |
| disabled | n/a |
| loading | action rows are server-decided; if absent, the section shows the streaming block (§8.4) |
| error | section-level: `The plan didn't arrive. Your numbers are above and they're correct.` + secondary `Try again` |
| empty | `Nothing to do differently today.` — no, banned (it claims safety). Use: `No change beats what you already do.` + `See every option` link |

---

### 7.7 Person card

| Property | Value |
|---|---|
| grid | 1 col <768 / 2 col 768–1023 / 4 col ≥1024 |
| padding | `10 11` |
| border | `1px solid var(--rule)`; `background:var(--panel)`; radius 2 |
| name | `--t-h3` 13.5/18, 600 |
| age | `--t-cap` 10.5, `--muted`, `· 68`, on the same line after the name |
| condition tag | `--t-micro` 10 uppercase, `1px solid currentColor`, padding `0 3`, `--muted`; risk conditions get `--alarm` |
| dose | `--t-data` 17, tabular, `margin-top:6`; unit `µg` 10 `--muted` |
| share | `--t-cap` 10.5, `--aq-text`: `31% of the household` |
| worst marker | 3 px `--aq-text` bar on the **left** edge only when this person is `worst_person`. This is the one legitimate left-accent in the system, and it encodes a computed fact, not decoration. |
| min-height | 96 |

**States**

| State | Render |
|---|---|
| default | as above |
| hover | border `--ink` (1 px, no width change) |
| focus-visible | ring outside, offset 2; the border stays `--ink` |
| selected | border `--ink` + `box-shadow:inset 0 0 0 1px var(--ink)` (a second rule, not a glow); the selected card's breakdown opens beneath the grid, full width |
| disabled | n/a |
| loading | name and age present, dose `—` |
| error | dose `—`, share replaced by `no figure` in `--alarm` |
| empty (no people) | one full-width panel: `Nobody added yet.` + secondary `Add people` |

---

### 7.8 Ledger row

Every option, ranked, `<details>`.

Mobile grid `26px minmax(0,1fr) 58px`; desktop `28px minmax(0,1fr) 76px 88px`.

| Cell | Spec |
|---|---|
| rank | `--t-cap` 10.5 mono `--muted`, tabular, `padding-top:2` |
| title | `--t-ui` 13/18, 500; `who` sub-line `--t-cap` 10.5 `--muted` |
| dose removed | `--t-data-s` 12.5, 600, right, tabular |
| per rupee | desktop only, `--t-cap` 10.5, `--ink2`, right, with `small` label `per ₹1,000` at 9 → **10** |
| padding | `9 0` |
| border | bottom `1px solid var(--rule)` |
| body | `padding:2px 0 14px 33px` (mobile: `padding-left:0`), `--t-ui` 13/19, `--ink2`, `max-width:66ch` |
| source line | `2px solid var(--rule2)` left border, padding-left 8, `--t-cap` 10.5, `--muted` |

**States**

| State | Render |
|---|---|
| default (closed) | summary row |
| hover | title underlined `1px` `--rule2`, `text-underline-offset:3` |
| focus-visible | ring on `<summary>`, offset `-2` |
| open | a 1 px `--rule2` appears between summary and body (not `--rule`) |
| disabled | n/a |
| loading | 6 placeholder rows: rank present, title a 60% 1 px rule, figure `—` |
| error | one row: `Every option couldn't load.` + secondary `Try again` |
| empty | `No option makes a measurable difference.` + link to the evidence drawer |

---

### 7.9 Evidence drawer

Two drawers: constants (56), household editor. Same chassis.

| Property | Value |
|---|---|
| border | `1px solid var(--rule2)` — one step heavier than a panel, because it is an affordance |
| summary | padding `10 12`; title `--t-ui` 12.5/17, 600; sub `--t-cap` 10.5 `--muted`, `max-width:46ch` |
| affordance | right-aligned `--t-micro` 10 uppercase mono, `open` / `close`, `1px solid var(--rule2)`, padding `1 4` |
| open state | summary gets `border-bottom:1px solid var(--rule)` |
| group | `border-top:1px solid var(--rule)`, `padding:7 0` |
| group head | `--t-cap` 10.5, 700, `--ink2` |
| constant row | grid `minmax(0,1fr) auto`, `--t-cap` 10.5, `--muted`, padding `1.5 0`; value mono `--ink` 500, nowrap |
| kind tag | `--t-micro` 10 uppercase, `1px solid currentColor`, `measured`→`--ok`, `estimate`→`--alarm`, `literature`/`standard`→`--muted` |
| body padding | `2 12 12` |

**States:** default/closed, hover (title underline, affordance border `--ink`), focus-visible
(ring offset -2), open (as above), loading (`Loading 56 constants…` inside the open body),
error (`Couldn't load sources.` + `Try again`), empty (`No constants recorded.`). Disabled: n/a.

---

### 7.10 Buttons

**Primary** — one per screen, maximum.

| Property | Value |
|---|---|
| height | 40 mobile / 36 desktop; padding `0 14`; radius 2 |
| fill | `--ink`; text `--paper`; **15.79:1** light / **16.54:1** dark |
| type | `--t-ui` 13, 600, `.01em` |
| hover | fill `--ink2` (light `#383d41` with `#eeedea` = 9.38:1; dark `#c2c6c4` with `#0e1012` = 11.05:1) |
| active | `translateY(1px)` only, 90 ms |
| focus-visible | 2 px `--ink` ring at `outline-offset:2px`. The offset lands on `--paper`, so an ink ring against an ink fill still reads (15.79:1). Do not use a `--paper` ring here — it disappears on the page. |
| disabled | fill `--rule2`, text `--ink` at full opacity (8.73:1 light, 8.27:1 dark) — never a ghosted label |
| loading | label replaced by `…` + `aria-busy="true"`; width locked with `min-width` so nothing jumps; no spinner |
| error | the button itself does not turn red; the message appears adjacent |

**Secondary** — as primary but `background:none`, `border:1px solid var(--ctl)`, text `--ink`.
Hover: `border-color:var(--ink)`. Disabled: dashed `--rule2`, text `--muted`.

**Text button** (ledger "Show in the ledger", evidence links): no border, no fill, `--ink`,
`text-decoration:underline`, `text-underline-offset:3px`, `text-decoration-color:var(--rule2)`;
hover → decoration colour `--ink`. Height 44 at ≤559 (pad with padding, not a fake box).

Label rules: verbs, 2–3 words, sentence case, no arrows, no "+".

---

### 7.11 Text input (place search, name, age)

| Property | Value |
|---|---|
| height | 40 mobile / 36 desktop |
| padding | `0 10` |
| border | `1px solid var(--ctl)`; radius 2; `background:var(--panel)` |
| type | `--t-ui` 13; value `--ink`; placeholder `--muted` (5.47:1 — a placeholder must be readable, it is often the only instruction) |
| label | visible, `--t-label` 10.5 above the field. **No placeholder-as-label, ever.** |
| focus-visible | border `--ink` + 2 px ring at offset 1 (inside, so the field does not jump) |
| hover | border `--ink` |
| disabled | dashed `--rule2`, text `--muted`, `cursor:not-allowed` |
| loading (geocode in flight) | 1 px `--rule2` rule under the field animating as an indeterminate sweep, 1.8 s; text unchanged |
| error | border `--alarm` + 10.5 px `--alarm` message below, `Couldn't find that place. Try a district name.` |
| empty | placeholder `City or district` (never "Search…") |
| suggestion list | `--panel`, 1 px `--rule2`, the system's one shadow (§6.3), rows 38, mono-free, `--t-ui`; each row shows `name` + `--muted` `admin1` |

---

### 7.12 Theme toggle

Two states, manually toggled, `html[data-theme]`, persisted in `localStorage` under
`saans.theme`. First load reads `matchMedia('(prefers-color-scheme: dark)')` **once** and writes
the explicit attribute — no third "auto" state, because a third state is a hidden mode and this
is a 06:40 tool.

| Property | Value |
|---|---|
| form | mono text button in the masthead, `min-width:64`, height 32, `1px solid var(--ctl)`, radius 2 |
| label | the **destination**, not the state: shows `Dark` in light mode, `Light` in dark mode |
| type | `--t-label` 10.5, `.1em` |
| `aria-pressed` | `true` when dark |
| hover | border `--ink`, text `--ink` |
| focus-visible | ring offset 2 |
| pressed/current | n/a — the label always names the action, so there is no "on" appearance |
| disabled | n/a |
| loading | n/a (instant, client-side) |
| error/empty | n/a |

**Banned:** sun/moon icon toggles, 3-way segmented "Auto/Light/Dark" controls, and animating the
theme change. The swap is one frame. It is a light switch, not a transition.

Masthead total: `Saans.` mark (serif 19, `--ink`, the full stop in `--aq-text`) + place chip +
clock + spacer + theme toggle. 44 px tall, one line, `border-bottom:1px solid var(--rule)`,
`background:var(--paper)`, `position:sticky`, `z-index:20`.

---

## 8. Motion

### 8.1 Tokens

```css
--d1:90ms;  /* state change: hover, selection, press */
--d2:140ms; /* entrance: a panel or row appears */
--d3:220ms; /* emphasis: the delta flash, drawer open */
--ease:cubic-bezier(.2,0,0,1); /* decelerate hard, no overshoot */
```

Only these three durations. No `0.3s ease`, no `ease-in-out`, no spring.

### 8.2 What animates

| Thing | Spec |
|---|---|
| hover/selection colour | `background-color`,`border-color`,`color` — 90 ms `--ease` |
| drawer open (`<details>`) | content appears at once; the summary's border-bottom fades in over 140 ms. **Height is not animated** — animating `height` on a `<details>` costs a JS shim and janks on a cheap Android. |
| tally delta | a 2 px `--aq-lift` underline under the changed figure: appears instantly, fades out over 220 ms. The digits themselves swap in one frame. |
| streaming progress | §8.4 |
| skip-link reveal | instant |

### 8.3 What must never animate

- **Numbers.** No count-up, no odometer, no digit roll. A number that animates is a number the
  user cannot trust at the moment they read it, and count-up is the single most recognisable
  "AI dashboard" tell.
- Layout: no width/height/top/left transitions on rows, panels, or the chart.
- The chart on load: **no bars growing from zero.** The chart is a measurement; it is either
  measured or not.
- Entrance animations on the verdict. It is the first thing painted; it must not fly in.
- The theme swap, the page background, the plate colour.
- Scroll: `scroll-behavior:smooth` only for the one "Show in the ledger" jump, and never on
  reduced-motion.
- Parallax, blur transitions, marquee, shimmer skeletons, pulsing whole panels.

### 8.4 Progress treatment for a 30–90 s generation

This is the longest wait in the product and currently shows a static label while the SSE stream
is full of usable signal. Spec:

**Three steps, driven by real events, not by a timer:**

| SSE event | Phase label (mono, `--t-cap`) | Segments filled |
|---|---|---|
| request sent | `Reading your numbers` | 1 of 3 |
| `facts` | `Choosing what to say` | 2 of 3 |
| first `token` | `Writing it` | 2 of 3 |
| `plan` received | `Checking every figure` | 3 of 3 |
| `done` | label removed, block collapses | — |

Phase 3 has two labels but one segment: `Checking every figure` is the post-processing pass
(`enforce()`), which is genuinely a distinct thing happening, and it usually lasts under a second.

- The block sits **above** the plan's prose slot, never as an overlay, never as a modal.
- Indicator: three 24 × 2 px segments, 4 px apart. Completed `--ink`, current `--aq-text`,
  pending `--rule`. This is determinate in *steps*, which is honest, and indeterminate in time,
  which is also honest.
- While any phase is active, the current segment carries a 1.8 s indeterminate sweep (a 2 px
  `--aq-text` block translating 0 → 24 px, `linear`, `infinite`). One moving element, 24 px,
  never wider.
- **No percentage. No spinner. No "this may take a while".** If it takes 90 s, the page says
  `Writing it` for 90 s and the user can read the ladder above, which is already correct.
- Streamed tokens: append at the model's own rate. **Do not** typewrite at a fixed per-character
  delay — it desynchronises from the stream and turns a 40 s generation into 90 s.
- **Prerequisite:** the current client parser keeps only SSE events carrying a `today` key and so
  throws away every `token` event. The progress spec above is unimplementable until that one
  condition is removed. This is the highest-value line of code in the whole redesign.
- Show at most 3 sentences of streamed prose. Append a 2 px × 15 px `--ink` block after the last
  character, blinking at 1.2 s, so the text reads as still being written rather than as broken.
  On `plan`, swap in the final text in one frame and remove the block.
- Timeout path (>180 s): phase label becomes `It's taking too long.` in `--alarm`, plus secondary
  `Try again`; the rest of the page stays untouched and usable.

### 8.5 Reduced motion

```css
@media (prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important;scroll-behavior:auto!important}
  .stream-seg{background:var(--aq-text)}      /* sweep → static filled segment */
  .delta-underline{animation:none;opacity:1}  /* flash → persistent 2px rule, removed on next change */
}
```
Everything still *works*: the phase label and step segments carry all the information; only the
movement is gone. No component's meaning depends on motion.

---

## 9. Responsive behaviour

Breakpoints: **320 (floor), 390 (primary), 768 (tablet), 1440 (desktop).**
Gutters: 12 / 16 / 24 / 24. Max content width 1120.

### 9.1 320

- Page padding 12. Everything single column.
- Verdict 26/30 (a one-step override of `--t-verdict`, 27→26 at 320 only), max 3 lines,
  `hyphens:auto` **off** — allow a 4th line rather than hyphenate.
- Ladder collapses to two lines per rung: label + value on line 1, track full width on line 2,
  `why` below. Row height 52.
- Chart keeps 24 columns at 10.4 px. Axis labels `00 06 12 18` only, `--t-micro` 10.
- Picker rows 44 px (`box-sizing:border-box` includes the 1 px rule), title wraps to 2 lines
  (`white-space:normal` at this width only).
- Person cards 1 col. Ledger loses the `per ₹1,000` column entirely (it moves into the drawer
  body). Plan meta wraps to 2 lines.
- Masthead: the place chip truncates to 12 ch; the clock shows `06:40` only.
- **Test: `document.documentElement.scrollWidth === 320`.** Any `min-width` in px on a flex child
  is the usual culprit; the fix is `minmax(0,1fr)`, never a smaller fixed width.

### 9.2 390 (primary)

- Page padding 16. Single column. Verdict 27/31.
- Ladder three columns, 38 px rows, `why` collapsed.
- Chart 148 px panel, full width.
- Bench: picker list then tally stacked; tally is **not** sticky (it would eat half the screen).
- Person cards single column (2 col would give 173 px each, too narrow for a 17 px figure
  and a name).
- Above-the-fold budget from §5.4: 709 px of content in 812.

### 9.3 768

- Page padding 24. Two-column `people` grid. Ledger gains the `per ₹1,000` column.
- The **margin label grid** turns on: section labels move into a 64 px left column; content
  starts at x=64. This is what makes the page read as a form rather than a stack.
- Verdict 34/38 (the fluid step between the 27 and 40 endpoints); plate height 176.
- Chart gains hover/scrub pointer support (`cursor:crosshair`, pointer events).
- Bench becomes 2 col: picker `1fr`, tally 300 px. Tally is **not** sticky until 1024 — at 768 the
  tally at `top:52` would cover the picker it is measuring.
- Evidence drawer body goes 4-col for constants at ≥900.

### 9.4 1440

- Max width 1120 centred; 24 px gutters unused (the column is the constraint).
- Margin label column 88 px; content 1fr; optional right rail 300 px used **only** by the tally
  when the bench is in view.
- Verdict 40/44, plate 196, `max-width:22ch` — the sentence occupies a third of the plate and the
  rest is deliberate empty `--plate`. Do not fill it.
- People 4 col; ladder rows 38; chart 96 px plot; axis labels every 2 h above 900 px.
- Line lengths capped: prose 68ch, help 62ch. At 1120 px a full-width paragraph is 140ch and
  unreadable — the caps are mandatory, not stylistic.

### 9.5 What is dropped, and what never changes

| Dropped | Where |
|---|---|
| `per ₹1,000` column | < 620 |
| condition tags inside ledger rows | < 620 (kept in the drawer) |
| hour labels beyond 00/06/12/18 | < 560 |
| the `why` line on ladder rungs | collapsed at all widths, expanded on tap |
| sticky tally | < 1024 |
| margin label column | < 768 |
| the aside sentence next to section heads | < 560 (it moves under the head, 1 line) |

**Never dropped:** the verdict's metadata line, the unit on any number, the uncertainty band, the
source line in the ledger body, the skip link, the theme toggle.

**No horizontal overflow at any width.** Rules: no `width` in px on a grid child; all grid
templates use `minmax(0,1fr)`; `overflow-wrap:anywhere` only on the place name; `overflow-x` is
never `hidden` on `body` (that hides bugs); test at 320/375/390/414/768/1024/1440.

---

## 10. Anti-patterns for this product

Each of these is a defect, not a preference. Reject in review by name.

**The generic-AI-dashboard tells**
1. **Gradient hero.** Any `linear-gradient` background, especially indigo→violet, on the top
   380 px. Also bans "aurora" blobs and mesh gradients as `background-image`.
2. **Glassmorphism.** `backdrop-filter`, semi-transparent panels, frosted cards. There is already
   a real tonal system; blur is a substitute for one.
3. **Indigo / violet / #6366f1** anywhere. The accent must come from the air, and there is exactly
   one accent.
4. **Icon-tile grids.** Four rounded squares with an emoji or a stroked icon and a label. The
   product has no feature list; its "features" are numbers.
5. **Left-accent cards.** A 3 px coloured left border on a white rounded card. One exception is
   permitted, named in §7.7 (the worst-person marker), and it encodes a computed fact. Everywhere
   else it is decoration.
6. **Oversized rounded rectangles.** Radius ≥ 8 px on a card, ≥ 999 px pills for status. At 2 px
   a panel reads as printed stock; at 16 px it reads as a phone app from 2019.
7. **Emoji.** 🍃 😷 💨 ✅. In a health product an emoji in a number's row is a credibility loss.
   The one glyph allowed is a middot and an em dash.
8. **Count-up numbers / odometer digits.** See §8.3.
9. **Sparkline decoration.** A tiny trend line with no axis, no unit, and no source. If a series
   ships it gets a scale, a label, and a readout.
10. **"Good morning, Sukesh 👋"** or any greeting block. The page greets with the reading.
11. **A floating action button.** Nothing floats here. The primary action is in the flow.
12. **Skeleton shimmer.** Grey blocks with a moving highlight. Use static rules at the exact
    dimensions of the content (already specified per component).
13. **Drop shadows on cards** beyond the single popover in §6.3.
14. **Centered marketing layout**, a tagline above the verdict, or a "How it works" strip.

**Domain-specific wrongness**
15. **A gauge/dial/speedometer.** An arc with a needle implies a continuous sensor and a scale
    that does not exist; the product models, it does not measure.
16. **"Safe" / "unsafe" / "hazardous" badges.** The narrator is forbidden the word "safe" (§11);
    the UI must be too. Use the CPCB category word and a number.
17. **Traffic-light triads** (green/amber/red rows side by side). It flattens six CPCB categories
    into three and invents a judgement.
18. **The CPCB raw hexes** (§3.6). A yellow badge with white text is the most likely single
    accessibility regression in this project.
19. **An AQI number as the hero.** The hero is the household's dose. A city AQI headline means
    the product has become the app it exists to replace.
20. **Red for "Severe" and red for "error"** in the same viewport with no other differentiator.
21. **Percentages without a base.** `−16%` must always be adjacent to the two absolute values.
22. **A map.** Any map, tile, or outline of Delhi. It adds a network request and no decision.
23. **Charts with two y-axes.** Ambient and indoor share one µg/m³ axis or they do not share a
    panel.
24. **A "Share" card with the logo and a rounded gradient** — if a share view ever ships it uses
    the plate, the band, and the sentence, nothing else.
25. **An account, a login, an onboarding modal, a cookie banner, a newsletter field.**

---

## 11. Copy voice

The product speaks to one tired adult, in the second person, in the imperative. It is a notice
from a competent neighbour who has done the arithmetic — not a coach, not a doctor, not a
chatbot.

**Rules**

1. **Verb first.** If a sentence opens with "It is important to…" or "You may want to consider…",
   delete everything before the verb.
2. **One idea per sentence. Max 12 words.** The verdict sentence is additionally capped at 92
   characters, which at 390 px is 3 lines — whichever limit binds first.
3. **Numbers carry their unit and their base.** `18,400 µg/day across 4 people`, never `18.4k`.
4. **Say what changes, not what is true.** "Shut the bedroom window until 10" beats "PM2.5 is
   elevated".
5. **Banned words:** safe, unsafe, hazardous, dangerous, protect, worry, risk-free, optimal,
   leverage, personalised, insights, AI-powered, journey, wellness, breathe easy, "we".
6. **No moralising and no shame.** The stove is a fact with a cost attached, not a failing.
7. **No exclamation marks. No emoji. No rhetorical questions.**
8. **Never claim a measurement.** "Our model says", "estimated", "the band is" — and the app
   already says it does not measure.
9. **Uncertainty is stated in the same sentence as the number**, not in a footnote:
   `15,430 µg/day, give or take 2,100`.
10. **Empty and error states are instructions.** Say what happened, then the next tap. Never
    "Something went wrong."
11. **Local words are correct words.** chulha, autowala, Amma, PNG cylinder. Do not translate
    them into "traditional cookstove".
12. **Sentence case everywhere.** Uppercase is reserved for 10–10.5 px mono labels; a button is
    never `SAVE CHANGES`.

**Six before/after**

| # | Before (bad) | After (good) | Why |
|---|---|---|---|
| 1 | "Air quality in your area is currently poor. Consider limiting outdoor activity." | "Don't open the windows before 10. The air outside is 4× worse than your kitchen." | Verb first, a time, and a comparison instead of an adjective. |
| 2 | "Your estimated daily PM2.5 inhalation dose is 6,283 µg." | "Your family breathes in 18,400 µg today. Amma takes a third of it." | Household total, a named person, a share — the product's actual claim. |
| 3 | "No interventions selected. Select interventions to see combined impact." | "Nothing chosen yet. Tick what you could do." | Same instruction, 60% shorter, no jargon. |
| 4 | "AI is generating your personalised plan. This may take up to 90 seconds…" | "Writing your plan. Your numbers above are already correct." | Names the wait, removes the apology, and tells them the useful part is ready. |
| 5 | "Error: failed to fetch /api/ambient (500)" | "The air feed didn't answer. These numbers are from 06:12." | What failed, and what the user is actually looking at. |
| 6 | "You should consider using a HEPA purifier to reduce your exposure to PM2.5." | "A purifier in the room where Amma sleeps takes 22% off her day. ₹8,400." | Imperative-adjacent, specific, costed, and it names the person it helps. |

**Microcopy bank** (use verbatim; do not paraphrase)

| Slot | Copy |
|---|---|
| skip link | `Skip to the numbers` |
| masthead place chip (empty) | `Set location` |
| verdict header | `{CATEGORY} · {HH:MM} · {PLACE}` |
| verdict loading | `Reading the air` |
| ladder header | `Street to lungs` |
| chart header | `Next 24 hours` / right: `µg/m³ indoors` |
| bench header | `Build your plan` / aside: `Tick what you could do. The number moves.` |
| tally empty | `Nothing chosen yet. Tick what you could do.` |
| tally loading | `Recomputing 3 changes` |
| overlap | `Together these remove 16.1%, not 19.3%. They overlap.` |
| plan header | `Today's plan` |
| plan limit | `What this can't see: your indoor air is modelled, not measured.` |
| people header | `Who carries it` |
| ledger header | `Every option, by dose removed per rupee` |
| evidence header | `The arithmetic and its sources` |
| evidence sub | `Measured, literature, standard or estimate — labelled, never blurred.` |
| editor summary | `Your household` |
| editor aside | `These are assumptions. Change them and every number changes.` |
| stream phases | `Reading your numbers` → `Choosing what to say` → `Writing it` → `Checking every figure` |
| error (feed) | `The air feed didn't answer. Retry, or read the last reading.` |
| timeout | `It's taking too long. Your numbers are above; the plan can wait.` |
| 404-equivalent | `That page isn't part of Saans.` |

---

## 12. Byte budget and implementation order

Baseline when measured: 65,041 B total, 20,903 B of it CSS inside `<style>`. Ceiling ~70 KB leaves
**~5 KB** — which is why §3.3 uses two accent tracks instead of six full palettes, and why the tag
sizes get raised without new classes.

| Change | Δ bytes |
|---|---|
| New tokens in `:root` (`--plate`, `--plate-ink`, `--plate-muted`, `--well`, `--ctl`, `--knob-ink`) | +180 |
| Dark overrides for the same | +170 |
| Spacing + type tokens (only the six you actually reference; skip `--s1..--s9` and use literals) | +140 |
| 6 × `html[data-aq=x]{--aq-text:…;--aq-lift:…}` (light) | +345 |
| 6 × dark `[data-aq]` overrides, one token each (`--aq-lift` aliased, §3.3) | +300 |
| Plate + band + margin-label grid | +340 |
| Tally band + delta underline + `--well` rows | +210 |
| Streaming step segments | +150 |
| `prefers-contrast` additions | +90 |
| **Subtotal** | **+1,925** |
| Collapse `.surhead`/`.sechead`/`.tally .th`/`.benchhead h2` label rules into one `.lbl` | −260 |
| Merge `.chip` and `.doneBtn` (identical chassis) | −180 |
| Delete `.pp .bar i` and the person-card inner borders (rules do the work) | −140 |
| Drop `.kind.measured`/`.estimate` classes; use one `.kind` + `[data-kind]` | −60 |
| Widen 8 px tags to 10 px, delete `.tag` entirely (fold into `.kind`) | −70 |
| **Freed** | **≈ −710** |

Net ≈ **+1.2 KB CSS** → ~22.1 KB of CSS, ~66.2 KB total, **~3.8 KB headroom**.

Two byte tricks that are not obvious:
- In dark mode set **only** `--aq-text` per category, and put `--aq-lift:var(--aq-text)` on
  `html[data-theme="dark"]`. That halves the category table and removes 12 declarations.
- Do **not** create a spacing token for every step. Use `--s:4` as a unit and write
  `padding:calc(var(--s)*3)` only where it reads better; literals are cheaper and this stylesheet
  has exactly one author.

If it still does not fit: the six-category table is the thing to keep, and the `prefers-contrast`
block is the thing to generalise (four overrides instead of seven).

**Build order (do not reorder):**
1. Tokens + both themes + `[data-aq]` (no visual change yet, everything compiles).
2. Plate: verdict and tally. This is 80% of the identity for 3% of the code.
3. Margin-label grid at ≥768 and the rule system; delete per-component borders that duplicate it.
4. Type scale sweep — including raising every sub-10 px size.
5. Component states, in the order of §7 (verdict → ladder → chart → picker → tally).
6. Streaming progress (§8.4) — highest user-visible return of anything left.
7. Responsive pass at 320 / 390 / 768 / 1440 with the overflow test.
8. Contrast test in `test_ui.py` with the hexes hardcoded.

**Acceptance (all measurable, all in `test_ui.py`):**
- `scrollWidth === clientWidth` at 320, 390, 768, 1440.
- Every pair in §3.5 asserted against hardcoded hexes.
- No `font-size` below 10 px in the stylesheet (regex the CSS, fail on match).
- No `border-radius` outside `{0,1,2,50%}`; no `box-shadow` count > 1; no `gradient`; no
  `backdrop-filter`; no `#6366f1`.
- Zero `http` in the file. Zero `@font-face`.
- Above-the-fold at 390 × 812 contains the verdict and the worst person's name.
