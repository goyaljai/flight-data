"""Curated non-holiday mega-event rows (e.g., FIFA World Cup 2026) from config/events.json."""
import json
from datetime import date, timedelta

from .config import PROJECT_ROOT

EVENT_FIELDS = ("Date", "Event_Name", "Event_Region", "Event_Source")
EVENT_REGION = "National"
EVENT_SOURCE = "curated-events"
_EVENTS_FILE = PROJECT_ROOT / "config" / "events.json"


def event_rows(start_year, end_year):
    with _EVENTS_FILE.open(encoding="utf-8") as handle:
        events = json.load(handle).get("events", [])
    rows = []
    for event in events:
        start = date.fromisoformat(event["start"])
        end = date.fromisoformat(event["end"])
        if end.year < start_year or start.year > end_year:
            continue
        day = max(start, date(start_year, 1, 1))
        last = min(end, date(end_year, 12, 31))
        while day <= last:
            rows.append(
                {
                    "Date": day.isoformat(),
                    "Event_Name": event["key"],
                    "Event_Region": EVENT_REGION,
                    "Event_Source": EVENT_SOURCE,
                }
            )
            day += timedelta(days=1)
    return rows