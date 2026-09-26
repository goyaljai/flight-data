"""Build the published two-slot-per-city/day dataset."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from .config import CITIES, CITY_BY_CODE, SLOT_HOURS, SLOT_LATE_AFTERNOON, SLOT_MORNING
from .storage import published_month_path, read_rows, runtime_month_path, write_rows

IST = ZoneInfo("Asia/Kolkata")
DAILY_CONTEXT_KEYS = ("City_Code", "Capture_Timestamp")
DAILY_CONTEXT_FIELDS = (
    "Date", "City", "City_Code", "Capture_Timestamp", "Capture_Label", "Captured_At",
    "Latitude", "Longitude", "Day_of_Week", "Is_Weekend",
    "Temperature_Max_C", "Temperature_Min_C", "Temperature_Mean_C", "Apparent_Temperature_Max_C", "Apparent_Temperature_Min_C",
    "Precipitation_Sum_MM", "Rain_Sum_MM", "Precipitation_Hours", "Wind_Speed_Max_KMH", "Wind_Gusts_Max_KMH", "Wind_Direction_Dominant_Deg", "Weather_Code", "Weather_Source",
    "Holiday_Names", "Holiday_Types", "Holiday_Regions", "Holiday_Sources", "Is_Holiday",
    "Slot_Temperature_C", "Slot_Humidity_Percent", "Slot_Precipitation_Probability_Percent", "Slot_Wind_Speed_KMH", "Slot_Weather_Code", "Slot_Condition_Text", "Capture_Source",
)
SLOT_FIELDS = ("Temperature_C", "Humidity_Percent", "Precipitation_Probability", "Wind_Speed", "Weather_Code", "Weather_Condition", "Capture_Source", "Captured_At")


def scheduled_timestamp(day, label):
    return datetime.combine(day, time(SLOT_HOURS[label], 0), IST).isoformat(timespec="seconds")


def build_daily_context_rows(year, month, through=None):
    first = date(year, month, 1)
    last = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    weather = {(r.get("City_Code"), r.get("Date")): r for r in read_rows(runtime_month_path(first, "weather.csv"))}
    calendar = {r.get("Date"): r for r in read_rows(runtime_month_path(first, "calendar.csv"))}
    holidays = {}
    for row in read_rows(runtime_month_path(first, "holidays.csv")):
        holidays.setdefault(row.get("Date"), []).append(row)
    snapshots = {}
    for row in read_rows(runtime_month_path(first, "weather_snapshots.csv")):
        snapshots[(row.get("City_Code"), row.get("Date"), row.get("Capture_Label"))] = row
    final_day = min(last.fromordinal(last.toordinal() - 1), through) if through else last.fromordinal(last.toordinal() - 1)
    rows = []
    day = first
    while day <= final_day:
        day_text = day.isoformat()
        cal = calendar.get(day_text, {})
        for city in CITIES:
            source = weather.get((city.code, day_text), {})
            applicable = [row for row in holidays.get(day_text, []) if row.get("State_Region") in ("National", city.subdiv)]
            applicable.sort(key=lambda row: (row.get("State_Region", ""), row.get("Holiday_Name", "")))
            for label in (SLOT_MORNING, SLOT_LATE_AFTERNOON):
                snapshot = snapshots.get((city.code, day_text, label), {})
                row = {field: "" for field in DAILY_CONTEXT_FIELDS}
                row.update({field: source.get(field, "") for field in ("Date", "City", "City_Code", "Latitude", "Longitude", "Temperature_Max_C", "Temperature_Min_C", "Temperature_Mean_C", "Apparent_Temperature_Max_C", "Apparent_Temperature_Min_C", "Precipitation_Sum_MM", "Rain_Sum_MM", "Precipitation_Hours", "Wind_Speed_Max_KMH", "Wind_Gusts_Max_KMH", "Wind_Direction_Dominant_Deg", "Weather_Code", "Weather_Source")})
                row.update({"Date": day_text, "City": city.name, "City_Code": city.code, "Capture_Timestamp": scheduled_timestamp(day, label), "Capture_Label": label, "Latitude": city.latitude, "Longitude": city.longitude, "Day_of_Week": cal.get("Day_of_Week", day.strftime("%A")), "Is_Weekend": cal.get("Is_Weekend", "true" if day.weekday() >= 5 else "false")})
                row.update({"Holiday_Names": "; ".join(r.get("Holiday_Name", "") for r in applicable), "Holiday_Types": "; ".join(r.get("Holiday_Type", "") for r in applicable), "Holiday_Regions": "; ".join(r.get("State_Region", "") for r in applicable), "Holiday_Sources": "; ".join(r.get("Source", "") for r in applicable), "Is_Holiday": "true" if applicable else "false"})
                row.update({"Captured_At": snapshot.get("Captured_At", ""), "Slot_Temperature_C": snapshot.get("Temperature_C", ""), "Slot_Humidity_Percent": snapshot.get("Humidity_Percent", ""), "Slot_Precipitation_Probability_Percent": snapshot.get("Precipitation_Probability", ""), "Slot_Wind_Speed_KMH": snapshot.get("Wind_Speed", ""), "Slot_Weather_Code": snapshot.get("Weather_Code", ""), "Slot_Condition_Text": snapshot.get("Weather_Condition", ""), "Capture_Source": snapshot.get("Capture_Source", "unavailable") if snapshot else "unavailable"})
                rows.append(row)
        day = date.fromordinal(day.toordinal() + 1)
    return rows


def write_month(year, month, through=None):
    rows = build_daily_context_rows(year, month, through)
    write_rows(published_month_path(date(year, month, 1)), rows, DAILY_CONTEXT_FIELDS)
    return len(rows)
