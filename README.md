# India Daily Context Dataset

This repository contains a standalone Python collector for daily weather, calendar, Indian public-holiday, and optional festival context for 15 Indian cities. The output is partitioned by month under `data/YYYY/MM/` so each month's files remain independently manageable.

## Cities

Mumbai (`BOM`), Delhi (`DEL`), Bengaluru (`BLR`), Hyderabad (`HYD`), Chennai (`MAA`), Kolkata (`CCU`), Pune (`PNQ`), Ahmedabad (`AMD`), Surat (`STV`), Visakhapatnam (`VTZ`), Jaipur (`JAI`), Kochi (`COK`), Chandigarh (`IXC`), Indore (`IDR`), and Lucknow (`LKO`).

## Output

- `weather.csv`: one logical row per `City_Code` + `Date`, with model/reanalysis daily weather fields and `Weather_Source` provenance.
- `calendar.csv`: one row per `Date`, with `Day_of_Week` and `Is_Weekend`.
- `holidays.csv`: one row per holiday/date/region, including national and city-state rows where available.

The stable join keys are `City_Code` + `Date` for weather, and `Date` plus the relevant region for holidays. No future forecast placeholders are written; collection ends at today in `Asia/Kolkata` unless an explicit end date is supplied.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

API keys are read only from environment variables. Copy `.env.example` to a local, ignored file or export variables in the process environment. The collector does not auto-load `.env` files.

## Commands

```bash
python -m collector
python -m collector --incremental
python -m collector --start 2026-06-01 --end 2026-09-25
python -m collector --only weather
python -m collector --only calendar --only holidays
python -m collector --serpapi-label morning --only weather
python -m collector --serpapi-label midday --only weather
```

The initial backfill for this checkout is 2026-06-01 through 2026-09-25. Repeated incremental runs detect existing city/date records and avoid duplicate API work. Failed requests are retried with exponential backoff; persistent failures are not converted into null weather rows. Malformed rows are recorded in `data/failures.log`.

## Source decisions

### Weather

Open-Meteo is the primary historical source because it provides daily fields, supports the Indian locations, permits all configured locations in one request, and is suitable for historical backfill. Dates from 2022 onward use Open-Meteo's Historical Forecast API; older supported dates use the Historical Weather API/ERA5. The collector preserves the source name in each row.

SerpAPI Google Weather is an optional supplementary source for current daily observations. It is not a historical database: its weather answer box is current/forecast-oriented, returns unit-bearing strings and weekday labels, and cannot reliably reconstruct a missed historical date. It can be used for twice-daily current snapshots and fallback/cross-check collection, but those snapshots belong in a separate audit dataset rather than silently replacing the consistent historical series. Configure it with `SERPAPI_API_KEY`; never commit the key.

SerpAPI rows are written to monthly `weather_snapshots.csv` files. Only parsed fields needed for analysis are retained; full API JSON responses are deliberately discarded. Snapshot keys include capture timestamp, city, and label, so morning and midday captures are retained independently.

Open-Meteo weather data requires CC BY 4.0 attribution. See https://open-meteo.com/en/license and cite Zippenfenig, P. (2023), *Open-Meteo.com Weather API*, https://doi.org/10.5281/ZENODO.7970649. The free service is intended for non-commercial use and has no uptime guarantee; use a suitable subscription for commercial operation.

### Holidays and festivals

The deterministic baseline is `python-holidays` with India subdivisions for the configured states and union territory. It is local, MIT-licensed, and avoids one request per date. Optional Calendarific enrichment can be enabled with `CALENDARIFIC_API_KEY`; source-specific rows and disagreements are preserved instead of silently overwriting the baseline.

Nager.Date and the community Indian Festivals API are treated as optional enrichment candidates, not authoritative replacements. Nager.Date exposes annual holiday responses with subdivision codes and holiday types, but India subdivision completeness must be checked for each requested year. The Indian Festivals API provides useful state-wise cultural/festival enrichment for 2025–2040, but it is static community data and lunar/observance dates can vary. Official central and state notifications remain the strongest authority when an exact annual gazette is required.

### Calendar

Weekday and weekend values are generated locally from the Gregorian calendar and require no external API.

## Data quality and limitations

- Validation rejects invalid city codes, malformed dates, duplicate city/date keys, and unexpected API cardinality.
- Weather values are grid-cell model/reanalysis estimates, not necessarily airport-station observations.
- Open-Meteo and SerpAPI values must remain distinguishable through provenance.
- Lunar and regional holiday dates may be estimated or revised after official notifications.
- When the pinned holiday library is upgraded, regenerate affected holiday partitions if historical names or estimated dates change.

## Automation

The collector is designed for a twice-daily cron or GitHub Actions schedule. The VM uses 00:30 and 06:30 UTC, equivalent to 06:00 and 12:00 IST, without changing the shared VM timezone. Each run commits and pushes successful CSV/source changes using the dedicated GitHub deploy key; failures remain in VM logs and successful data is still pushed. Existing unrelated flight-scraper cron jobs remain untouched.
