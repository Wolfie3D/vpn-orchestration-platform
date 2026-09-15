"""Read-only display-currency rates derived from the ECB daily reference feed.

The account ledger and every authoritative quote remain in USD. These rates
are presentation metadata only and must never be used to settle, credit or
debit money.
"""

from __future__ import annotations

from datetime import datetime, timezone
import threading
import time
from xml.etree import ElementTree

import httpx
from loguru import logger


ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
DISPLAY_CURRENCIES = ("USD", "EUR", "GBP", "CNY", "JPY", "KRW", "INR", "PHP", "TRY")
_CACHE_TTL_SECONDS = 12 * 60 * 60
_lock = threading.Lock()
_cache: dict | None = None
_cache_at = 0.0


def _parse_ecb(xml: str) -> dict:
    root = ElementTree.fromstring(xml)
    ecb_per_eur: dict[str, float] = {"EUR": 1.0}
    rate_date = None
    for node in root.iter():
        currency = node.attrib.get("currency")
        rate = node.attrib.get("rate")
        if node.attrib.get("time"):
            rate_date = node.attrib["time"]
        if currency and rate:
            value = float(rate)
            if value > 0:
                ecb_per_eur[currency.upper()] = value
    usd_per_eur = ecb_per_eur.get("USD")
    if not usd_per_eur:
        raise ValueError("ECB feed does not contain USD")
    per_usd = {
        code: (1.0 if code == "USD" else round(ecb_per_eur[code] / usd_per_eur, 8))
        for code in DISPLAY_CURRENCIES
        if code in ecb_per_eur or code == "USD"
    }
    return {
        "base": "USD",
        "rates": per_usd,
        "rate_date": rate_date,
        "source": "European Central Bank",
        "display_only": True,
    }


def get_display_rates(*, force_refresh: bool = False) -> dict:
    """Return cached USD display rates; degrade to USD-only if ECB is down."""

    global _cache, _cache_at
    now = time.monotonic()
    if not force_refresh and _cache and now - _cache_at < _CACHE_TTL_SECONDS:
        return dict(_cache)
    with _lock:
        now = time.monotonic()
        if not force_refresh and _cache and now - _cache_at < _CACHE_TTL_SECONDS:
            return dict(_cache)
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(ECB_DAILY_URL, headers={"Accept": "application/xml"})
                response.raise_for_status()
                if len(response.content) > 1_000_000:
                    raise ValueError("ECB response is unexpectedly large")
                result = _parse_ecb(response.text)
            result["fetched_at"] = datetime.now(timezone.utc).isoformat()
            result["stale"] = False
            _cache = result
            _cache_at = now
            return dict(result)
        except Exception as exc:
            logger.warning("Could not refresh display exchange rates: {}", exc)
            if _cache:
                stale = dict(_cache)
                stale["stale"] = True
                return stale
            return {
                "base": "USD",
                "rates": {"USD": 1.0},
                "rate_date": None,
                "fetched_at": None,
                "source": "unavailable",
                "display_only": True,
                "stale": True,
            }
