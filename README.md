# My Weather

Minimal weather dashboard + Apple Calendar feeds, in the style of [ClimoCal](https://climocal.johnnyhockin.com).

- **Web app**: [index.html](index.html) — current location (geolocation) plus any cities or zip codes you add. Served via GitHub Pages.
- **Calendar feeds**: `calendars/<city>.ics` — 16-day forecast as all-day events (`☀️ 88°/72°`), regenerated hourly by [GitHub Actions](.github/workflows/update-calendars.yml).

## Subscribe in Apple Calendar

Mac: Calendar → File → New Calendar Subscription… → paste the feed URL.
Set **Location: iCloud** (syncs to iPhone), **Auto-refresh: Every hour**, **Alerts: Remove**.

## Add a calendar city

Edit [cities.json](cities.json) (name + coordinates), commit — the next hourly run picks it up and a new `calendars/<name>.ics` appears.

Weather data by [Open-Meteo](https://open-meteo.com/). Zip lookup by [Zippopotam.us](https://api.zippopotam.us).
