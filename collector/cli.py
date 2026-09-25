"""Command-line interface for the daily context collector."""
import argparse
import logging
from datetime import date, timedelta

from . import storage
from .calendar_data import CALENDAR_FIELDS, calendar_rows, parse_date
from .config import DEFAULT_START_DATE, calendarific_key
from .holidays import HOLIDAY_FIELDS, holiday_rows
from .weather import WEATHER_FIELDS, ist_today, missing_weather_dates, weather_rows

logger = logging.getLogger(__name__)

_WEATHER_KEYS = ("City_Code", "Date")
_CALENDAR_KEYS = ("Date",)
_HOLIDAY_KEYS = ("Date", "State_Region", "Holiday_Name")

_DATASETS = ("weather", "calendar", "holidays")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="collector",
        description="Collect daily India weather, calendar, and holiday context into monthly CSVs.",
    )
    parser.add_argument("--start", type=parse_date, default=DEFAULT_START_DATE,
                        help="first date YYYY-MM-DD (default: %(default)s)")
    parser.add_argument("--end", type=parse_date, default=None,
                        help="last date YYYY-MM-DD (default: today in Asia/Kolkata)")
    parser.add_argument("--only", choices=_DATASETS, action="append",
                        help="collect only the named dataset(s); repeatable")
    parser.add_argument("--incremental", action="store_true",
                        help="skip work where existing CSVs already cover the range")
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    today = ist_today()
    end = args.end or today
    if args.start > end:
        parser.error("--start must be on or before --end")

    datasets = set(args.only or _DATASETS)
    if "calendar" in datasets:
        _collect_calendar(args.start, end, args.incremental)
    if "holidays" in datasets:
        _collect_holidays(args.start, end)
    if "weather" in datasets:
        _collect_weather(args.start, end, today, args.incremental)
    return 0


def _collect_calendar(start, end, incremental):
    if incremental and not _any_missing(_existing_dates("calendar.csv", start, end), start, end):
        logger.info("calendar: already complete for %s..%s", start, end)
        return
    rows = calendar_rows(start, end)
    _upsert(rows, "calendar.csv", _CALENDAR_KEYS, CALENDAR_FIELDS,
            storage.validate_calendar_key, "calendar")


def _collect_holidays(start, end):
    try:
        rows = holiday_rows(start.year, end.year, calendarific_api_key=calendarific_key())
    except ValueError as exc:
        raise SystemExit(f"holidays: {exc}")
    rows = [r for r in rows if start.isoformat() <= r["Date"] <= end.isoformat()]
    _upsert(rows, "holidays.csv", _HOLIDAY_KEYS, HOLIDAY_FIELDS,
            storage.validate_holiday_key, "holiday", touch_all_months=(start, end))


def _collect_weather(start, end, today, incremental):
    if incremental:
        existing = _existing_rows("weather.csv", start, end)
        missing = missing_weather_dates(existing, start, end, today)
        if not missing:
            logger.info("weather: nothing missing in %s..%s", start, end)
            return
        start, end = min(missing), max(missing)
        logger.info("weather: refetching %s..%s (%d missing dates)", start, end, len(missing))
    rows = weather_rows(start, end, today=today)
    _upsert(rows, "weather.csv", _WEATHER_KEYS, WEATHER_FIELDS,
            storage.validate_weather_key, "weather")


def _upsert(rows, name, key_fields, fieldnames, validator, kind, touch_all_months=None):
    grouped = {}
    for row in rows:
        try:
            day = parse_date(row.get("Date", ""))
        except ValueError:
            storage.log_failure(kind, row.get("Date", ""), "malformed date")
            continue
        grouped.setdefault((day.year, day.month), []).append(row)
    if touch_all_months is not None:
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
