import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add the chatgpt-mcp directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import order_gateway
from order_gateway import TradeMode

class TestBrokerStatus(unittest.TestCase):
    @patch("order_gateway.read_state")
    @patch("order_gateway._locked_state")
    @patch("order_gateway.request")
    def test_get_broker_status_found(self, mock_request, mock_locked_state, mock_read_state):
        # Setup mock state
        mock_proposal = {
            "id": "test123",
            "broker_order_id": "alpaca_id_123",
            "status": "submitted"
        }
        mock_read_state.return_value = {"proposals": {"test123": mock_proposal}}

        # Mock locked_state to return the proposal
        from contextlib import contextmanager
        @contextmanager
        def mock_locked_state_cm(mode):
            yield {"proposals": {"test123": mock_proposal}}
        mock_locked_state.side_effect = mock_locked_state_cm

        # Mock Alpaca response
        mock_request.return_value = {"id": "alpaca_id_123", "status": "filled"}

        res = order_gateway.get_broker_status("test123")
        self.assertEqual(res["status"], "filled")
        self.assertEqual(res["broker_order_id"], "alpaca_id_123")

    @patch("order_gateway.read_state")
    def test_get_broker_status_not_found(self, mock_read_state):
        mock_read_state.return_value = {"proposals": {}}

        with self.assertRaises(ValueError):
            order_gateway.get_broker_status("invalid_id")

if __name__ == '__main__':
    unittest.main()
