"""Build one joined city/date CSV row from monthly source data."""
from datetime import date

from .config import CITIES
from .storage import month_path, read_rows, write_rows

DAILY_CONTEXT_KEYS = ("City_Code", "Date")
DAILY_CONTEXT_FIELDS = (
    "Date", "City", "City_Code", "Latitude", "Longitude", "Day_of_Week", "Is_Weekend",
    "Temperature_Max_C", "Temperature_Min_C", "Temperature_Mean_C", "Apparent_Temperature_Max_C", "Apparent_Temperature_Min_C",
    "Precipitation_Sum_MM", "Rain_Sum_MM", "Precipitation_Hours", "Wind_Speed_Max_KMH", "Wind_Gusts_Max_KMH",
    "Wind_Direction_Dominant_Deg", "Weather_Code", "Weather_Source",
    "Holiday_Names", "Holiday_Types", "Holiday_Regions", "Holiday_Sources", "Is_Holiday",
    "Morning_Capture_Timestamp", "Morning_Temperature_C", "Morning_Weather_Condition", "Morning_Precipitation_Probability", "Morning_Humidity_Percent", "Morning_Wind_Speed", "Morning_Location",
    "Midday_Capture_Timestamp", "Midday_Temperature_C", "Midday_Weather_Condition", "Midday_Precipitation_Probability", "Midday_Humidity_Percent", "Midday_Wind_Speed", "Midday_Location",
)


def build_daily_context_rows(year, month, holiday_horizon=None):
    first = date(year, month, 1)
    last = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    weather = read_rows(month_path(first, "weather.csv"))
    calendar = {r["Date"]: r for r in read_rows(month_path(first, "calendar.csv"))}
    holidays = {}
    for row in read_rows(month_path(first, "holidays.csv")):
        holidays.setdefault(row["Date"], []).append(row)
    snapshots = {}
    for row in read_rows(month_path(first, "weather_snapshots.csv")):
        key = (row["City_Code"], row["Date"], row["Capture_Label"])
        if key not in snapshots or row["Capture_Timestamp"] > snapshots[key]["Capture_Timestamp"]:
            snapshots[key] = row
    rows = []
    for source in weather:
        day, city_code = source["Date"], source["City_Code"]
        if not first.isoformat() <= day < last.isoformat():
            continue
        city = next((c for c in CITIES if c.code == city_code), None)
        region = city.subdiv if city else ""
        applicable = [r for r in holidays.get(day, []) if r.get("State_Region") in ("National", region)]
        applicable.sort(key=lambda r: (r.get("State_Region", ""), r.get("Holiday_Name", "")))
        row = {field: "" for field in DAILY_CONTEXT_FIELDS}
        for field in DAILY_CONTEXT_FIELDS[:7] + DAILY_CONTEXT_FIELDS[7:20]:
            row[field] = source.get(field, "")
        cal = calendar.get(day, {})
        row["Day_of_Week"], row["Is_Weekend"] = cal.get("Day_of_Week", ""), cal.get("Is_Weekend", "")
        row["Holiday_Names"] = "; ".join(r.get("Holiday_Name", "") for r in applicable)
        row["Holiday_Types"] = "; ".join(r.get("Holiday_Type", "") for r in applicable)
        row["Holiday_Regions"] = "; ".join(r.get("State_Region", "") for r in applicable)
        row["Holiday_Sources"] = "; ".join(r.get("Source", "") for r in applicable)
        row["Is_Holiday"] = "true" if applicable else "false"
        for label, prefix in (("morning", "Morning_"), ("midday", "Midday_")):
            snapshot = snapshots.get((city_code, day, label), {})
            for field in ("Capture_Timestamp", "Temperature_C", "Weather_Condition", "Precipitation_Probability", "Humidity_Percent", "Wind_Speed", "Location"):
                row[prefix + field] = snapshot.get(field, "")
        rows.append(row)
    return sorted(rows, key=lambda r: (r["Date"], r["City_Code"]))


def write_month(year, month):
    rows = build_daily_context_rows(year, month)
    write_rows(month_path(date(year, month, 1), "daily_context.csv"), rows, DAILY_CONTEXT_FIELDS)
    return len(rows)


def build_month(year, month):
    return build_daily_context_rows(year, month)
