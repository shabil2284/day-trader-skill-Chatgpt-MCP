import unittest
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add this checkout's MCP implementation to sys.path.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "chatgpt-mcp"))
import order_gateway

def paper_propose(**kwargs):
    """Give mocked buy proposals an explicit test-only bracket risk plan."""
    if kwargs.get("side") == "buy" and kwargs.get("mode") == order_gateway.TradeMode.PAPER:
        if kwargs.get("order_type") == "market" and kwargs.get("reference_price") is not None:
            kwargs["order_type"] = "limit"
            kwargs["limit_price"] = kwargs["reference_price"]
            kwargs["reference_price"] = None
        entry = kwargs.get("limit_price")
        if entry is not None:
            kwargs.setdefault("stop_loss_price", round(float(entry) - 1.00, 2))
            kwargs.setdefault("take_profit_price", round(float(entry) + 2.00, 2))
    return order_gateway.propose(**kwargs)




class TestOrderAudit(unittest.TestCase):
    def setUp(self):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True
        self.test_state_dir = Path(tempfile.mkdtemp())
        order_gateway.STATE_DIR = self.test_state_dir
        # Mock environment
        order_gateway._ENV_VARS = {
            "ALPACA_PAPER_API_KEY": "paper_key",
            "ALPACA_PAPER_SECRET_KEY": "paper_secret"
        }

    def tearDown(self):
        for f in self.test_state_dir.glob("*"):
            f.unlink()
        self.test_state_dir.rmdir()

    def test_reconciliation_flow(self):
        """Test reconciliation flow when submission outcome is unknown."""
        with patch("urllib.request.urlopen") as mock_urlopen,              patch("order_gateway.validate_risk") as mock_risk:
            
            # Setup: Mock success for initial account check, then timeout/unknown for post
            mock_account = MagicMock()
            mock_account.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()
            
            # Proposal
            mock_urlopen.return_value.__enter__.return_value = mock_account
            prop = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )
            
            # Simulate submission unknown
            proposal_id = prop["proposal_id"]
            with order_gateway._locked_state(order_gateway.TradeMode.PAPER) as state:
                state["proposals"][proposal_id]["status"] = "submission_unknown"
            
            # Mock Alpaca successful lookup
            mock_order = MagicMock()
            mock_order.read.return_value = json.dumps({
                "id": "alpaca_123", "status": "accepted"
            }).encode()
            mock_urlopen.return_value.__enter__.side_effect = [mock_order]
            
            # Reconcile
            result = order_gateway.reconcile(proposal_id)
            self.assertEqual(result["status"], "SUBMITTED")
            
            # Verify state
            state = order_gateway.read_state(order_gateway.TradeMode.PAPER)
            self.assertEqual(state["proposals"][proposal_id]["status"], "submitted")

if __name__ == "__main__":
    unittest.main()
