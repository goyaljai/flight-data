# India Daily Context Dataset

This standalone Python collector publishes monthly `daily_context.csv` files for 15 Indian cities. Each observed city/date has two rows: `morning` at 09:00 IST and `late_afternoon` at 17:00 IST.

## Published data

```text
data/YYYY/MM/daily_context.csv
```

Rows retain `Date` and `City_Code` for daily joins and use `City_Code` plus scheduled `Capture_Timestamp` as the slot key. The CSV contains repeated daily weather/calendar/holiday fields and normalized slot fields: temperature, humidity, precipitation probability, wind speed, weather code, condition text, `Capture_Source`, and `Captured_At`.

The city codes are `BOM`, `DEL`, `BLR`, `HYD`, `MAA`, `CCU`, `PNQ`, `AMD`, `STV`, `VTZ`, `JAI`, `COK`, `IXC`, `IDR`, and `LKO`.

## Sources

Open-Meteo supplies daily historical weather and historical hourly values for the two slot times. SerpAPI supplies live slot observations. Historical slot rows are labeled `open-meteo-historical-hourly-backfill`; live rows are labeled `serpapi-google-weather`; failed live slots are labeled `unavailable` and retain blank observation fields. No random or fabricated values are inserted.

Calendar weekday/weekend values are generated locally. Indian holidays use `python-holidays` with state subdivisions. `CALENDARIFIC_API_KEY` is optional and is not required for the baseline collector.

## Automation

The VM remains in UTC and cron runs at:

```text
03:30 UTC = 09:00 IST
11:45 UTC = 17:15 IST
```

Each run loads the root-only `SERPAPI_API_KEY`, collects incrementally, writes private source state under `/var/lib/jai-dontdelete`, publishes only `data/YYYY/MM/daily_context.csv`, commits changed outputs, and pushes to GitHub. The runtime source state is separate from the Git checkout.

Dates are written through today only. Daily aggregate weather for the current date becomes available on the following run; current-day slot rows are still published immediately. A month rolls over automatically without manual date edits.

## Local usage

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
COLLECTOR_RUNTIME_ROOT=.runtime python -m collector --start 2026-06-01 --end 2026-09-25 --historical-slots
```

API keys are environment variables and must never be committed. Open-Meteo data requires CC BY 4.0 attribution.
