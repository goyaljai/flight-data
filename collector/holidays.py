"""India holiday rows from python-holidays with optional Calendarific enrichment."""
import logging
from datetime import date

import holidays
from holidays.constants import GOVERNMENT, PUBLIC

from .config import (
    CALENDARIFIC_API_URL,
    CITIES,
    HOLIDAYS_MAX_YEAR,
    HOLIDAYS_MIN_YEAR,
)
from .http import HttpError, get_json

logger = logging.getLogger(__name__)

HOLIDAY_FIELDS = ("Date", "Holiday_Name", "Holiday_Type", "State_Region", "Is_Holiday", "Source")

SOURCE_PYTHON_HOLIDAYS = "python-holidays"
SOURCE_CALENDARIFIC = "calendarific"
NATIONAL = "National"

SUBDIVISIONS = tuple(dict.fromkeys(c.subdiv for c in CITIES))

_CATEGORIES = (PUBLIC, GOVERNMENT)


def check_year_support(start_year, end_year):
    if start_year < HOLIDAYS_MIN_YEAR or end_year > HOLIDAYS_MAX_YEAR:
        raise ValueError(
            f"python-holidays India support is {HOLIDAYS_MIN_YEAR}-{HOLIDAYS_MAX_YEAR}; "
            f"requested {start_year}-{end_year}"
        )


def holiday_rows(start_year, end_year, calendarific_api_key=""):
    check_year_support(start_year, end_year)
    years = list(range(start_year, end_year + 1))
    rows = []
    national = _collect(None, years)
    national_names = {day: {name for name, _ in entries} for day, entries in national.items()}
    for day, entries in national.items():
        for name, category in entries:
            rows.append(_row(day, name, category, NATIONAL, SOURCE_PYTHON_HOLIDAYS))
    for subdiv in SUBDIVISIONS:
        for day, entries in _collect(subdiv, years).items():
            for name, category in entries:
                if name in national_names.get(day, set()):
                    continue
                rows.append(_row(day, name, category, subdiv, SOURCE_PYTHON_HOLIDAYS))
    taken = {(r["Date"], r["State_Region"]) for r in rows}
    rows.extend(_calendarific_rows(years, calendarific_api_key, taken))
    return rows


def _collect(subdiv, years):
    merged = {}
    for category in _CATEGORIES:
        calendar = holidays.India(subdiv=subdiv, years=years, categories=(category,))
        for day, name in sorted(calendar.items()):
            bucket = merged.setdefault(day, [])
            seen = {n for n, _ in bucket}
            for component in str(name).split("; "):
                if component not in seen:
                    seen.add(component)
                    bucket.append((component, category))
    return merged


def _row(day, name, category, region, source):
    return {
        "Date": day.isoformat(),
        "Holiday_Name": name,
        "Holiday_Type": category,
        "State_Region": region,
        "Is_Holiday": "true",
        "Source": source,
    }


_CALENDARIFIC_LOCATION_OVERRIDES = {"TS": "in-tg"}


def _calendarific_location(subdiv):
    return _CALENDARIFIC_LOCATION_OVERRIDES.get(subdiv, f"in-{subdiv.lower()}")


def _calendarific_rows(years, api_key, taken):
    if not api_key:
        return []
    rows = []
    for year in years:
        for subdiv in SUBDIVISIONS:
            context = f"calendarific {year} {subdiv}"
            try:
                payload = get_json(
                    CALENDARIFIC_API_URL,
                    params={
                        "api_key": api_key,
                        "country": "IN",
                        "year": year,
                        "location": _calendarific_location(subdiv),
                        "type": "national,local",
                    },
                    context=context,
                )
            except HttpError as exc:
                logger.warning("%s: enrichment skipped: %s", context, exc)
                continue
            for item in payload.get("response", {}).get("holidays", []):
                iso = item.get("date", {}).get("iso", "")
                region = NATIONAL if item.get("locations") == "All" else subdiv
                key = (iso, region)
                if not iso or key in taken:
                    continue
                try:
                    day = date.fromisoformat(iso)
                except ValueError:
                    logger.warning("%s: skipping malformed date %r", context, iso)
                    continue
                taken.add(key)
                rows.append(
                    _row(
                        day,
                        item.get("name", ""),
                        str(item.get("primary_type", "")).lower(),
                        region,
                        SOURCE_CALENDARIFIC,
                    )
                )
    return rows
