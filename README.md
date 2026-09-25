# India Daily Context Dataset

This standalone Python collector produces one clean monthly CSV per month for 15 Indian cities. Each `daily_context.csv` row is one `City_Code` + `Date` and combines calendar, weather, holiday, and morning/midday SerpAPI fields.

## Output

```text
data/YYYY/MM/daily_context.csv
```

Only `daily_context.csv` is published to GitHub. The collector may use private migration/runtime inputs locally, but `calendar.csv`, `holidays.csv`, `weather.csv`, `weather_snapshots.csv`, and macOS `._*` sidecars are ignored and removed from Git tracking. Raw SerpAPI JSON is never retained.

## Operation

The VM runs at 00:30 and 06:30 UTC, equivalent to 06:00 and 12:00 IST without changing the shared VM timezone. Every run incrementally collects missing source data, rebuilds the affected `daily_context.csv`, commits CSV/source changes, and pushes them to GitHub with the dedicated deploy key. Individual SerpAPI city failures are logged while successful city rows are retained.

## Sources

Open-Meteo supplies consistent historical daily weather; SerpAPI supplies current morning/midday observations; `python-holidays` supplies deterministic Indian national/state holiday data; calendar weekday/weekend values are generated locally. Source fields remain explicit in the combined CSV. Open-Meteo requires CC BY 4.0 attribution.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python -m collector --start 2026-06-01 --end 2026-09-25
```

API keys are environment variables. `SERPAPI_API_KEY` is installed only in the VM root secret file and is never committed.
