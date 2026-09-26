"""SerpAPI live slot observations."""
import logging
import time
from datetime import datetime, time as clock_time
from zoneinfo import ZoneInfo

from .config import CITIES, SLOT_HOURS, SLOT_LATE_AFTERNOON, SLOT_MORNING
from .http import HttpError, get_json

logger = logging.getLogger(__name__)
SERPAPI_URL = "https://serpapi.com/search.json"
SNAPSHOT_FIELDS = ("Date", "City", "City_Code", "Capture_Timestamp", "Capture_Label", "Captured_At", "Temperature_C", "Humidity_Percent", "Precipitation_Probability", "Wind_Speed", "Weather_Code", "Weather_Condition", "Capture_Source")


def collect_snapshots(api_key, label, day=None):
    if not api_key:
        return []
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    day = day or now.date()
    scheduled = datetime.combine(day, clock_time(SLOT_HOURS[label], 0), ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
    rows = []
    for city in CITIES:
        result = None
        for attempt, query in enumerate((f"weather {city.name} India", f"weather in {city.name}", f"{city.name} weather"), 1):
            try:
                payload = get_json(SERPAPI_URL, {"engine": "google", "q": query, "api_key": api_key, "gl": "in", "hl": "en", "device": "desktop", "no_cache": "true" if attempt > 1 else "false"}, context=f"SerpAPI {city.code} {label} attempt {attempt}")
                result = _weather_result(payload)
                if result:
                    break
                raise HttpError("weather result missing")
            except (HttpError, TypeError, AttributeError) as exc:
                logger.warning("SerpAPI %s %s attempt %d failed: %s", city.code, label, attempt, exc)
                if attempt < 3:
                    time.sleep(0.5)
        rows.append(_row(city, day, label, scheduled, now, result))
    return rows


def _row(city, day, label, scheduled, captured, weather):
    return {"Date": day.isoformat(), "City": city.name, "City_Code": city.code, "Capture_Timestamp": scheduled, "Capture_Label": label, "Captured_At": captured.isoformat(timespec="seconds"), "Temperature_C": _number(weather.get("temperature")) if weather else "", "Humidity_Percent": _number(weather.get("humidity")) if weather else "", "Precipitation_Probability": _number(weather.get("precipitation")) if weather else "", "Wind_Speed": _number(weather.get("wind")) if weather else "", "Weather_Code": "", "Weather_Condition": weather.get("weather", "") if weather else "", "Capture_Source": "serpapi-google-weather" if weather else "unavailable"}


def _weather_result(payload):
    answer = payload.get("answer_box", {}) if isinstance(payload, dict) else {}
    candidates = answer if isinstance(answer, list) else [answer]
    candidates += payload.get("answer_box_list", []) if isinstance(payload, dict) else []
    for item in candidates:
        if isinstance(item, dict) and (item.get("type") == "weather_result" or (item.get("temperature") is not None and (item.get("weather") or item.get("location")))):
            return item
    return None


def _number(value):
    if value is None:
        return ""
    text = "".join(char for char in str(value) if char.isdigit() or char in ".-")
    return float(text) if text else ""
