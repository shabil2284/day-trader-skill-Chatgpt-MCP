import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import unittest
from unittest.mock import patch, MagicMock
from order_gateway import TradeMode, propose

class TestExecutionLogic(unittest.TestCase):
    @patch("order_gateway.request")
    @patch("order_gateway.validate_risk")
    @patch("order_gateway._locked_state")
    def test_mocked_proposal_lifecycle(self, mock_lock, mock_risk, mock_request):
        # Mock account check
        mock_request.return_value = {"status": "ACTIVE", "buying_power": "10000.00"}

        # Test propose with amount under the cap
        proposal = propose(TradeMode.PAPER, "AAPL", "buy", 1, "market", reference_price=50.0)
        self.assertEqual(proposal["status"], "PENDING_APPROVAL")
        self.assertIn("proposal_id", proposal)

if __name__ == "__main__":
    unittest.main()
