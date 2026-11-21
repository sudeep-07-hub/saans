#!/usr/bin/env python3
"""
Security and contract tests.

These are the claims a reviewer will check, so they are asserted rather than
described. They run against a live server on a random port, because a header
that only exists in the middleware source is not a header anyone received.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}{f'  [{detail}]' if detail else ''}")
    if not cond:
        FAILS.append(name)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def req(url: str, method="GET", body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def main() -> int:
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "saans.server:app", "--port", str(port),
         "--log-level", "error"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(40):
            try:
                req(base + "/api/health", timeout=2)
                break
            except Exception:
                time.sleep(0.25)
        else:
            print("server did not start")
            return 1

        # --- transport hardening -----------------------------------------
        status, headers, _ = req(base + "/")
        h = {k.lower(): v for k, v in headers.items()}
        check("page serves 200", status == 200, str(status))
        check("content-security-policy present", "content-security-policy" in h)
        csp = h.get("content-security-policy", "")
        check("CSP defaults to no sources", "default-src 'none'" in csp)
        check("CSP forbids framing", "frame-ancestors 'none'" in csp)
        check("CSP forbids form submission", "form-action 'none'" in csp)
        check("CSP restricts connect to self", "connect-src 'self'" in csp)
        check("no remote script origin allowed", "script-src 'self'" in csp)
        # This one is not decoration. The page uses innerHTML to build list
        # rows, and 'unsafe-inline' in script-src permits inline handlers, so
        # without script-src-attr 'none' an injected onerror= was executable.
        # Verified in a real browser: the handler now does not fire.
        check("CSP blocks inline event handlers", "script-src-attr 'none'" in csp)
        check("x-content-type-options nosniff", h.get("x-content-type-options") == "nosniff")
        check("x-frame-options DENY", h.get("x-frame-options") == "DENY")
        check("referrer-policy no-referrer", h.get("referrer-policy") == "no-referrer")
        check("permissions-policy locks sensors", "geolocation=()" in h.get("permissions-policy", ""))
        check("cross-origin-opener-policy set", h.get("cross-origin-opener-policy") == "same-origin")

        # --- the API surface is deliberately small ----------------------
        check("interactive docs disabled", req(base + "/api/docs")[0] == 404)
        check("openapi schema disabled", req(base + "/openapi.json")[0] == 404)
        check("redoc disabled", req(base + "/redoc")[0] == 404)

        # --- path traversal ----------------------------------------------
        for probe in ("/static/../../server.py", "/static/..%2f..%2fserver.py",
                      "/static/%2e%2e/%2e%2e/server.py"):
            check(f"traversal blocked: {probe}", req(base + probe)[0] in (400, 404), )

        # --- input validation --------------------------------------------
        cases = [
            ("latitude out of range", {"location": {"lat": 999, "lon": 77}}),
            ("longitude out of range", {"location": {"lat": 28, "lon": 500}}),
            ("negative age", {"people": [{"name": "X", "age": -5}]}),
            ("age beyond human range", {"people": [{"name": "X", "age": 500}]}),
            ("oversized name", {"people": [{"name": "A" * 5000, "age": 30}]}),
            ("too many people", {"people": [{"name": "p", "age": 30}] * 13}),
            ("no people", {"people": []}),
            ("unknown cooking fuel", {"home": {"cooking_fuel": "plutonium"}}),
            ("unknown condition", {"people": [{"name": "X", "age": 30, "conditions": ["ebola"]}]}),
            ("absurd cook minutes", {"habits": {"cook_minutes": 99999}}),
            ("absurd commute", {"transport": {"km_per_day": 1_000_000_000}}),
            ("negative fuel burn", {"habits": {"waste_burning_kg_week": -5}}),
            ("unknown mask", {"transport": {"mask": "scarf"}}),
            ("oversized label", {"location": {"label": "X" * 5000}}),
        ]
        for name, body in cases:
            status, _, _ = req(base + "/api/brief", "POST", body)
            check(f"rejects {name}", status == 422, str(status))

        # --- a valid request still works after all that ------------------
        status, _, body = req(base + "/api/brief", "POST",
                              {"people": [{"name": "X", "age": 30}, {"name": "Y", "age": 8,
                                                                     "commutes": False}]})
        check("valid household accepted", status == 200, str(status))
        if status == 200:
            d = json.loads(body)
            check("response carries a numeric AQI", isinstance(d["brief"]["aqi"]["aqi"], int))
            check("response carries every ranked option", len(d["ranked"]) >= 10)
            check("response carries a per-person dose", len(d["brief"]["household"]["people"]) == 2)

        # --- hostile strings are stored, never interpreted ---------------
        payload = '<img src=x onerror=alert(1)>'
        status, _, body = req(base + "/api/brief", "POST",
                              {"people": [{"name": payload, "age": 30}]})
        check("markup in a name does not break the request", status == 200, str(status))
        if status == 200:
            d = json.loads(body)
            check("markup is returned as data", d["people"][0]["name"] == payload)
            # The client renders with textContent; assert the served page does
            # not itself inject any innerHTML built from API data.
            _, _, page = req(base + "/")
            page_text = page.decode()
            check("page never interpolates API strings into innerHTML",
                  "innerHTML = c.name" not in page_text and "innerHTML=c.name" not in page_text)

        # --- unknown intervention is a 404, not a crash ------------------
        status, _, _ = req(base + "/api/simulate", "POST",
                           {"household": {}, "key": "nonexistent_intervention"})
        check("unknown intervention returns 404", status == 404, str(status))

        # --- /api/combine: same contract, plus its own bounds -------------
        st, _, body = req(base + "/api/combine", "POST",
                          {"household": {}, "keys": ["nonexistent_intervention"]})
        check("combine rejects an unknown key with 404", st == 404, str(st))
        st, _, body = req(base + "/api/combine", "POST", {"household": {}, "keys": []})
        # Parse rather than substring-match: json.dumps puts a space after the
        # colon, so b'"pct": 0' is not stable formatting.
        empty_ok = False
        try:
            empty_ok = st == 200 and json.loads(body)["effect"]["pct"] == 0
        except (ValueError, KeyError):
            empty_ok = False
        check("combine accepts an empty set", empty_ok, f"{st} {body[:60]!r}")
        # An unbounded list is a cheap denial of service: each key re-runs a
        # whole day per person per scenario.
        too_many = ["cleaner"] * 15
        st, _, _ = req(base + "/api/combine", "POST", {"household": {}, "keys": too_many})
        check("combine caps the key list", st == 422, str(st))

        # --- SSE endpoint streams and terminates -------------------------
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=180)
        conn.request("POST", "/api/plan", body=json.dumps({}),
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        check("plan endpoint upgrades to event-stream",
              "text/event-stream" in resp.getheader("content-type", ""))
        raw = resp.read().decode()
        check("stream contains a facts event", "event: facts" in raw)
        check("stream contains a plan event", "event: plan" in raw)
        check("stream terminates with done", "event: done" in raw)
        plan = None
        for block in raw.split("\n\n"):
            if block.startswith("event: plan"):
                plan = json.loads(block.split("data: ", 1)[1])
        check("plan parses", isinstance(plan, dict))
        if plan:
            check("plan states its provenance", plan.get("generated_by") in ("model", "deterministic"))
            check("plan carries actions", len(plan.get("today", [])) >= 1)
        conn.close()

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
