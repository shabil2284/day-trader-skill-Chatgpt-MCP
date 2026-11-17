#!/usr/bin/env python3
"""
Test Alpaca PAPER readiness.
"""

import unittest
from unittest.mock import patch
from pathlib import Path
import sys

# Add the chatgpt-mcp directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution_server import get_execution_server_status, get_account, get_positions


class TestPaperReadiness(unittest.TestCase):

    @patch('order_gateway._ENV_VARS', {
        'ALPACA_PAPER_API_KEY': 'paper_key',
        'ALPACA_PAPER_SECRET_KEY': 'paper_secret'
    })
    @patch('order_gateway.ALPACA_PAPER_TRADING_ENABLED', True)
    @patch('order_gateway.ALPACA_LIVE_TRADING_ENABLED', False)
    @patch('order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED', True)
    def test_paper_account_configured(self):
        """Test that paper account is properly configured."""
        status = get_execution_server_status()
        self.assertTrue(status['paper_account_configured'])
        self.assertFalse(status['live_account_configured'])
        self.assertTrue(status['broker_connection_configured'])
        self.assertTrue(status['paper_trading_enabled'])
        self.assertFalse(status['live_trading_enabled'])
        self.assertTrue(status['order_submission_enabled'])

    @patch('order_gateway.request')
    def test_paper_account_status(self, mock_request):
        """Test that paper account status is properly returned."""
        # Mock account response
        mock_request.return_value = {
            "status": "ACTIVE",
            "currency": "USD",
            "cash": "10000.00",
            "portfolio_value": "10000.00",
            "buying_power": "10000.00",
            "trading_blocked": False
        }

        result = get_account("paper")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(result["cash"], "10000.00")
        self.assertEqual(result["buying_power"], "10000.00")
        self.assertEqual(result["mode"], "PAPER")

    @patch('order_gateway.request')
    def test_paper_positions_empty(self, mock_request):
        """Test that empty positions are properly returned for paper."""
        # Mock empty positions response
        mock_request.return_value = []

        result = get_positions("paper")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["positions"], [])
        self.assertEqual(result["count"], 0)

    @patch('order_gateway.request')
    def test_paper_positions_with_data(self, mock_request):
        """Test that positions with data are properly returned for paper."""
        # Mock positions response with data
        mock_request.return_value = [
            {
                "symbol": "AAPL",
                "qty": "10",
                "market_value": "500.00",
                "unrealized_pl": "10.00"
            }
        ]

        result = get_positions("paper")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["positions"]), 1)
        self.assertEqual(result["positions"][0]["symbol"], "AAPL")
        self.assertEqual(result["positions"][0]["quantity"], "10")


if __name__ == '__main__':
    unittest.main()