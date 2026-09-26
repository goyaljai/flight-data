"""Configuration and city metadata for the daily context collector."""
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_ROOT = Path(os.environ.get("COLLECTOR_RUNTIME_ROOT", str(PROJECT_ROOT / ".runtime")))
RUNTIME_DATA_ROOT = RUNTIME_ROOT / "data"
PUBLISHED_DATA_ROOT = Path(os.environ.get("COLLECTOR_PUBLISHED_ROOT", str(PROJECT_ROOT / "data")))
DATA_ROOT = RUNTIME_DATA_ROOT
FAILURE_LOG = RUNTIME_ROOT / "failures.log"
DEFAULT_START_DATE = date(2026, 6, 1)
OPEN_METEO_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_HISTORICAL_FORECAST_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
HISTORICAL_FORECAST_MIN_DATE = date(2022, 1, 1)
CALENDARIFIC_API_URL = "https://calendarific.com/api/v2/holidays"
HOLIDAYS_MIN_YEAR = 2001
HOLIDAYS_MAX_YEAR = 2035
HTTP_TIMEOUT_SECONDS = 60
HTTP_MAX_RETRIES = 4
HTTP_BACKOFF_BASE_SECONDS = 2.0
SLOT_MORNING = "morning"
SLOT_LATE_AFTERNOON = "late_afternoon"
SLOT_HOURS = {SLOT_MORNING: 9, SLOT_LATE_AFTERNOON: 17}
VALID_CITY_CODES = ("BOM", "DEL", "BLR", "HYD", "MAA", "CCU", "PNQ", "AMD", "STV", "VTZ", "JAI", "COK", "IXC", "IDR", "LKO")

@dataclass(frozen=True)
class City:
    code: str
    name: str
    latitude: float
    longitude: float
    subdiv: str
    region: str

CITIES = (
    City("BOM", "Mumbai", 19.0760, 72.8777, "MH", "Maharashtra"),
    City("DEL", "Delhi", 28.7041, 77.1025, "DL", "Delhi"),
    City("BLR", "Bengaluru", 12.9716, 77.5946, "KA", "Karnataka"),
    City("HYD", "Hyderabad", 17.3850, 78.4867, "TS", "Telangana"),
    City("MAA", "Chennai", 13.0827, 80.2707, "TN", "Tamil Nadu"),
    City("CCU", "Kolkata", 22.5726, 88.3639, "WB", "West Bengal"),
    City("PNQ", "Pune", 18.5204, 73.8567, "MH", "Maharashtra"),
    City("AMD", "Ahmedabad", 23.0225, 72.5714, "GJ", "Gujarat"),
    City("STV", "Surat", 21.1702, 72.8311, "GJ", "Gujarat"),
    City("VTZ", "Visakhapatnam", 17.6868, 83.2185, "AP", "Andhra Pradesh"),
    City("JAI", "Jaipur", 26.9124, 75.7873, "RJ", "Rajasthan"),
    City("COK", "Kochi", 9.9312, 76.2673, "KL", "Kerala"),
    City("IXC", "Chandigarh", 30.7333, 76.7794, "CH", "Chandigarh"),
    City("IDR", "Indore", 22.7196, 75.8577, "MP", "Madhya Pradesh"),
    City("LKO", "Lucknow", 26.8467, 80.9462, "UP", "Uttar Pradesh"),
)
CITY_BY_CODE = {city.code: city for city in CITIES}

def serpapi_key():
    return os.environ.get("SERPAPI_API_KEY", "").strip()

def calendarific_key():
    return os.environ.get("CALENDARIFIC_API_KEY", "").strip()
