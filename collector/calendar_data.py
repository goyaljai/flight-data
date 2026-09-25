"""Deterministic calendar rows: Date, Day_of_Week, Is_Weekend."""
from datetime import date, timedelta

CALENDAR_FIELDS = ("Date", "Day_of_Week", "Is_Weekend")


def date_range(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def calendar_rows(start, end):
    rows = []
    for day in date_range(start, end):
        rows.append(
            {
                "Date": day.isoformat(),
                "Day_of_Week": day.strftime("%A"),
                "Is_Weekend": "true" if day.weekday() >= 5 else "false",
            }
        )
    return rows


def parse_date(value):
    return date.fromisoformat(value)
