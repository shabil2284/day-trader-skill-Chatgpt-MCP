import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path to import order_gateway
sys.path.append(str(Path(__file__).resolve().parents[1]))
import order_gateway
from order_gateway import TradeMode

class TestEndpointNormalization(unittest.TestCase):
    @patch("urllib.request.urlopen")
    @patch("order_gateway.credentials")
    def test_request_normalization(self, mock_credentials, mock_urlopen):
        # Mock urlopen response
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        mock_credentials.return_value = ("key", "secret", "https://api.alpaca.markets/v2")

        # 1. Base URL has /v2, path has no /v2
        order_gateway.request("GET", "/account", TradeMode.PAPER)
        args, kwargs = mock_urlopen.call_args
        self.assertEqual(args[0].full_url, "https://api.alpaca.markets/v2/account")

        # 2. Base URL has /v2, path has /v2
        order_gateway.request("GET", "/v2/account", TradeMode.PAPER)
        args, kwargs = mock_urlopen.call_args
        self.assertEqual(args[0].full_url, "https://api.alpaca.markets/v2/account")

        # 3. Base URL has no /v2, path has no /v2
        mock_credentials.return_value = ("key", "secret", "https://api.alpaca.markets")
        order_gateway.request("GET", "/account", TradeMode.PAPER)
        args, kwargs = mock_urlopen.call_args
        self.assertEqual(args[0].full_url, "https://api.alpaca.markets/v2/account")

        # 4. Base URL has no /v2, path has /v2
        mock_credentials.return_value = ("key", "secret", "https://api.alpaca.markets")
        order_gateway.request("GET", "/v2/account", TradeMode.PAPER)
        args, kwargs = mock_urlopen.call_args
        self.assertEqual(args[0].full_url, "https://api.alpaca.markets/v2/account")

        # 5. Path without leading slash
        mock_credentials.return_value = ("key", "secret", "https://api.alpaca.markets/v2")
        order_gateway.request("GET", "account", TradeMode.PAPER)
        args, kwargs = mock_urlopen.call_args
        self.assertEqual(args[0].full_url, "https://api.alpaca.markets/v2/account")

        # 6. Base URL with trailing slash
        mock_credentials.return_value = ("key", "secret", "https://api.alpaca.markets/v2/")
        order_gateway.request("GET", "/account", TradeMode.PAPER)
        args, kwargs = mock_urlopen.call_args
        self.assertEqual(args[0].full_url, "https://api.alpaca.markets/v2/account")

if __name__ == "__main__":
    unittest.main()
