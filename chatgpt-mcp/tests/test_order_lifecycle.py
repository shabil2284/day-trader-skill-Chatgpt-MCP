#!/usr/bin/env python3
"""
Test the full order lifecycle using MCP handlers.
"""

import unittest
from unittest.mock import patch
from pathlib import Path
import sys

# Add the chatgpt-mcp directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import order_gateway

from execution_server import (
    propose_order,
    approve_and_submit_order,
    reject_order,
    reconcile_order
)


class TestOrderLifecycle(unittest.TestCase):

    @patch('order_gateway.propose')
    @patch('order_gateway.approve_and_submit')
    @patch('order_gateway.reject')
    @patch('order_gateway.reconcile')
    @patch('order_gateway.list_proposals')
    def test_order_lifecycle(self, mock_list_proposals, mock_reconcile, mock_reject, mock_approve_and_submit, mock_propose):
        """Test the full order lifecycle: propose, approve, submit, reject, reconcile."""

        # Mock proposal
        mock_propose.return_value = {
            "status": "PENDING_APPROVAL",
            "proposal_id": "test123",
            "mode": "PAPER",
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 1,
            "order_type": "MARKET",
            "approval_phrase": "APPROVE test123 PAPER BUY 1 AAPL LIMIT 50.00 STOP 49.00 TARGET 52.00 DAY"
        }

        # Mock approval and submission
        mock_approve_and_submit.return_value = {
            "status": "SUBMITTED_TO_ALPACA_PAPER",
            "proposal_id": "test123",
            "broker_order_id": "alpaca_id",
            "broker_status": "accepted"
        }

        # Mock rejection
        mock_reject.return_value = {
            "status": "REJECTED",
            "proposal_id": "test123",
            "mode": "PAPER"
        }

        # Mock reconciliation
        mock_reconcile.return_value = {
            "status": "SUBMITTED",
            "broker_order_id": "alpaca_id",
            "broker_status": "filled",
            "mode": "PAPER"
        }

        # Mock list proposals
        mock_list_proposals.return_value = []

        # 1. Propose an order
        proposal_result = propose_order(
            mode="paper",
            symbol="AAPL",
            side="buy",
            quantity=1,
            order_type="limit",
            limit_price=50.00,
            stop_loss_price=49.00,
            take_profit_price=52.00,
        )
        mock_propose.assert_called_with(
            mode=order_gateway.TradeMode.PAPER, symbol="AAPL", side="buy", quantity=1,
            order_type="limit", limit_price=50.00, reference_price=None,
            stop_loss_price=49.00, take_profit_price=52.00,
        )

        self.assertEqual(proposal_result["status"], "PENDING_APPROVAL")
        proposal_id = proposal_result["proposal_id"]
        approval_phrase = proposal_result["approval_phrase"]

        # 2. Approve and submit the order
        submit_result = approve_and_submit_order(
            proposal_id=proposal_id,
            approval_phrase=approval_phrase
        )

        self.assertEqual(submit_result["status"], "SUBMITTED_TO_ALPACA_PAPER")

        # 3. Reject a new proposal (simulate rejection)
        # First, propose another order
        mock_propose.return_value = {
            "status": "PENDING_APPROVAL",
            "proposal_id": "test456",
            "mode": "PAPER",
            "symbol": "MSFT",
            "side": "BUY",
            "quantity": 1,
            "order_type": "MARKET",
            "approval_phrase": "APPROVE test456 PAPER BUY 1 MSFT LIMIT 50.00 STOP 49.00 TARGET 52.00 DAY"
        }

        proposal_result2 = propose_order(
            mode="paper",
            symbol="MSFT",
            side="buy",
            quantity=1,
            order_type="limit",
            limit_price=50.00,
            stop_loss_price=49.00,
            take_profit_price=52.00,
        )

        reject_result = reject_order(proposal_id=proposal_result2["proposal_id"])
        self.assertEqual(reject_result["status"], "REJECTED")

        # 4. Test reconciliation (simulate uncertain submission)
        # First, create a proposal in submission_unknown state
        mock_propose.return_value = {
            "status": "PENDING_APPROVAL",
            "proposal_id": "test789",
            "mode": "PAPER",
            "symbol": "GOOG",
            "side": "BUY",
            "quantity": 1,
            "order_type": "MARKET",
            "approval_phrase": "APPROVE test789 PAPER BUY 1 GOOG LIMIT 50.00 STOP 49.00 TARGET 52.00 DAY"
        }

        # Simulate submission failure
        mock_approve_and_submit.return_value = {
            "status": "SUBMISSION_UNKNOWN",
            "proposal_id": "test789",
            "mode": "PAPER"
        }

        # Approve and submit
        submit_result2 = approve_and_submit_order(
            proposal_id="test789",
            approval_phrase="APPROVE test789 PAPER BUY 1 GOOG LIMIT 50.00 STOP 49.00 TARGET 52.00 DAY"
        )

        # Reconcile
        reconcile_result = reconcile_order(proposal_id="test789")
        self.assertEqual(reconcile_result["status"], "SUBMITTED")


if __name__ == '__main__':
    unittest.main()
