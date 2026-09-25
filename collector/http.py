"""HTTP helper with retries, backoff, and transient-failure handling."""
import logging
import time

import requests

from .config import (
    HTTP_BACKOFF_BASE_SECONDS,
    HTTP_MAX_RETRIES,
    HTTP_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class HttpError(Exception):
    pass


def get_json(url, params, *, context="request"):
    last_error = None
    for attempt in range(1, HTTP_MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=HTTP_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            last_error = f"{context}: network error: {exc}"
            logger.warning("%s (attempt %d/%d)", last_error, attempt, HTTP_MAX_RETRIES)
            _sleep_backoff(attempt)
            continue
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as exc:
                raise HttpError(f"{context}: invalid JSON response: {exc}") from exc
        if response.status_code in _RETRYABLE_STATUSES:
            retry_after = response.headers.get("Retry-After")
            last_error = f"{context}: HTTP {response.status_code}"
            logger.warning("%s (attempt %d/%d)", last_error, attempt, HTTP_MAX_RETRIES)
            _sleep_backoff(attempt, retry_after)
            continue
        raise HttpError(f"{context}: HTTP {response.status_code}: {response.text[:300]}")
    raise HttpError(f"{last_error} (exhausted {HTTP_MAX_RETRIES} attempts)")


def _sleep_backoff(attempt, retry_after=None):
    if retry_after is not None:
        try:
            delay = float(retry_after)
        except ValueError:
            delay = HTTP_BACKOFF_BASE_SECONDS * attempt
    else:
        delay = HTTP_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
    time.sleep(min(delay, 60.0))
