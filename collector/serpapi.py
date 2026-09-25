"""Optional SerpAPI current-weather snapshots parsed into CSV rows."""
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import CITIES, DATA_ROOT
from .http import HttpError, get_json

logger = logging.getLogger(__name__)
SERPAPI_URL = "https://serpapi.com/search.json"
SNAPSHOT_FIELDS = (
    "Capture_Timestamp", "Date", "City", "City_Code", "Capture_Label",
    "Temperature_C", "Weather_Condition", "Precipitation_Probability",
    "Humidity_Percent", "Wind_Speed", "Location", "Source", "Raw_JSON_Path",
)


def collect_snapshots(api_key, label):
    if not api_key:
        logger.info("serpapi: no key configured; skipping %s snapshot", label)
        return []
    captured = datetime.now(ZoneInfo("Asia/Kolkata"))
    rows = []
    for city in CITIES:
        context = f"serpapi weather {city.code} {label}"
        for attempt, query in enumerate((f"weather {city.name} India", f"weather in {city.name}", f"{city.name} weather"), 1):
            try:
                payload = get_json(
                    SERPAPI_URL,
                    params={"engine": "google", "q": query, "api_key": api_key, "gl": "in", "hl": "en", "device": "desktop", "no_cache": "true" if attempt > 1 else "false"},
                    context=f"{context} attempt {attempt}",
                )
                weather = _weather_result(payload)
                if not weather:
                    raise HttpError(f"{context}: weather_result missing")
                rows.append(_row(city, captured, label, weather))
                break
            except (HttpError, AttributeError, TypeError) as exc:
                logger.warning("%s attempt %d failed: %s", context, attempt, exc)
                if attempt == 3:
                    continue
                time.sleep(0.5)
    return rows


def _weather_result(payload):
    answer = payload.get("answer_box", {}) if isinstance(payload, dict) else {}
    candidates = answer if isinstance(answer, list) else [answer]
    candidates += payload.get("answer_box_list", []) if isinstance(payload, dict) else []
    for item in candidates:
        if isinstance(item, dict) and (item.get("type") == "weather_result" or (item.get("temperature") is not None and (item.get("weather") or item.get("location")))):
            return item
    return None


def _row(city, captured, label, weather):
    return {
        "Capture_Timestamp": captured.isoformat(timespec="seconds"),
        "Date": captured.date().isoformat(),
        "City": city.name,
        "City_Code": city.code,
        "Capture_Label": label,
        "Temperature_C": _temperature_c(weather.get("temperature"), weather.get("unit")),
        "Weather_Condition": weather.get("weather", ""),
        "Precipitation_Probability": _number(weather.get("precipitation")),
        "Humidity_Percent": _number(weather.get("humidity")),
        "Wind_Speed": weather.get("wind", ""),
        "Location": weather.get("location", ""),
        "Source": "serpapi-google-weather",
        "Raw_JSON_Path": "",
    }


def _number(value):
    if value is None:
        return ""
    return "".join(c for c in str(value) if c.isdigit() or c in ".-")


def _temperature_c(value, unit):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if str(unit).lower().startswith("fahrenheit"):
        return round((number - 32) * 5 / 9, 2)
    return number
