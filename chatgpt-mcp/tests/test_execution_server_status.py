import unittest
from unittest.mock import patch
from pathlib import Path
import sys

# Add the chatgpt-mcp directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution_server import get_execution_server_status

class TestExecutionServerStatus(unittest.TestCase):

    @patch('order_gateway._ENV_VARS', {})
    @patch('order_gateway.ALPACA_PAPER_TRADING_ENABLED', False)
    @patch('order_gateway.ALPACA_LIVE_TRADING_ENABLED', False)
    @patch('order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED', False)
    def test_no_keys_disabled_trading(self):
        status = get_execution_server_status()
        self.assertEqual(status['server'], 'Execution Server')
        self.assertEqual(status['status'], 'running')
        self.assertFalse(status['paper_account_configured'])
        self.assertFalse(status['live_account_configured'])
        self.assertFalse(status['broker_connection_configured'])
        self.assertFalse(status['paper_trading_enabled'])
        self.assertFalse(status['live_trading_enabled'])
        self.assertFalse(status['order_submission_enabled'])

    @patch('order_gateway._ENV_VARS', {'ALPACA_PAPER_API_KEY': 'pk'})
    @patch('order_gateway.ALPACA_PAPER_TRADING_ENABLED', True)
    @patch('order_gateway.ALPACA_LIVE_TRADING_ENABLED', False)
    @patch('order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED', True)
    def test_paper_key_enabled_paper_trading(self):
        status = get_execution_server_status()
        self.assertTrue(status['paper_account_configured'])
        self.assertFalse(status['live_account_configured'])
        self.assertTrue(status['broker_connection_configured'])
        self.assertTrue(status['paper_trading_enabled'])
        self.assertFalse(status['live_trading_enabled'])
        self.assertTrue(status['order_submission_enabled'])

    @patch('order_gateway._ENV_VARS', {'ALPACA_LIVE_API_KEY': 'lk'})
    @patch('order_gateway.ALPACA_PAPER_TRADING_ENABLED', False)
    @patch('order_gateway.ALPACA_LIVE_TRADING_ENABLED', True)
    @patch('order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED', True)
    def test_live_credentials_never_enable_live_trading(self):
        status = get_execution_server_status()
        self.assertFalse(status['paper_account_configured'])
        self.assertTrue(status['live_account_configured'])
        self.assertTrue(status['broker_connection_configured'])
        self.assertFalse(status['paper_trading_enabled'])
        self.assertFalse(status['live_trading_enabled'])
        self.assertTrue(status['live_trading_policy_enforced'])
        self.assertTrue(status['order_submission_enabled'])

if __name__ == '__main__':
    unittest.main()
