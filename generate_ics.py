#!/usr/bin/env python3
"""Generate weather calendar feeds (.ics) from Open-Meteo, ClimoCal-style.

Reads cities.json, writes one feed per city into calendars/ plus a combined
all.ics. Each day becomes an all-day event like "⛅ 88°/75°". Run daily
(GitHub Actions or launchd) so the 16-day window rolls forward; stable UIDs
mean subscribed calendars update in place instead of duplicating events.

No dependencies — Python 3 stdlib only.
"""
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "calendars"
FORECAST_DAYS = 16

# WMO weather code -> (emoji, description); mirrors index.html
WEATHER = {
    0: ("☀️", "Clear sky"), 1: ("🌤️", "Mostly clear"), 2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"), 45: ("🌫️", "Fog"), 48: ("🌫️", "Icy fog"),
    51: ("🌦️", "Light drizzle"), 53: ("🌦️", "Drizzle"), 55: ("🌧️", "Heavy drizzle"),
    56: ("🌧️", "Freezing drizzle"), 57: ("🌧️", "Freezing drizzle"),
    61: ("🌧️", "Light rain"), 63: ("🌧️", "Rain"), 65: ("🌧️", "Heavy rain"),
    66: ("🌧️", "Freezing rain"), 67: ("🌧️", "Freezing rain"),
    71: ("🌨️", "Light snow"), 73: ("🌨️", "Snow"), 75: ("❄️", "Heavy snow"),
    77: ("🌨️", "Snow grains"), 80: ("🌦️", "Light showers"), 81: ("🌧️", "Showers"),
    82: ("⛈️", "Heavy showers"), 85: ("🌨️", "Snow showers"), 86: ("❄️", "Snow showers"),
    95: ("⛈️", "Thunderstorm"), 96: ("⛈️", "Storm with hail"), 99: ("⛈️", "Storm with hail"),
}


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def ics_escape(text):
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")


def fold(line):
    """RFC 5545 line folding: max 75 octets per line, continuations indented."""
    out, cur, cur_len = [], "", 0
    for ch in line:
        ch_len = len(ch.encode("utf-8"))
        if cur_len + ch_len > 75:
            out.append(cur)
            cur, cur_len = " " + ch, 1 + ch_len
        else:
            cur, cur_len = cur + ch, cur_len + ch_len
    out.append(cur)
    return out


def fetch_forecast(city, unit):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={city['lat']}&longitude={city['lon']}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min"
        f"&temperature_unit={unit}&timezone=auto&forecast_days={FORECAST_DAYS}"
    )
    with urllib.request.urlopen(url, timeout=30) as res:
        return json.load(res)


def vevent(city, date, code, hi, lo, stamp, updated_local, include_city_name):
    emoji, desc = WEATHER.get(code, ("🌡️", "Forecast"))
    label = f" {city['name']}" if include_city_name else ""
    return [
        "BEGIN:VEVENT",
        f"UID:{slugify(city['name'])}-{date}@my-weather",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{date.replace('-', '')}",
        "SUMMARY:" + ics_escape(f"{emoji} {round(hi)}°/{round(lo)}°{label}"),
        "DESCRIPTION:" + ics_escape(
            f"{city['name']}: {desc}. High {round(hi)}°, low {round(lo)}°."
            f" Updated {updated_local}."
        ),
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def vcalendar(name, event_lines):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//My Weather//Open-Meteo//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + ics_escape(name),
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
        *event_lines,
        "END:VCALENDAR",
    ]
    return "\r\n".join(folded for line in lines for folded in fold(line)) + "\r\n"


def main():
    config = json.loads((ROOT / "cities.json").read_text())
    unit = config.get("unit", "celsius")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(exist_ok=True)

    all_events = []
    for city in config["cities"]:
        data = fetch_forecast(city, unit)
        daily = data["daily"]
        local_now = datetime.now(timezone.utc) + timedelta(seconds=data.get("utc_offset_seconds", 0))
        updated_local = local_now.strftime("%b %-d, %-I:%M %p")
        city_events, combined = [], []
        for date, code, hi, lo in zip(
            daily["time"], daily["weather_code"],
            daily["temperature_2m_max"], daily["temperature_2m_min"],
        ):
            if hi is None or lo is None:  # far end of the window can lack data
                continue
            city_events += vevent(city, date, code, hi, lo, stamp, updated_local, include_city_name=False)
            combined += vevent(city, date, code, hi, lo, stamp, updated_local, include_city_name=True)
        all_events += combined

        path = OUT_DIR / f"{slugify(city['name'])}.ics"
        path.write_text(vcalendar(f"Weather — {city['name']}", city_events), encoding="utf-8")
        print(f"wrote {path.name}: {len(daily['time'])} days")

    (OUT_DIR / "all.ics").write_text(vcalendar("Weather — All Cities", all_events), encoding="utf-8")
    print(f"wrote all.ics: {len(config['cities'])} cities")


if __name__ == "__main__":
    main()
