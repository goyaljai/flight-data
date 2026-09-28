"""Daily ATF proxy price (Mumbai normal petrol, INR per litre) from mypetrolprice.com."""
import logging
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .config import FUEL_PRICE_URL
from .http import HttpError, get_text

logger = logging.getLogger(__name__)

ATF_FIELDS = ("Date", "ATF_Proxy_Price_INR_Per_Litre", "ATF_Region", "ATF_Source", "ATF_Note", "Captured_At")
ATF_ANCHOR = "Mumbai"
ATF_SOURCE = "mypetrolprice-mumbai-petrol"
_RETRY_ATTEMPT_WINDOW_DAYS = 7
_MIN_PRICE, _MAX_PRICE = 30.0, 400.0
_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
_PRICE_PATTERN = re.compile(r'<div class="fnt27">\s*(?:&#8377;|&#x20B9;|₹|Rs\.?)\s*([\d.]+)')


def atf_rows(start, end, existing=()):
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    cutoff = (today - timedelta(days=_RETRY_ATTEMPT_WINDOW_DAYS)).isoformat()
    settled = set()
    for row in existing:
        if row.get("ATF_Proxy_Price_INR_Per_Litre", "").strip() or row.get("Captured_At", "")[:10] >= cutoff:
            settled.add(row.get("Date", ""))
    rows = []
    day = start
    while day <= end:
        if day not in settled and day == today:
            price, note = fetch_mumbai_petrol_price()
            rows.append(_row(day, price, note))
        day = date.fromordinal(day.toordinal() + 1)
    return rows


def fetch_mumbai_petrol_price():
    try:
        text = get_text(FUEL_PRICE_URL, headers={"User-Agent": _USER_AGENT}, context="mypetrolprice")
    except HttpError as exc:
        logger.warning("fuel price: %s", exc)
        return "", ""
    for match in _PRICE_PATTERN.finditer(text):
        try:
            value = float(match.group(1))
        except ValueError:
            continue
        if _MIN_PRICE <= value <= _MAX_PRICE:
            return match.group(1), ATF_SOURCE
    logger.warning("fuel price: no price found on %s", FUEL_PRICE_URL)
    return "", ""


def _row(day, price, note):
    return {
        "Date": day.isoformat(),
        "ATF_Proxy_Price_INR_Per_Litre": price,
        "ATF_Region": ATF_ANCHOR,
        "ATF_Source": ATF_SOURCE,
        "ATF_Note": note,
        "Captured_At": datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds"),
    }