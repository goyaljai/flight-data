# ✈️ The India Flight Prices Dataset

Welcome to the **Automated Indian Aviation Dataset**. This repository hosts a massive, continuously growing database of flight prices across the 15 largest cities in India. 

This dataset is designed specifically for **Deep Learning, Time-Series Forecasting, and Machine Learning** projects.

## ⚙️ Architecture & Methodology
Unlike static Kaggle datasets that suffer from "data decay", this dataset updates itself **every single day autonomously**.

* **The Engine:** A GitHub Actions cron job pings the SerpApi (Google Flights) engine daily at exactly 12:00 UTC.
* **The Target Matrix:** It tracks flights across 15 major cities (210 total permutations).
* **The Rotation Strategy:** To optimize API limits while capturing rolling data, the scraper uses a **3-Day Rotation Matrix**. It divides the 210 routes into 3 batches, scraping one batch per day.
* **The Horizon:** For every route, it captures the price exactly **7, 14, 30, and 60 days out** to map the "Surge Zone" and "Advance Booking" curves.

---

## 📊 Data Dictionary (Column Breakdown)

The `massive_flight_dataset.csv` file contains highly detailed, multivariate features for every single flight. Here is exactly what each column represents:

| Column Name | Type | Description |
| :--- | :--- | :--- |
| **`Scrape_Timestamp`** | `Datetime` | The exact time the scraper queried the API. This is crucial for tracking "when" the price was recorded. |
| **`Days_to_Departure`** | `Integer` | The number of days between the scrape date and the flight date. Guaranteed to be exactly `7`, `14`, `30`, or `60`. |
| **`Departure_Date`** | `Date` | The actual calendar date the flight takes off (Format: YYYY-MM-DD). |
| **`Day_of_Week`** | `String` | The day of the week for the departure date (e.g., `Monday`, `Friday`). Highly useful for weekend surge pricing analysis. |
| **`Departure_Time`** | `String` | The time of day the flight takes off (e.g., `10:00`). |
| **`Arrival_Time`** | `String` | The time of day the flight lands at its destination (e.g., `12:20`). |
| **`Source_City`** | `String` | The 3-letter IATA Airport Code of the departure city (e.g., `BLR` for Bengaluru). |
| **`Destination_City`** | `String` | The 3-letter IATA Airport Code of the arrival city (e.g., `JAI` for Jaipur). |
| **`Airline`** | `String` | The carrier operating the flight (e.g., `IndiGo`, `Air India`, `Akasa Air`). |
| **`Flight_Number`** | `String` | The unique alphanumeric identifier for the flight (e.g., `6E 5212`). |
| **`Total_Duration_Mins`** | `Integer` | The total duration of the trip from takeoff to final landing, measured in minutes. |
| **`Number_of_Stops`** | `Integer` | `0` indicates a direct flight. `1` or more indicates layovers. |
| **`CO2_Emissions_Grams`** | `Integer` | The estimated carbon footprint of the flight. Excellent for complex multi-variable Deep Learning models. |
| **`Price_Level`** | `String` | Google's internal classification of the fare (`high`, `typical`, or `low`). Extremely powerful categorical feature for ML. |
| **`Flight_Category`** | `String` | Denotes whether this specific row represents the `"Best"` flight recommended by Google, or the absolute `"Cheapest"` flight available. |
| **`Price_INR`** | `Integer` | The exact price of this specific flight at the exact moment of scraping, in Indian Rupees (₹). |

---

## 🏙️ Cities Tracked
* Mumbai (`BOM`), Delhi (`DEL`), Bengaluru (`BLR`), Hyderabad (`HYD`), Chennai (`MAA`), Kolkata (`CCU`), Pune (`PNQ`), Ahmedabad (`AMD`), Surat (`STV`), Visakhapatnam (`VTZ`), Jaipur (`JAI`), Kochi (`COK`), Chandigarh (`IXC`), Indore (`IDR`), Lucknow (`LKO`).

---

## Daily Context Collector (Weather, Calendar, Holidays)

The `collector` package builds per-day context features for the flight dataset, written as monthly CSV partitions under `data/YYYY/MM/`. Join keys: weather joins on `City_Code` + `Date`, holidays join on `Date` + `State_Region` (the city's subdivision code, or `National` — the city-to-subdivision mapping lives in `collector/config.py`), calendar joins on `Date`.

### Setup

```
pip install -r requirements.txt
```

### Commands

```
python -m collector                                   # full range: 2026-06-01 through today in India
python -m collector --incremental                     # fetch only dates missing from existing CSVs
python -m collector --start 2026-06-01 --end 2026-09-25
python -m collector --only weather                    # or: calendar, holidays (repeatable flag)
```

Optional: export `CALENDARIFIC_API_KEY` (see `.env.example`) to cross-fill holiday dates from Calendarific (one request per state per year). Variables must be present in the process environment — the collector reads `os.environ` directly and does not auto-load `.env` files. `SERPAPI_API_KEY` is reserved for the flight scraper and is not used by the context collector. Transient API failures are retried with backoff; persistent API failures abort the run with a non-zero exit, while malformed rows are skipped and logged to `data/failures.log`.

### Output Schemas

| File | Granularity | Columns |
| :--- | :--- | :--- |
| `data/YYYY/MM/weather.csv` | one row per city/date | `Date`, `City`, `City_Code`, `Latitude`, `Longitude`, `Temperature_Max_C`, `Temperature_Min_C`, `Temperature_Mean_C`, `Apparent_Temperature_Max_C`, `Apparent_Temperature_Min_C`, `Precipitation_Sum_MM`, `Rain_Sum_MM`, `Precipitation_Hours`, `Wind_Speed_Max_KMH`, `Wind_Gusts_Max_KMH`, `Wind_Direction_Dominant_Deg`, `Weather_Code`, `Weather_Source` |
| `data/YYYY/MM/calendar.csv` | one row per date | `Date`, `Day_of_Week`, `Is_Weekend` |
| `data/YYYY/MM/holidays.csv` | one row per holiday/region/date | `Date`, `Holiday_Name`, `Holiday_Type`, `State_Region` (`National` or a state/UT code), `Is_Holiday`, `Source` |

### Data Sources & Licensing

* **Weather: Open-Meteo.** Past dates use the Historical Forecast API (archived operational model runs, most accurate for recent years); dates before 2022 fall back to the Historical Weather API (ERA5). The collector stores dates through today only and never writes forecast placeholders. Weather data is licensed **CC BY 4.0** — attribution is required. Cite: Zippenfenig, P. (2023), *Open-Meteo.com Weather API*, https://doi.org/10.5281/ZENODO.7970649; and when ERA5 data is used: Hersbach, H. et al. (2023), *ERA5 hourly data on single levels from 1940 to present*, ECMWF, https://doi.org/10.24381/cds.adbb2d47. The free tier is **non-commercial use only** (10,000 calls/day, no uptime guarantee); commercial use of this pipeline requires an Open-Meteo subscription.
* **Holidays: `python-holidays`** (MIT, https://github.com/vacanza/holidays), India country + subdivision calendars, both `PUBLIC` and `GOVERNMENT` categories. Optional enrichment from Calendarific (https://calendarific.com) when `CALENDARIFIC_API_KEY` is set.
* **Calendar:** derived deterministically from the Gregorian calendar; no external source.
* **Alternatives considered and rejected:** IMD station data (no stable public REST API suitable for unattended collection) and NOAA GSOD (observation-only; cannot cover future flight dates) were evaluated and are not used as primary sources.

### Known Limitations

* **Only dates through today are stored.** Future flight dates are intentionally excluded because this dataset is for observed/historical daily context, not forecast snapshots.
* **Grid-cell, not airport-station, values.** Open-Meteo returns model grid-cell estimates (9–25 km); for coastal cities (`BOM`, `MAA`, `COK`, `VTZ`, `STV`) the selected land grid cell may differ from airport conditions.
* **Reproducibility tiers differ.** Historical Forecast rows are archived operational model output and can shift slightly if re-fetched after upstream model upgrades; the ERA5 tier is the stable long-term-consistency option.
* **Holiday coverage is 2001–2035.** `python-holidays` derives India dates from archived government and secondary calendar sources; some Hindu/Islamic lunar holidays are astronomically estimated and flagged `(estimated)` by the library. The collector fails loudly for years outside the supported range.
* **Holiday rows are append-only.** Storage upserts by key and never deletes. If the pinned `holidays` version is later bumped and a holiday's name or estimated date changes, superseded rows can persist — regenerate the affected `data/YYYY/MM/holidays.csv` files from scratch after a version bump.
