"""Command-line interface for the daily context collector."""
import argparse
import logging
from datetime import date, timedelta

from . import storage
from .calendar_data import CALENDAR_FIELDS, calendar_rows, parse_date
from .config import DEFAULT_START_DATE, calendarific_key
from .daily_context import DAILY_CONTEXT_FIELDS, DAILY_CONTEXT_KEYS, build_daily_context_rows
from .holidays import HOLIDAY_FIELDS, holiday_rows
from .serpapi import SNAPSHOT_FIELDS, collect_snapshots
from .weather import WEATHER_FIELDS, ist_today, missing_weather_dates, weather_rows

logger = logging.getLogger(__name__)
_WEATHER_KEYS = ("City_Code", "Date")
_CALENDAR_KEYS = ("Date",)
_HOLIDAY_KEYS = ("Date", "State_Region", "Holiday_Name")
_DATASETS = ("weather", "calendar", "holidays", "daily_context")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="collector", description="Collect daily India context data.")
    parser.add_argument("--start", type=parse_date, default=DEFAULT_START_DATE)
    parser.add_argument("--end", type=parse_date, default=None)
    parser.add_argument("--only", choices=_DATASETS, action="append")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--serpapi-label", choices=("morning", "midday"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    today = ist_today()
    end = args.end or today
    if args.start > end:
        parser.error("--start must be on or before --end")
    datasets = set(args.only or _DATASETS)
    try:
        if "calendar" in datasets:
            _collect_calendar(args.start, end, args.incremental)
        if "holidays" in datasets:
            _collect_holidays(args.start, end)
        if "weather" in datasets:
            _collect_weather(args.start, end, today, args.incremental)
        if args.serpapi_label:
            _collect_serpapi(args.serpapi_label)
    finally:
        if "daily_context" in datasets:
            _collect_daily_context(args.start, end, today if args.serpapi_label else None)
    return 0


def _collect_daily_context(start, end, today=None):
    months = set(storage.month_range(start, end))
    if today is not None:
        months.add((today.year, today.month))
    for year, month in sorted(months):
        rows = build_daily_context_rows(year, month, end)
        path = storage.month_path(date(year, month, 1), "daily_context.csv")
        added, total = storage.upsert_monthly(path, rows, DAILY_CONTEXT_KEYS, DAILY_CONTEXT_FIELDS, storage.validate_weather_key, "daily_context")
        logger.info("daily_context %04d-%02d: +%d rows (total %d)", year, month, added, total)


def _collect_serpapi(label):
    from .config import serpapi_key
    try:
        rows = collect_snapshots(serpapi_key(), label)
    except Exception as exc:
        storage.log_failure("serpapi", label, str(exc))
        raise SystemExit("serpapi: snapshot collection failed; see failures.log")
    if not rows:
        return
    day = parse_date(rows[0]["Date"])
    path = storage.month_path(day, "weather_snapshots.csv")
    added, total = storage.upsert_snapshot_rows(path, rows, ("Capture_Timestamp", "City_Code", "Capture_Label"), SNAPSHOT_FIELDS)
    logger.info("serpapi %s: +%d rows (total %d)", label, added, total)


def _collect_calendar(start, end, incremental):
    if incremental and not _any_missing(_existing_dates("calendar.csv", start, end), start, end):
        logger.info("calendar: already complete for %s..%s", start, end)
        return
    _upsert(calendar_rows(start, end), "calendar.csv", _CALENDAR_KEYS, CALENDAR_FIELDS, storage.validate_calendar_key, "calendar")


def _collect_holidays(start, end):
    try:
        rows = holiday_rows(start.year, end.year, calendarific_api_key=calendarific_key())
    except ValueError as exc:
        raise SystemExit(f"holidays: {exc}")
    rows = [r for r in rows if start.isoformat() <= r["Date"] <= end.isoformat()]
    _upsert(rows, "holidays.csv", _HOLIDAY_KEYS, HOLIDAY_FIELDS, storage.validate_holiday_key, "holiday", touch_all_months=(start, end))


def _collect_weather(start, end, today, incremental):
    if incremental:
        missing = missing_weather_dates(_existing_rows("weather.csv", start, end), start, end, today)
        if not missing:
            logger.info("weather: nothing missing in %s..%s", start, end)
            return
        start, end = min(missing), max(missing)
    _upsert(weather_rows(start, end, today=today), "weather.csv", _WEATHER_KEYS, WEATHER_FIELDS, storage.validate_weather_key, "weather")


def _upsert(rows, name, key_fields, fieldnames, validator, kind, touch_all_months=None):
    grouped = {}
    for row in rows:
        try:
            day = parse_date(row.get("Date", ""))
        except ValueError:
            storage.log_failure(kind, row.get("Date", ""), "malformed date")
            continue
        grouped.setdefault((day.year, day.month), []).append(row)
    if touch_all_months:
        for year, month in storage.month_range(*touch_all_months):
            grouped.setdefault((year, month), [])
    for (year, month), group in sorted(grouped.items()):
        path = storage.month_path(date(year, month, 1), name)
        added, total = storage.upsert_monthly(path, group, key_fields, fieldnames, validator, kind)
        logger.info("%s %04d-%02d: +%d rows (total %d)", kind, year, month, added, total)


def _existing_rows(name, start, end):
    rows = []
    for year, month in storage.month_range(start, end):
        rows.extend(storage.read_rows(storage.month_path(date(year, month, 1), name)))
    return rows


def _existing_dates(name, start, end):
    return {r.get("Date", "") for r in _existing_rows(name, start, end)}


def _any_missing(present, start, end):
    current = start
    while current <= end:
        if current.isoformat() not in present:
            return True
        current += timedelta(days=1)
    return False
