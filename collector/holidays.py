"""India holiday rows from python-holidays plus curated static entries."""
from datetime import date

import holidays
from holidays.constants import GOVERNMENT, PUBLIC

from .config import CITIES, HOLIDAYS_MAX_YEAR, HOLIDAYS_MIN_YEAR

HOLIDAY_FIELDS = ("Date", "Holiday_Name", "Holiday_Type", "State_Region", "Is_Holiday", "Source")

SOURCE_PYTHON_HOLIDAYS = "python-holidays"
SOURCE_CURATED = "curated-holidays"
NATIONAL = "National"

SUBDIVISIONS = tuple(dict.fromkeys(c.subdiv for c in CITIES))

_CATEGORIES = (PUBLIC, GOVERNMENT)

STATIC_HOLIDAYS = tuple(
    (date(2026, 4, 14), "Ambedkar Jayanti", "government holiday", subdiv)
    for subdiv in ("AP", "CH", "DL", "GJ", "KA", "KL", "MH", "MP", "RJ", "TS", "UP", "WB")
)


def check_year_support(start_year, end_year):
    if start_year < HOLIDAYS_MIN_YEAR or end_year > HOLIDAYS_MAX_YEAR:
        raise ValueError(
            f"python-holidays India support is {HOLIDAYS_MIN_YEAR}-{HOLIDAYS_MAX_YEAR}; "
            f"requested {start_year}-{end_year}"
        )


def holiday_rows(start_year, end_year):
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
    rows.extend(_static_holiday_rows(years, taken))
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


def _static_holiday_rows(years, taken):
    rows = []
    for day, name, category, subdiv in STATIC_HOLIDAYS:
        if day.year not in years:
            continue
        key = (day.isoformat(), subdiv)
        if key in taken:
            continue
        taken.add(key)
        rows.append(_row(day, name, category, subdiv, SOURCE_CURATED))
    return rows
