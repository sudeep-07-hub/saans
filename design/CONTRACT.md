# FROZEN CONTRACT — read before designing or writing code

This file is authoritative. If a design idea conflicts with it, the design
changes. Anything in `MUST NOT BREAK` is load-bearing and already tested.

## The diagnosis (agreed, do not relitigate)

The current UI is organised as **evidence**: verdict → now → plan → ranking →
source shares → emissions → factors, all on one long scroll. That answers "is
this well researched?" It does **not** answer "why would I open this tomorrow
morning?"

A daily-use product is a **loop**, not a layout:

    trigger  →  glance (1s, one answer)  →  act (one thing)
             →  confirm (I did it)  →  feedback (vs yesterday)  →  return

The current app has glance and act. It has **no trigger, no confirm, no
feedback, no memory**. That is the gap. A reskin will not close it.

## The product this must become

A household opens it standing in a cold kitchen at 06:40, half asleep, on a
cheap Android phone, on a slow connection. In **under two seconds** they must
know: *can I open the window, can the child go out, what is the one thing I do
today.* Then close it. Then come back tomorrow because it remembered.

## MUST NOT BREAK (verified behaviour, tested)

1. **API contract** — these endpoints and payload fields are fixed:
   - `POST /api/brief` → `{brief:{aqi:{aqi,label,slug,dominant,health},
     grap:{label,detail,applies}, who:{multiple,label}, ambient_pm25,
     indoor_pm25, kitchen_pm25,
     worst_hour:{hour,pm25}, best_hour:{hour,pm25},
     next_trough:{hour,pm25}, next_peak:{hour,pm25}, elevated_now:bool,
     headline, now:[{icon,text,why}], school:{applies,level,advice},
     household:{people:[{name,age,dose_ug,mean_exposure,cigarettes,
     attributed_risk_share,sensitivity,by_place}], segments, household_dose_ug,
     household_cigarettes}, profile:{label,basis,mid,verified_city,local_note},
     emissions:{...}, stamp}, ranked:[{key,title,pct,band_pct,cost_inr,
     runtime_inr_yr,effort,why,source,tags,worst_person,worst_pct,per_person}],
     hourly:[{hour,pm25}], people, segments, model:{available,name}}`

     **`worst_hour`/`best_hour` are extrema over the whole 0–23 series and are
     often in the past. `next_trough`/`next_peak` are the forward-window
     equivalents and are what any "what do I do now" copy MUST use.**
     `elevated_now` is whether the current reading is ≥85% of the day's peak —
     use it to decide between "keep them shut" and "open them at the low".
   - `GET /api/geocode?q=` → `{results:[{name,admin,country,lat,lon,label,
     country_code,timezone}]}`
   - `GET /api/factors` → `{groups:{...}, method:[], limits:[]}`
   - `POST /api/plan` → SSE events `facts`, `token`, `plan`, `done`
   - `POST /api/simulate` → `{key}` + household → before/after
   - `POST /api/brief`, `/api/skeleton`, `/api/plan`, `/api/combine` all take the
     **same flat household body** (`location`, `home`, `habits`, `transport`,
     `people`, `office`, `tone`). `/api/simulate` and `/api/auth`-style wrappers
     are the only ones that nest it. Two shapes for one concept is how every
     configured household was silently replaced by the default four-person
     family — see commit 26bbdd9. Never reintroduce a second shape.
2. **Plan streaming** — must read SSE via `fetch` + `getReader()`, render
   `figures[]`, `today[]` (time/action/why/effect/who/who_pct/effort),
   `the_one_thing` (action/why/effect/band/cost_inr/who/who_pct/source),
   `this_week[]`, `for_children`, `what_this_does_not_fix`, `generated_by`,
   `notes`. It must say whether wording came from the model or the fallback.
3. **Accessibility floor** — WCAG AA on all text (4.5:1 normal, 3:1 large);
   visible `:focus-visible` rings; a skip link; `aria-live` on content that
   changes without navigation; text equivalents for every chart; every control
   keyboard-reachable; `<html lang>`, landmark `<main>`, labelled inputs;
   honours `prefers-reduced-motion`, `prefers-contrast: more`, and must add
   `prefers-color-scheme`.
4. **Security** — no `innerHTML` with API-derived strings (use `textContent`);
   no third-party CDN, font, or script (the CSP is `default-src 'none'`);
   no `eval`; no inline event handlers.
5. **Never claim safety.** No "safe", no "you will". These are enforced server
   side too, but the UI must not imply them either.
6. **Self-contained** — one HTML file, no build step, no framework, no web
   fonts. Target **≤ 70 KB** uncompressed. Must work on a slow 3G phone.

## Design constraints

- **Mobile-first.** The primary target is a 360–390 px Android. Desktop is the
  adaptation, not the reverse. Thumb-reachable primary controls.
- **Progressive disclosure, three levels deep.** Today's answer occupies level 1
  (one screen). The plan and the day are level 2. The ranking, source shares,
  emissions, and the 56-constant evidence drawer are level 3 — reachable,
  never in the way. Right now everything is level 1, which is why it reads as a
  wall.
- **Dark mode is a first-class mode**, not an inversion. This is used at 06:40
  in winter and at 23:00. Follow `prefers-color-scheme`, plus a manual toggle
  that persists.
- **Time-aware.** The app must know what hour it is and lead with the decision
  that belongs to that hour. It already receives `worst_hour` and `best_hour` —
  the "now" card must not advise opening windows during the modelled peak.
- **Quiet, not gamified.** A health product must not be a casino. No emoji
  streaks, no confetti, no "🔥 14 days!". Progress is stated plainly or not at
  all.
- **Typography and colour carry the hierarchy**, not boxes. Avoid: gradient
  hero, glassmorphism, icon-tiled feature grid, accent left-rails, oversized
  rounded cards, indigo/violet accent, Inter-by-default.
- **No fake data.** No invented numbers, no placeholder testimonials, no
  decorative stats.

## Local persistence (the retention mechanism)

`localStorage` only — no account, no server, no analytics. Must survive
refresh. State to keep:
- `done:<YYYY-MM-DD>:<key>` — the action acknowledged today
- a compact history of `{date, aqi, indoor, done:[keys]}` for the last ~30 days
- the household profile (so it does not have to be re-entered)
- the theme choice
Must degrade: if `localStorage` throws (private mode / quota), the app still
works, just without memory.

## The hard question every delegate must answer

**Why would someone open this a second time?** If your proposal does not
change the answer from "to read the same report again", it is not finished.
