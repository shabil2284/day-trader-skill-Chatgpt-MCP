import unittest
from unittest.mock import patch
from pathlib import Path
import sys

# Add the chatgpt-mcp directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import get_positions as server_get_positions, list_order_proposals as server_list_order_proposals
from execution_server import get_positions, list_order_proposals

class TestEmptyResponses(unittest.TestCase):

    @patch('order_gateway.request')
    def test_get_positions_empty_list(self, mock_request):
        """Test that get_positions returns structured dict with empty positions list when API returns []"""
        mock_request.return_value = []

        for func in [server_get_positions, get_positions]:
            for mode in ['paper', 'live']:
                result = func(mode)
                self.assertIsInstance(result, dict, f"{func.__module__}.{func.__name__} should return dict")
                self.assertEqual(result["positions"], [], f"{func.__module__}.{func.__name__} positions should be empty list")
                self.assertEqual(result["count"], 0, f"{func.__module__}.{func.__name__} count should be 0")
                self.assertEqual(result["mode"], mode.upper())

    @patch('order_gateway.request')
    def test_get_positions_unexpected_type_raises_runtime_error(self, mock_request):
        """Test that unexpected non-list responses (e.g. dict or None) raise RuntimeError"""
        for invalid_resp in [{}, None, "invalid"]:
            mock_request.return_value = invalid_resp
            for func in [server_get_positions, get_positions]:
                for mode in ['paper', 'live']:
                    with self.assertRaises(RuntimeError):
                        func(mode)

    @patch('order_gateway.request')
    def test_get_positions_broker_exception_propagates(self, mock_request):
        """Test that broker request exceptions propagate as errors"""
        mock_request.side_effect = RuntimeError("Broker connection failed")
        for func in [server_get_positions, get_positions]:
            for mode in ['paper', 'live']:
                with self.assertRaises(RuntimeError):
                    func(mode)

    @patch('order_gateway.request')
    def test_get_positions_non_empty(self, mock_request):
        """Test that non-empty positions retain data correctly"""
        raw_position = {
            "symbol": "AAPL",
            "qty": "10",
            "market_value": "1500.00",
            "unrealized_pl": "50.00"
        }
        mock_request.return_value = [raw_position]

        for func in [server_get_positions, get_positions]:
            for mode in ['paper', 'live']:
                result = func(mode)
                self.assertIsInstance(result, dict)
                self.assertEqual(result["count"], 1)
                self.assertEqual(result["mode"], mode.upper())
                self.assertEqual(len(result["positions"]), 1)
                if func == get_positions:
                    # execution_server normalizes field names
                    self.assertEqual(result["positions"][0]["symbol"], "AAPL")
                    self.assertEqual(result["positions"][0]["quantity"], "10")
                else:
                    self.assertEqual(result["positions"][0], raw_position)

    @patch('order_gateway.list_proposals')
    def test_list_order_proposals_empty_list(self, mock_list_proposals):
        """Test that list_order_proposals returns structured dict with count 0 when no proposals exist"""
        mock_list_proposals.return_value = []

        for func in [server_list_order_proposals, list_order_proposals]:
            for mode in [None, 'paper', 'live']:
                result = func(mode)
                self.assertIsInstance(result, dict, f"{func.__module__}.{func.__name__} should return dict")
                self.assertEqual(result["proposals"], [], f"{func.__module__}.{func.__name__} proposals should be empty list")
                self.assertEqual(result["count"], 0, f"{func.__module__}.{func.__name__} count should be 0")
                expected_mode = mode.upper() if mode else "ALL"
                self.assertEqual(result["mode"], expected_mode)

    @patch('order_gateway.list_proposals')
    def test_list_order_proposals_unexpected_type_raises_runtime_error(self, mock_list_proposals):
        """Test that unexpected non-list proposal responses raise RuntimeError"""
        for invalid_resp in [{}, None, "invalid"]:
            mock_list_proposals.return_value = invalid_resp
            for func in [server_list_order_proposals, list_order_proposals]:
                for mode in [None, 'paper', 'live']:
                    with self.assertRaises(RuntimeError):
                        func(mode)

    @patch('order_gateway.list_proposals')
    def test_list_order_proposals_non_empty(self, mock_list_proposals):
        """Test that list_order_proposals retains data correctly when proposals exist"""
        sample_proposal = {"id": "test_id", "status": "pending"}
        mock_list_proposals.return_value = [sample_proposal]

        for func in [server_list_order_proposals, list_order_proposals]:
            for mode in [None, 'paper', 'live']:
                result = func(mode)
                self.assertIsInstance(result, dict)
                self.assertEqual(result["count"], 1)
                self.assertEqual(result["proposals"], [sample_proposal])

    def test_invalid_mode_validation(self, *args):
        """Verify that invalid trading modes return error dictionary instead of raising exception"""
        for func in [server_get_positions, get_positions]:
            res = func("invalid_mode")
            self.assertIn("error", res)
            self.assertTrue("Invalid mode" in res["error"])

        for func in [server_list_order_proposals, list_order_proposals]:
            res = func("invalid_mode")
            self.assertIn("error", res)
            self.assertTrue("Invalid mode" in res["error"])

if __name__ == '__main__':
    unittest.main()
