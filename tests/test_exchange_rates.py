from unittest.mock import MagicMock, patch

from src.modules.subscription import exchange_rates


ECB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Envelope>
  <Cube>
    <Cube time="2026-09-04">
      <Cube currency="USD" rate="1.2000"/>
      <Cube currency="CNY" rate="8.4000"/>
      <Cube currency="GBP" rate="0.9000"/>
    </Cube>
  </Cube>
</Envelope>
"""


def _clear_cache():
    exchange_rates._cache = None
    exchange_rates._cache_at = 0.0


def test_ecb_rates_are_normalized_to_usd():
    result = exchange_rates._parse_ecb(ECB_XML)
    assert result["base"] == "USD"
    assert result["rates"]["USD"] == 1.0
    assert result["rates"]["CNY"] == 7.0
    assert result["rates"]["GBP"] == 0.75
    assert result["rate_date"] == "2026-09-04"
    assert result["display_only"] is True


def test_network_failure_degrades_to_usd_without_affecting_money():
    _clear_cache()
    with patch.object(exchange_rates.httpx, "Client", side_effect=RuntimeError("offline")):
        result = exchange_rates.get_display_rates(force_refresh=True)
    assert result["rates"] == {"USD": 1.0}
    assert result["stale"] is True
    assert result["display_only"] is True


def test_stale_cache_is_preserved_when_refresh_fails():
    _clear_cache()
    response = MagicMock()
    response.content = ECB_XML.encode()
    response.text = ECB_XML
    response.raise_for_status.return_value = None
    client = MagicMock()
    client.__enter__.return_value.get.return_value = response
    with patch.object(exchange_rates.httpx, "Client", return_value=client):
        fresh = exchange_rates.get_display_rates(force_refresh=True)
    assert fresh["stale"] is False

    with patch.object(exchange_rates.httpx, "Client", side_effect=RuntimeError("offline")):
        stale = exchange_rates.get_display_rates(force_refresh=True)
    assert stale["rates"] == fresh["rates"]
    assert stale["stale"] is True
