import unittest
from unittest.mock import patch

from etf_sources import _fetch_ishares_holdings, _fetch_ishares_product_data_holdings


class _FakeResponse:
    def __init__(self, payload=None, text="", status_code=200):
        self._payload = payload or {}
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _ishares_api_payload(*tickers):
    return {
        "componentsByNameMap": {
            "holdings": {
                "containersByNameMap": {
                    "all": {
                        "dataPointsByNameMap": {
                            "ticker": {
                                "value": list(tickers),
                            },
                            "asOfDate": {
                                "formattedValue": "May 15, 2026",
                            },
                        },
                    },
                },
            },
        },
    }


class EtfSourcesTests(unittest.TestCase):
    def test_ishares_product_data_holdings_reads_all_ticker_values(self):
        with patch("requests.get", return_value=_FakeResponse(_ishares_api_payload("AAPL", "BRK.B", "USD", "MSFT"))):
            payload = _fetch_ishares_product_data_holdings("IWB", "239707")

        self.assertEqual(payload["symbol"], "IWB")
        self.assertEqual(payload["tickers"], ["AAPL", "BRK-B", "MSFT"])
        self.assertEqual(payload["as_of"], "May 15, 2026")
        self.assertIn("iShares product-data API", payload["note"])

    def test_ishares_holdings_uses_product_data_api_before_yahoo_fallback(self):
        with patch("requests.get", return_value=_FakeResponse(_ishares_api_payload("BE", "CRDO", "FN"))) as mock_get:
            payload = _fetch_ishares_holdings("IWM")

        self.assertEqual(payload["tickers"], ["BE", "CRDO", "FN"])
        self.assertEqual(mock_get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
