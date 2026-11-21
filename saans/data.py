"""
Live air quality and weather, plus an honest offline fallback.

Upstream: Open-Meteo (air quality + forecast), CAMS Europe/global models for
the pollutant fields, and Open-Meteo's geocoder. No API key, no account, and
the only thing that leaves the device is a latitude and longitude.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from .engine import Ambient

UA = "Saans/1.0 (community air-quality assistant; local use)"
TIMEOUT = 12

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_URL = "https://api.open-meteo.com/v1/forecast"

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 900  # 15 minutes; the upstream model updates hourly


def _get(url: str, params: dict) -> dict:
    key = url + "?" + urllib.parse.urlencode(params)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    req = urllib.request.Request(
        key, headers={"User-Agent": UA, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    _cache[key] = (time.time(), data)
    return data


# Seasonal climatology used only when there is no network. These are rough
# city-level winter/summer means, labelled as modelled in the UI. Delhi
# November PM2.5 runs 150-250 ug/m3; monsoon June-August is 30-60.
CLIMATOLOGY = {
    "delhi": [180, 150, 110, 95, 90, 70, 55, 45, 55, 120, 200, 210],
    "gurugram": [175, 145, 110, 95, 90, 70, 55, 45, 55, 120, 195, 205],
    "noida": [170, 145, 108, 92, 88, 68, 54, 44, 54, 118, 190, 200],
    "ghaziabad": [180, 150, 110, 95, 92, 70, 56, 46, 56, 122, 200, 210],
    "faridabad": [170, 145, 108, 92, 88, 68, 54, 44, 54, 118, 190, 200],
    "kanpur": [165, 140, 105, 90, 88, 72, 60, 50, 60, 125, 190, 200],
    "lucknow": [160, 140, 105, 90, 86, 70, 58, 48, 58, 120, 185, 195],
    "patna": [175, 150, 110, 95, 90, 72, 58, 48, 58, 125, 195, 205],
    "mumbai": [95, 80, 65, 55, 45, 40, 32, 30, 38, 60, 95, 110],
    "kolkata": [120, 105, 85, 75, 68, 55, 45, 42, 50, 85, 130, 145],
    "bengaluru": [55, 50, 48, 45, 40, 32, 26, 24, 30, 42, 55, 60],
    "chennai": [55, 50, 45, 42, 38, 32, 28, 26, 30, 40, 50, 58],
    "hyderabad": [65, 60, 55, 50, 45, 38, 32, 30, 36, 50, 65, 72],
    "lahore": [190, 170, 140, 120, 110, 95, 80, 70, 80, 130, 200, 210],
    "dhaka": [180, 160, 135, 120, 110, 95, 75, 65, 75, 120, 175, 190],
    "kathmandu": [150, 140, 120, 100, 90, 70, 55, 50, 60, 100, 155, 165],
}


def geocode(name: str, count: int = 6) -> list[dict]:
    try:
        data = _get(GEOCODE_URL, {"name": name, "count": count, "language": "en", "format": "json"})
        out = []
        for r in data.get("results", []) or []:
            out.append({
                "name": r.get("name"),
                "admin": r.get("admin1"),
                "country": r.get("country"),
                "country_code": r.get("country_code"),
                "lat": r.get("latitude"),
                "lon": r.get("longitude"),
                "timezone": r.get("timezone"),
                "population": r.get("population") or 0,
                "label": ", ".join(x for x in [r.get("name"), r.get("admin1"), r.get("country")] if x),
            })
        return out
    except Exception:
        return []


def _climatology(lat: float, lon: float, label: str) -> tuple[float, str]:
    month = datetime.now().month
    text = (label or "").lower()
    for key, series in CLIMATOLOGY.items():
        if key in text:
            return float(series[month - 1]), key
    # fall back to a latitude-based guess and say so
    if abs(lat) > 45:
        return (35.0 if month in (6, 7, 8) else 20.0), "latitude estimate"
    return (60.0 if month in (11, 12, 1, 2) else 40.0), "latitude estimate"


def fetch_ambient(lat: float, lon: float, label: str = "", tz: str = "auto") -> Ambient:
    """Current pollutant field plus the next 48 hours, with a labelled fallback."""
    amb = Ambient()
    live = False

    try:
        aq = _get(AIR_URL, {
            "latitude": lat, "longitude": lon,
            "current": "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,us_aqi",
            "hourly": "pm2_5,pm10,nitrogen_dioxide",
            "forecast_days": 2, "timezone": tz,
        })
        cur = aq.get("current") or {}
        if cur.get("pm2_5") is not None:
            amb.pm25 = float(cur["pm2_5"])
            amb.pm10 = cur.get("pm10")
            amb.no2 = cur.get("nitrogen_dioxide")
            amb.label = (aq.get("timezone_abbreviation") or "local") + " CAMS model"
            amb.source = "Open-Meteo / CAMS air quality model"
            live = True
            # The observation time is the only trustworthy clock here: the
            # hourly series begins at midnight, so its first row says hour 0 at
            # any time of day. Keep the upstream hour so "what happens next"
            # starts now rather than at 00:00.
            ct = cur.get("time")
            if isinstance(ct, str) and len(ct) >= 13:
                try:
                    amb.obs_hour = int(ct[11:13]) % 24
                except ValueError:
                    amb.obs_hour = None
        hourly = aq.get("hourly") or {}
        times = hourly.get("time") or []
        vals = hourly.get("pm2_5") or []
        for i, t in enumerate(times):
            if i >= len(vals) or vals[i] is None:
                continue
            try:
                hour = int(str(t)[11:13])
            except Exception:
                continue
            amb.hourly.append({"time": t, "hour": hour, "pm25": float(vals[i])})
    except Exception:
        pass

    try:
        wx = _get(WX_URL, {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "timezone": tz,
        })
        cur = wx.get("current") or {}
        amb.temp_c = cur.get("temperature_2m")
        amb.rh = cur.get("relative_humidity_2m")
        amb.wind_kmh = cur.get("wind_speed_10m")
    except Exception:
        pass

    if not live:
        pm, key = _climatology(lat, lon, label)
        amb.pm25 = pm
        amb.pm10 = round(pm * 1.9, 0)
        amb.no2 = round(pm * 0.45, 0)
        amb.label = f"modelled seasonal average ({key})"
        amb.source = "offline seasonal climatology - not a live measurement"
        amb.hourly = [{"hour": h, "pm25": round(pm * (0.75 + 0.5 * _diurnal(h)), 1), "time": f"--T{h:02d}"}
                      for h in range(24)]

    return amb


def _diurnal(hour: int) -> float:
    """Winter-time shape: inversion peak around 0600-0900 and again 2000-2300."""
    import math
    morning = math.exp(-((hour - 7) ** 2) / 12)
    evening = math.exp(-((hour - 21) ** 2) / 18)
    midday = math.exp(-((hour - 14) ** 2) / 30)
    return 0.45 * morning + 0.55 * evening - 0.35 * midday


def worst_hour(ambient: Ambient) -> dict:
    if not ambient.hourly:
        return {"hour": 8, "pm25": ambient.pm25}
    best = max(ambient.hourly, key=lambda r: r.get("pm25") or 0)
    return {"hour": best.get("hour"), "pm25": round(best.get("pm25") or ambient.pm25, 1)}


def cleanest_hour(ambient: Ambient, morning_only: bool = True) -> dict:
    rows = [r for r in ambient.hourly if r.get("pm25") is not None]
    if morning_only:
        rows = [r for r in rows if 5 <= (r.get("hour") or 0) <= 11] or rows
    if not rows:
        return {"hour": 15, "pm25": ambient.pm25}
    best = min(rows, key=lambda r: r.get("pm25") or 0)
    return {"hour": best.get("hour"), "pm25": round(best.get("pm25") or ambient.pm25, 1)}


def stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
