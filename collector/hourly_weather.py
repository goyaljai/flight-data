"""Open-Meteo hourly historical slot data."""
from datetime import date

from .config import CITIES, OPEN_METEO_HISTORICAL_FORECAST_URL, SLOT_HOURS, SLOT_LATE_AFTERNOON, SLOT_MORNING
from .http import get_json


def historical_slot_rows(start, end):
    payload = get_json(OPEN_METEO_HISTORICAL_FORECAST_URL, {"latitude": ",".join(str(c.latitude) for c in CITIES), "longitude": ",".join(str(c.longitude) for c in CITIES), "start_date": start.isoformat(), "end_date": end.isoformat(), "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,weather_code", "timezone": "Asia/Kolkata"}, context="Open-Meteo hourly historical slots")
    entries = payload if isinstance(payload, list) else [payload]
    rows = []
    current = start
    while current <= end:
        for city, entry in zip(CITIES, entries):
            hourly = entry.get("hourly", {})
            indexes = {value: index for index, value in enumerate(hourly.get("time", []))}
            for label, hour in SLOT_HOURS.items():
                index = indexes.get(f"{current.isoformat()}T{hour:02d}:00")
                rows.append(_row(city, current, label, hourly, index, "open-meteo-historical-hourly-backfill"))
        current = date.fromordinal(current.toordinal() + 1)
    return rows


def _row(city, day, label, hourly, index, source):
    values = {name: _value(hourly, name, index) for name in ("temperature_2m", "relative_humidity_2m", "precipitation_probability", "wind_speed_10m", "weather_code")}
    return {"Date": day.isoformat(), "City": city.name, "City_Code": city.code, "Capture_Label": label, "Capture_Timestamp": _scheduled(day, label), "Captured_At": "", "Temperature_C": values["temperature_2m"], "Humidity_Percent": values["relative_humidity_2m"], "Precipitation_Probability": values["precipitation_probability"], "Wind_Speed": values["wind_speed_10m"], "Weather_Code": values["weather_code"], "Weather_Condition": _condition(values["weather_code"]), "Capture_Source": source}


def _scheduled(day, label):
    return f"{day.isoformat()}T{SLOT_HOURS[label]:02d}:00:00+05:30"


def _value(hourly, name, index):
    if index is None:
        return ""
    values = hourly.get(name, [])
    return values[index] if index < len(values) and values[index] is not None else ""


def _condition(code):
    return {0: "clear", 1: "mainly_clear", 2: "partly_cloudy", 3: "overcast", 45: "fog", 48: "depositing_rime_fog", 51: "light_drizzle", 53: "moderate_drizzle", 55: "dense_drizzle", 61: "slight_rain", 63: "moderate_rain", 65: "heavy_rain", 80: "slight_rain_showers", 81: "moderate_rain_showers", 82: "violent_rain_showers", 95: "thunderstorm"}.get(code, "")
