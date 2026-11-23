#!/usr/bin/env python3
"""
UI contract tests — run against the served file, not against claims.

The point of this file is that a redesign cannot pass by being pretty. Every
check here is something a reviewer would otherwise have to remember to look at,
and every one of them has been broken at least once during this project.

Usage:  python3 test_ui.py                 (expects a server on 8017)
        python3 test_ui.py --port 8017
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request

FAILS: list[str] = []
PORT = 8017


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}{f'  [{detail}]' if detail else ''}")
    if not cond:
        FAILS.append(name)


def get(path: str, timeout: int = 30) -> str:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=timeout) as r:
        return r.read().decode()


def contrast(hex_a: str, hex_b: str) -> float:
    def lum(h: str) -> float:
        h = h.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    la, lb = lum(hex_a), lum(hex_b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def main() -> int:
    if "--port" in sys.argv:
        global PORT
        PORT = int(sys.argv[sys.argv.index("--port") + 1])

    try:
        html = get("/")
    except Exception as exc:
        print(f"cannot reach server on {PORT}: {exc}")
        return 1

    size = len(html.encode())
    print(f"--- served {size:,} bytes\n")

    # --- constraints -------------------------------------------------------
    # The 70 KB ceiling was an invented target in CONTRACT.md, not a rule from
    # the brief (whose only size rule is 10 MB for the repo). The orchestrator
    # raised it to 90 KB in design/ORCHESTRATOR_REVIEW.md, "Conflicts resolved"
    # §3, rather than delete accessibility guarantees to hit a number. Asserted
    # here so the new ceiling is a checked constraint, not a preference.
    check("under 90 KB", size <= 90 * 1024, f"{size/1024:.1f} KB")
    check("no external stylesheet", not re.search(r'<link[^>]+rel=["\']stylesheet', html, re.I))
    check("no external script", not re.search(r'<script[^>]+src=', html, re.I))
    check("no web font", "@font-face" not in html and "fonts.googleapis" not in html)
    check("no CDN origin referenced", not re.search(r'https?://(?!127\.0\.0\.1)', html))
    check("no eval", not re.search(r"\beval\s*\(", html))
    check("no inline event handlers", not re.search(r'\son(click|change|input|load|error)\s*=', html, re.I))

    # --- structure & i18n --------------------------------------------------
    check("html lang set", bool(re.search(r'<html[^>]+lang=', html, re.I)))
    check("has a <main> landmark", "<main" in html)
    check("has a skip link", 'class="skip"' in html or 'href="#main"' in html)
    check("has a <title>", bool(re.search(r"<title>[^<]{5,}</title>", html, re.I)))

    # --- accessibility -----------------------------------------------------
    check("focus-visible styling present", "focus-visible" in html)
    check("aria-live used", "aria-live" in html)
    check("chart has a text alternative", "role=\"img\"" in html and 'class="sr"' in html)
    check("reduced motion honoured", "prefers-reduced-motion" in html)
    check("high contrast honoured", "prefers-contrast" in html)
    check("colour scheme honoured", "prefers-color-scheme" in html)
    inputs = re.findall(r"<input[^>]*>", html, re.I)
    unlabelled = [i for i in inputs
                  if not re.search(r'aria-label|aria-labelledby|id=["\'][^"\']+["\']', i, re.I)]
    check("every input is labelled or identified", not unlabelled,
          f"{len(unlabelled)} unlabelled: {unlabelled[:2]}")

    # --- security ----------------------------------------------------------
    # innerHTML is allowed only with clearly static markup. Flag any use that
    # interpolates a ${...} expression, which could carry API text.
    bad_inner = re.findall(r"innerHTML\s*=\s*[`'\"][^`'\"]*\$\{", html)
    check("no innerHTML with interpolated values", not bad_inner, str(bad_inner[:2]))
    check("textContent is used for data", html.count("textContent") >= 8,
          f"{html.count('textContent')} uses")

    # --- the design contract (DESIGN.md level 1) ---------------------------
    # Match the design intent, not the identifiers I happened to imagine. The
    # first version of this file asserted id="dayband" and failed a correct
    # implementation that called it "plot" — the harness was the bug.
    check("a verdict element exists", 'id="verdict"' in html)
    band = re.search(r'id="(plot|band|dayband)"', html)
    check("day band exists", band is not None, band.group(0) if band else "")
    check("day band is an accessibility object", 'role="img"' in html)
    check("day band has a text alternative wired",
          bool(re.search(r'role="img"[^>]*aria-labelledby="(\w+)"', html))
          and bool(re.search(r'aria-labelledby="\w+"', html)),
          (re.search(r'role="img" aria-labelledby="(\w+)"', html) or [""])[0])
    # The three concentrations, by the words the ladder uses rather than by ids
    # I invented in an earlier version. The redesign renamed them; the contract
    # is that a household can see outdoor, indoor and stove concentrations.
    for label in ("outdoor", "indoors", "stove"):
        check(f"the {label} concentration is shown",
              bool(re.search(rf'"{label}"', html)) or bool(re.search(rf'>{label}<', html, re.I))
              or (label == "stove" and "the stove" in html))
    check("a worst-off person line exists",
          bool(re.search(r'id="(personNote|person|heaviest)"', html)),
          (re.search(r'id="(personNote|person|heaviest)"', html) or [""])[0])
    check("localStorage is used for memory", "localStorage" in html)
    check("storage access is guarded",
          re.search(r"try\s*\{[^}]*localStorage", html, re.S) is not None)
    # A null trough hour means the cleanest point is the reading in hand; the
    # page must not print "00:00" there. Matched loosely because the variable
    # name differs between the chart, the verdict and the plan.
    check("trough hour null is handled, not printed as 00",
          bool(re.search(r"\.hour === null", html)))

    # --- must not claim safety --------------------------------------------
    prose = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    prose = re.sub(r"<style[\s\S]*?</style>", "", prose, flags=re.I)
    prose_text = re.sub(r"<[^>]+>", " ", prose)
    check("no 'safe' claim in markup",
          not re.search(r"\b(is|are|keeps?|stays?)\s+\w*\s*safe\b", prose_text, re.I),
          (re.search(r".{0,40}\bsafe\b.{0,40}", prose_text, re.I) or [""])[0])

    # --- palette contrast --------------------------------------------------
    root = re.search(r":root\s*\{(.*?)\}", html, re.S)
    if root:
        vars_ = dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", root.group(1)))
        for fg, bg in (("ink", "paper"), ("ink-2", "paper"), ("muted", "paper")):
            if fg in vars_ and bg in vars_:
                r = contrast(vars_[fg], vars_[bg])
                check(f"light contrast {fg} on {bg} >= 4.5", r >= 4.5, f"{r}:1")
    dark = re.search(r"prefers-color-scheme:\s*dark\s*\)\s*\{(.*?)\}", html, re.S)
    data_dark = re.search(r'(?::root|html)\[data-theme="dark"\]\s*\{(.*?)\}', html, re.S)
    # A manual theme toggle needs data-theme selectors, which is a better
    # implementation than a bare media query — accept either.
    check("dark mode defines its own surface tokens", dark is not None or data_dark is not None)
    block = data_dark or dark
    if block:
        dv = dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", block.group(1)))
        ink = dv.get("ink") or dv.get("fg") or dv.get("text")
        paper = dv.get("paper") or dv.get("bg") or dv.get("surface")
        if ink and paper:
            r = contrast(ink, paper)
            check("dark contrast ink on paper >= 4.5", r >= 4.5, f"{r}:1")
        else:
            check("dark block defines ink and paper", False, str(sorted(dv)))
    check("theme choice is persisted", bool(re.search(r"THEME_KEY|theme", html)) and "localStorage" in html)

    # The verdict must never argue with itself. Two shipped forms were wrong:
    # "A good day to open up. It climbs again by 00:00" (advice to ventilate,
    # immediately followed by a reason not to) and "Keep them shut until about
    # now" (a null trough hour rendered as a time). Asserting on source text is
    # brittle — my own comment tripped an earlier version — so this checks that
    # the blind-append VARIABLE is gone and that no verdict path emits a time in
    # front of a null-hour trough.
    check("the verdict no longer appends a blind climb clause",
          not re.search(r"\bconst climb\s*=", html),
          "a `const climb =` clause is still appended to every verdict form")
    check("the verdict branches on whether a trough hour exists",
          "hasTrough" in html, "a null trough hour can render as 'until about now'")
    # The four verdict forms that must exist. "calm" was removed on purpose: at
    # 4.8x the WHO guideline a reassuring word is false, so the calm-day branch
    # now frames against the guideline instead.
    for phrase in ("Keep them shut", "Open up at", "it is at its best",
                   "Windows open. ", "the WHO guideline"):
        check(f"a verdict form exists: {phrase!r}", phrase in html)

    # --- the API the page depends on still answers -------------------------
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(
                f"http://127.0.0.1:{PORT}/api/brief", method="POST",
                data=b"{}", headers={"Content-Type": "application/json"}),
            timeout=60).read()
        brief = json.loads(raw)["brief"]
        for k in ("next_trough", "next_peak", "elevated_now"):
            check(f"brief still carries {k}", k in brief)

        # The chart draws d.hourly; the legend quotes next_peak. If those two
        # disagree the picture and the number contradict each other about
        # tonight, which is exactly what happened when server._hourly averaged
        # the 48-hour response into a typical day.
        d = json.loads(raw)
        series = {r["hour"]: r["pm25"] for r in (d.get("hourly") or [])}
        peak = brief.get("next_peak") or {}
        if series and peak.get("hour") is not None:
            check("the chart's peak hour matches the legend's peak value",
                  abs(series.get(peak["hour"], -1) - peak["pm25"]) < 1.5,
                  f"chart[{peak['hour']}]={series.get(peak['hour'])} vs legend {peak['pm25']}")
            check("the legend's peak really is the series maximum",
                  max(series.values()) <= peak["pm25"] + 1.5,
                  f"series max {max(series.values())} vs legend {peak['pm25']}")

        # Every intervention in the API must be reachable on the page. The UI
        # sliced to 9 of 14 with no control to reveal the rest. Asserting on
        # source text is brittle (my own comment tripped it), so this checks
        # that no truncating slice is applied to the ranked array.
        ranked = d.get("ranked") or []
        truncates = re.search(r"\(d\.ranked \|\| \[\]\)\.slice\(", html) is not None
        check("the page does not truncate the ranking", not truncates,
              f"{len(ranked)} ranked in the API")
    except Exception as exc:
        check("brief endpoint answers", False, str(exc)[:60])

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
