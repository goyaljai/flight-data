"""Tiered Open-Meteo daily weather rows for all configured cities."""
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .config import (
    CITIES,
    HISTORICAL_FORECAST_MIN_DATE,
    OPEN_METEO_HISTORICAL_FORECAST_URL,
    OPEN_METEO_HISTORICAL_URL,
)
from .http import HttpError, get_json

logger = logging.getLogger(__name__)

WEATHER_FIELDS = (
    "Date",
    "City",
    "City_Code",
    "Latitude",
    "Longitude",
    "Temperature_Max_C",
    "Temperature_Min_C",
    "Temperature_Mean_C",
    "Apparent_Temperature_Max_C",
    "Apparent_Temperature_Min_C",
    "Precipitation_Sum_MM",
    "Rain_Sum_MM",
    "Precipitation_Hours",
    "Wind_Speed_Max_KMH",
    "Wind_Gusts_Max_KMH",
    "Wind_Direction_Dominant_Deg",
    "Weather_Code",
    "Weather_Source",
)

SOURCE_ERA5 = "open-meteo-era5"
SOURCE_HISTORICAL_FORECAST = "open-meteo-historical-forecast"

_DAILY_VARIABLES = (
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "rain_sum",
    "precipitation_hours",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
    "weather_code",
)

_FIELD_TO_PARAM = (
    ("Temperature_Max_C", "temperature_2m_max"),
    ("Temperature_Min_C", "temperature_2m_min"),
    ("Temperature_Mean_C", "temperature_2m_mean"),
    ("Apparent_Temperature_Max_C", "apparent_temperature_max"),
    ("Apparent_Temperature_Min_C", "apparent_temperature_min"),
    ("Precipitation_Sum_MM", "precipitation_sum"),
    ("Rain_Sum_MM", "rain_sum"),
    ("Precipitation_Hours", "precipitation_hours"),
    ("Wind_Speed_Max_KMH", "wind_speed_10m_max"),
    ("Wind_Gusts_Max_KMH", "wind_gusts_10m_max"),
    ("Wind_Direction_Dominant_Deg", "wind_direction_10m_dominant"),
    ("Weather_Code", "weather_code"),
)

_TIER_URLS = {
    SOURCE_ERA5: OPEN_METEO_HISTORICAL_URL,
    SOURCE_HISTORICAL_FORECAST: OPEN_METEO_HISTORICAL_FORECAST_URL,
}


def tier_spans(start, end, today):
    spans = {}
    era5_end = min(end, HISTORICAL_FORECAST_MIN_DATE - timedelta(days=1))
    if start <= era5_end:
        spans[SOURCE_ERA5] = (start, era5_end)
    hf_start = max(start, HISTORICAL_FORECAST_MIN_DATE)
    hf_end = min(end, today - timedelta(days=1))
    if hf_start <= hf_end:
        spans[SOURCE_HISTORICAL_FORECAST] = (hf_start, hf_end)
    return spans


def ist_today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def weather_rows(start, end, today=None):
    today = today or ist_today()
    if start > end:
        raise ValueError(f"start {start} is after end {end}")
    spans = tier_spans(start, end, today)
    rows = []
    for source in (SOURCE_ERA5, SOURCE_HISTORICAL_FORECAST):
        if source in spans:
            tier_start, tier_end = spans[source]
            logger.info("weather: %s %s..%s", source, tier_start, tier_end)
            rows.extend(_fetch_tier(source, tier_start, tier_end))
    return rows


def missing_weather_dates(existing_rows, start, end, today):
    present = {}
    for row in existing_rows:
        present[(row.get("City_Code", ""), row.get("Date", ""))] = row.get("Weather_Source", "")
    missing = set()
    current = start
    while current <= end:
        iso = current.isoformat()
        for city in CITIES:
            source = present.get((city.code, iso))
            if (
                source is None
            ):
                missing.add(current)
                break
        current += timedelta(days=1)
    return missing


def _fetch_tier(source, start, end):
    url = _TIER_URLS[source]
    context = f"open-meteo {source} {start}..{end}"
    params = {
        "latitude": ",".join(str(c.latitude) for c in CITIES),
        "longitude": ",".join(str(c.longitude) for c in CITIES),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(_DAILY_VARIABLES),
        "timezone": "Asia/Kolkata",
    }
    payload = get_json(url, params, context=context)
    entries = payload if isinstance(payload, list) else [payload]
    if len(entries) != len(CITIES):
        raise HttpError(f"{context}: expected {len(CITIES)} locations, got {len(entries)}")
    rows = []
    expected_days = (end - start).days + 1
    for city, entry in zip(CITIES, entries):
        _check_coordinates(city, entry, context)
        times = entry.get("daily", {}).get("time") or []
        if len(times) != expected_days:
            raise HttpError(f"{context}: {city.code}: expected {expected_days} days, got {len(times)}")
        rows.extend(_entry_rows(city, entry, source))
    return rows


def _check_coordinates(city, entry, context):
    try:
        lat_diff = abs(float(entry.get("latitude", city.latitude)) - city.latitude)
        lon_diff = abs(float(entry.get("longitude", city.longitude)) - city.longitude)
    except (TypeError, ValueError):
        return
    if lat_diff > 0.5 or lon_diff > 0.5:
        logger.warning("%s: %s grid cell is %.2f/%.2f deg away from city centroid",
                       context, city.code, lat_diff, lon_diff)


def _entry_rows(city, entry, source):
    daily = entry.get("daily", {})
    rows = []
    for index, day in enumerate(daily.get("time") or []):
        row = _base_row(city, day, source)
        for field, param in _FIELD_TO_PARAM:
            values = daily.get(param) or []
            value = values[index] if index < len(values) else None
            row[field] = "" if value is None else value
        rows.append(row)
    return rows


def _base_row(city, day, source):
    row = {
        "Date": day,
        "City": city.name,
        "City_Code": city.code,
        "Latitude": city.latitude,
        "Longitude": city.longitude,
        "Weather_Source": source,
    }
    for field, _ in _FIELD_TO_PARAM:
        row[field] = ""
    return row
