"""Monthly CSV storage with deduplication, validation, and failure logging."""
import csv
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_ROOT, FAILURE_LOG, VALID_CITY_CODES
from .calendar_data import parse_date

logger = logging.getLogger(__name__)


def month_dir(day):
    return DATA_ROOT / f"{day.year:04d}" / f"{day.month:02d}"


def month_path(day, name):
    return month_dir(day) / name


def month_range(start, end):
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        yield year, month
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1


def read_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_name, path)
    except BaseException:
        os.unlink(tmp_name)
        raise


def log_failure(kind, key, message):
    FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with FAILURE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp}\t{kind}\t{key}\t{message}\n")


def validate_weather_key(row):
    city = row.get("City_Code", "")
    day = row.get("Date", "")
    if city not in VALID_CITY_CODES:
        return f"invalid city code: {city!r}"
    try:
        parse_date(day)
    except ValueError:
        return f"malformed date: {day!r}"
    return None


def validate_calendar_key(row):
    try:
        parse_date(row.get("Date", ""))
    except ValueError:
        return f"malformed date: {row.get('Date', '')!r}"
    return None


def validate_holiday_key(row):
    try:
        parse_date(row.get("Date", ""))
    except ValueError:
        return f"malformed date: {row.get('Date', '')!r}"
    if not row.get("Holiday_Name"):
        return "empty holiday name"
    return None


def upsert_monthly(path, new_rows, key_fields, fieldnames, validator, kind):
    existing = read_rows(path)
    combined = list(existing)
    index = {tuple(r.get(k, "") for k in key_fields): i for i, r in enumerate(combined)}
    added = 0
    for row in new_rows:
        problem = validator(row)
        if problem:
            log_failure(kind, str({k: row.get(k) for k in key_fields}), problem)
            continue
        key = tuple(row.get(k, "") for k in key_fields)
        if key in index:
            combined[index[key]] = row
        else:
            index[key] = len(combined)
            combined.append(row)
            added += 1
    combined.sort(key=lambda r: tuple(r.get(k, "") for k in key_fields))
    write_rows(path, combined, fieldnames)
    return added, len(combined)
