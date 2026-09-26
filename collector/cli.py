"""Command-line interface for collection and slot publishing."""
import argparse
import logging
from datetime import date

from . import storage
from .calendar_data import CALENDAR_FIELDS, calendar_rows, parse_date
from .config import DEFAULT_START_DATE, SLOT_LATE_AFTERNOON, SLOT_MORNING, calendarific_key, serpapi_key
from .daily_context import DAILY_CONTEXT_FIELDS, DAILY_CONTEXT_KEYS, build_daily_context_rows
from .holidays import HOLIDAY_FIELDS, holiday_rows
from .hourly_weather import historical_slot_rows
from .serpapi import SNAPSHOT_FIELDS, collect_snapshots
from .weather import WEATHER_FIELDS, ist_today, missing_weather_dates, weather_rows

logger = logging.getLogger(__name__)
_DATASETS = ("weather", "calendar", "holidays", "daily_context")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="collector")
    parser.add_argument("--start", type=parse_date, default=DEFAULT_START_DATE)
    parser.add_argument("--end", type=parse_date, default=None)
    parser.add_argument("--only", choices=_DATASETS, action="append")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--serpapi-label", choices=(SLOT_MORNING, SLOT_LATE_AFTERNOON))
    parser.add_argument("--historical-slots", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    today = ist_today()
    end = args.end or today
    if args.start > end:
        parser.error("--start must be on or before --end")
    datasets = set(args.only or _DATASETS)
    if args.historical_slots:
        _collect_historical_slots(args.start, end)
    if "calendar" in datasets:
        _collect_calendar(args.start, end, args.incremental)
    if "holidays" in datasets:
        _collect_holidays(args.start, end)
    if "weather" in datasets:
        _collect_weather(args.start, end, today, args.incremental)
    if args.serpapi_label:
        _collect_serpapi(args.serpapi_label, today)
    if "daily_context" in datasets:
        _collect_daily_context(args.start, end, today)
    return 0


def _collect_historical_slots(start, end):
    rows = historical_slot_rows(start, end)
    grouped = {}
    for row in rows:
        grouped.setdefault(row["Date"][:7], []).append(row)
    for month, values in grouped.items():
        year, month_number = (int(part) for part in month.split("-"))
        _upsert(values, "weather_snapshots.csv", ("City_Code", "Capture_Timestamp"), SNAPSHOT_FIELDS, "historical_slots", year, month_number)


def _collect_serpapi(label, day):
    rows = collect_snapshots(serpapi_key(), label, day)
    _upsert(rows, "weather_snapshots.csv", ("City_Code", "Capture_Timestamp"), SNAPSHOT_FIELDS, "serpapi", day.year, day.month)


def _collect_daily_context(start, end, today):
    months = set(storage.month_range(start, end))
    months.add((today.year, today.month))
    for year, month in sorted(months):
        rows = build_daily_context_rows(year, month, today)
        path = storage.published_month_path(date(year, month, 1))
        storage.write_rows(path, rows, DAILY_CONTEXT_FIELDS)
        logger.info("daily_context %04d-%02d: %d rows", year, month, len(rows))


def _collect_calendar(start, end, incremental):
    _upsert(calendar_rows(start, end), "calendar.csv", ("Date",), CALENDAR_FIELDS, "calendar")


def _collect_holidays(start, end):
    rows = [row for row in holiday_rows(start.year, end.year, calendarific_api_key=calendarific_key()) if start.isoformat() <= row["Date"] <= end.isoformat()]
    _upsert(rows, "holidays.csv", ("Date", "State_Region", "Holiday_Name"), HOLIDAY_FIELDS, "holiday")


def _collect_weather(start, end, today, incremental):
    if incremental:
        existing = _existing_rows("weather.csv", start, end)
        missing = missing_weather_dates(existing, start, end, today)
        if not missing:
            logger.info("weather: nothing missing in %s..%s", start, end)
            return
        start, end = min(missing), max(missing)
    _upsert(weather_rows(start, end, today=today), "weather.csv", ("City_Code", "Date"), WEATHER_FIELDS, "weather")


def _upsert(rows, name, keys, fields, kind, year=None, month=None):
    grouped = {}
    for row in rows:
        try:
            day = parse_date(row["Date"])
        except (KeyError, ValueError):
            storage.log_failure(kind, row.get("Date", ""), "malformed date")
            continue
        grouped.setdefault((day.year, day.month), []).append(row)
    if year is not None and month is not None:
        grouped = {(year, month): grouped.get((year, month), rows)}
    for (row_year, row_month), values in grouped.items():
        path = storage.runtime_month_path(date(row_year, row_month, 1), name)
        existing = storage.read_rows(path)
        index = {tuple(row.get(key, "") for key in keys): row for row in existing}
        for row in values:
            key = tuple(row.get(key, "") for key in keys)
            old = index.get(key)
            if old and old.get("Capture_Source") not in ("", "unavailable") and row.get("Capture_Source") in ("", "unavailable"):
                continue
            if old and old.get("Capture_Source") == "serpapi-google-weather" and row.get("Capture_Source") == "open-meteo-historical-hourly-backfill":
                continue
            index[key] = row
        storage.write_rows(path, sorted(index.values(), key=lambda row: tuple(row.get(key, "") for key in keys)), fields)


def _existing_rows(name, start, end):
    rows = []
    for year, month in storage.month_range(start, end):
        rows.extend(storage.read_rows(storage.runtime_month_path(date(year, month, 1), name)))
    return rows
