"""Daily national ATF price (INR per kilolitre) rows from SerpAPI search snippets."""
import logging
import re
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .http import HttpError, get_json
from .serpapi import SERPAPI_URL

logger = logging.getLogger(__name__)

ATF_FIELDS = ("Date", "ATF_Price_INR_KL", "ATF_Region", "ATF_Source", "ATF_Note", "Captured_At")
ATF_ANCHOR = "National"
ATF_SOURCE = "serpapi-atf"
_RETRY_ATTEMPT_WINDOW_DAYS = 7
_MIN_PRICE, _MAX_PRICE = 30000.0, 200000.0
_PRICE_PATTERN = re.compile(r"([\d][\d,]*(?:\.\d+)?)\s*(?:per\s+kilolitre|per\s+kl|/kilolitre|/kl)\b", re.IGNORECASE)


def atf_rows(start, end, api_key, existing=()):
    if not api_key:
        logger.warning("atf: no SerpAPI key; skipping")
        return []
    cutoff = (datetime.now(ZoneInfo("Asia/Kolkata")).date() - timedelta(days=_RETRY_ATTEMPT_WINDOW_DAYS)).isoformat()
    settled = set()
    for row in existing:
        if row.get("ATF_Price_INR_KL", "").strip() or row.get("Captured_At", "")[:10] >= cutoff:
            settled.add(row.get("Date", ""))
    rows = []
    day = start
    while day <= end:
        iso = day.isoformat()
        if iso not in settled:
            price, note = _fetch_price(day, api_key)
            rows.append(_row(day, price, note))
            if day < end:
                time.sleep(1.0)
        day = date.fromordinal(day.toordinal() + 1)
    return rows


def _fetch_price(day, api_key):
    query = f"India ATF jet fuel price {day.strftime('%B')} {day.day}, {day.year} rupees per kilolitre"
    try:
        payload = get_json(
            SERPAPI_URL,
            {"engine": "google", "q": query, "api_key": api_key, "gl": "in", "hl": "en", "device": "desktop", "no_cache": "false"},
            context=f"SerpAPI atf {day.isoformat()}",
        )
    except HttpError as exc:
        logger.warning("atf %s: %s", day.isoformat(), exc)
        return "", ""
    for item in payload.get("organic_results", []) if isinstance(payload, dict) else []:
        text = " ".join(str(item.get(key, "")) for key in ("title", "snippet"))
        match = _PRICE_PATTERN.search(text)
        if match:
            try:
                price = float(match.group(1).replace(",", ""))
            except ValueError:
                continue
            if _MIN_PRICE <= price <= _MAX_PRICE:
                return f"{price:,.0f}", (item.get("title", "") or "")[:100]
    logger.warning("atf %s: no price found in search results", day.isoformat())
    return "", ""


def _row(day, price, note):
    return {
        "Date": day.isoformat(),
        "ATF_Price_INR_KL": price,
        "ATF_Region": ATF_ANCHOR,
        "ATF_Source": ATF_SOURCE,
        "ATF_Note": note,
        "Captured_At": datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds"),
    }