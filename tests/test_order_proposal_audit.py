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




class TestOrderProposalAudit(unittest.TestCase):
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

    def test_proposal_uniqueness(self):
        """Test that different proposals have unique proposal IDs."""
        with patch("urllib.request.urlopen") as mock_urlopen,              patch("order_gateway.validate_risk") as mock_risk:
            
            # Setup: Mock success for initial account check
            mock_account = MagicMock()
            mock_account.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()
            
            mock_urlopen.return_value.__enter__.return_value = mock_account
            
            # Create two proposals
            prop1 = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )
            
            prop2 = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )
            
            # Check if proposal IDs are unique
            self.assertNotEqual(prop1["proposal_id"], prop2["proposal_id"])
            
    def test_proposal_expiry(self):
        """Test that proposals expire after TTL."""
        with patch("urllib.request.urlopen") as mock_urlopen,              patch("order_gateway.validate_risk") as mock_risk:
            
            # Setup: Mock success for initial account check
            mock_account = MagicMock()
            mock_account.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()
            
            mock_urlopen.return_value.__enter__.return_value = mock_account
            
            # Create a proposal
            prop = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )
            
            proposal_id = prop["proposal_id"]
            
            # Wait for proposal to expire
            # Instead of sleeping, manually expire it by setting status
            with order_gateway._locked_state(order_gateway.TradeMode.PAPER) as state:
                state["proposals"][proposal_id]["expires_at"] = time.time() - 1
            
            # Check if proposal is expired when listing
            proposals = order_gateway.list_proposals()
            for p in proposals:
                if p["proposal_id"] == proposal_id:
                    self.assertEqual(p["status"], "expired")

    def test_proposal_reconciliation(self):
        """Test reconciliation of proposals with uncertain submission outcome."""
        with patch("urllib.request.urlopen") as mock_urlopen,              patch("order_gateway.validate_risk") as mock_risk:
            
            # Setup: Mock success for initial account check
            mock_account = MagicMock()
            mock_account.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()
            
            mock_urlopen.return_value.__enter__.return_value = mock_account
            
            # Create a proposal
            prop = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )
            
            proposal_id = prop["proposal_id"]
            
            # Simulate submission unknown
            with order_gateway._locked_state(order_gateway.TradeMode.PAPER) as state:
                state["proposals"][proposal_id]["status"] = "submission_unknown"
                state["proposals"][proposal_id]["broker_order_id"] = None
            
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

    def test_proposal_approval_flow(self):
        """Test the approval and submission flow."""
        with patch("urllib.request.urlopen") as mock_urlopen,              patch("order_gateway.validate_risk") as mock_risk:
            
            # Setup: Mock success for initial account check, then successful submission
            mock_account = MagicMock()
            mock_account.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()
            
            mock_submit = MagicMock()
            mock_submit.read.return_value = json.dumps({
                "id": "alpaca_123", "status": "accepted"
            }).encode()
            
            mock_urlopen.return_value.__enter__.side_effect = [mock_account, mock_account, mock_submit]
            
            # Create a proposal
            prop = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )
            
            proposal_id = prop["proposal_id"]
            approval_phrase = prop["approval_phrase"]
            
            # Approve and submit
            result = order_gateway.approve_and_submit(proposal_id, approval_phrase)
            self.assertEqual(result["status"], "SUBMITTED_TO_ALPACA_PAPER")
            
            # Verify state
            state = order_gateway.read_state(order_gateway.TradeMode.PAPER)
            self.assertEqual(state["proposals"][proposal_id]["status"], "submitted")
            self.assertIsNotNone(state["proposals"][proposal_id]["broker_order_id"])

    def test_proposal_rejection(self):
        """Test rejection of a proposal."""
        with patch("urllib.request.urlopen") as mock_urlopen,              patch("order_gateway.validate_risk") as mock_risk:
            
            # Setup: Mock success for initial account check
            mock_account = MagicMock()
            mock_account.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()
            
            mock_urlopen.return_value.__enter__.return_value = mock_account
            
            # Create a proposal
            prop = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )
            
            proposal_id = prop["proposal_id"]
            
            # Reject the proposal
            result = order_gateway.reject(proposal_id)
            self.assertEqual(result["status"], "REJECTED")
            
            # Verify state
            state = order_gateway.read_state(order_gateway.TradeMode.PAPER)
            self.assertEqual(state["proposals"][proposal_id]["status"], "rejected")

if __name__ == "__main__":
    unittest.main()
