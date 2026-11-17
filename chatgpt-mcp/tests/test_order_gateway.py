import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os
import hashlib
import time
import secrets
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path to import order_gateway


sys.path.append(str(Path(__file__).resolve().parents[1]))
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

from order_gateway import TradeMode

class TestOrderGateway(unittest.TestCase):
    def setUp(self):
        # Reset switches and env vars for each test
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = False
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = False
        order_gateway.ALPACA_LIVE_TRADING_ENABLED = False
        order_gateway._ENV_VARS = {
            "ALPACA_PAPER_API_KEY": "paper_key",
            "ALPACA_PAPER_SECRET_KEY": "paper_secret",
            "ALPACA_LIVE_API_KEY": "live_key",
            "ALPACA_LIVE_SECRET_KEY": "live_secret"
        }

        # Temporary state directory
        self.test_state_dir = Path(tempfile.mkdtemp())
        order_gateway.STATE_DIR = self.test_state_dir

    def tearDown(self):
        # Cleanup
        for f in self.test_state_dir.glob("*"):
            if f.is_file(): f.unlink()
        if self.test_state_dir.exists():
            self.test_state_dir.rmdir()

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_propose_paper_buy_limit_bracket(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True

        # Mock account response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "status": "ACTIVE",
            "trading_blocked": False,
            "buying_power": "1000.00"
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = paper_propose(
            mode=TradeMode.PAPER,
            symbol="AAPL",
            side="buy",
            quantity=1,
            order_type="market",
            reference_price=50.00
        )

        self.assertEqual(res["status"], "PENDING_APPROVAL")
        self.assertEqual(res["mode"], "PAPER")
        self.assertEqual(res["symbol"], "AAPL")
        self.assertEqual(res["side"], "BUY")
        self.assertIn("APPROVE", res["approval_phrase"])
        self.assertIn("STOP 49.00 TARGET 52.00", res["approval_phrase"])
        mock_risk.assert_called_once()
        risk_order = mock_risk.call_args.args[0]
        self.assertEqual(risk_order["order_class"], "bracket")
        self.assertEqual(risk_order["stop_loss_stop_price"], "49.00")
        self.assertEqual(risk_order["take_profit_limit_price"], "52.00")
        self.assertEqual(risk_order["plan"], {"entry": "50.00", "stop": "49.00", "target": "52.00"})

    def test_buy_requires_limit_and_protective_stop_and_target(self):
        with patch("order_gateway.request") as mock_request, \
             patch("order_gateway.validate_risk"):
            with self.assertRaisesRegex(ValueError, "must use a limit order"):
                order_gateway.propose(
                    mode=TradeMode.PAPER, symbol="AAPL", side="buy", quantity=1,
                    order_type="market", reference_price=50.00,
                    stop_loss_price=49.00, take_profit_price=52.00,
                )
            with self.assertRaisesRegex(ValueError, "require both stop_loss_price and take_profit_price"):
                order_gateway.propose(
                    mode=TradeMode.PAPER, symbol="AAPL", side="buy", quantity=1,
                    order_type="limit", limit_price=50.00,
                )
            with self.assertRaisesRegex(ValueError, "stop_loss_price < entry price < take_profit_price"):
                order_gateway.propose(
                    mode=TradeMode.PAPER, symbol="AAPL", side="buy", quantity=1,
                    order_type="limit", limit_price=50.00,
                    stop_loss_price=51.00, take_profit_price=52.00,
                )
        mock_request.assert_not_called()

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_paper_notional_cap_accepts_100_and_rejects_100_01(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        account = MagicMock()
        account.read.return_value = json.dumps({
            "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = account

        accepted = paper_propose(
            mode=TradeMode.PAPER, symbol="AAPL", side="buy", quantity=1,
            order_type="market", reference_price=100.00,
        )
        self.assertEqual(accepted["estimated_value_usd"], 100.00)
        with self.assertRaisesRegex(ValueError, r"\$100\.00.*\$100\.01"):
            paper_propose(
                mode=TradeMode.PAPER, symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=100.01,
            )

    def test_paper_credentials_ignore_a_live_base_url_override(self):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway._ENV_VARS["APCA_API_BASE_URL"] = "https://api.alpaca.markets/v2"
        _, _, url = order_gateway.credentials(TradeMode.PAPER)
        self.assertEqual(url, order_gateway.PAPER_URL)

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_approval_rechecks_the_100_dollar_cap_from_persisted_order(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True
        account = MagicMock()
        account.read.return_value = json.dumps({
            "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = account
        proposal = paper_propose(
            mode=TradeMode.PAPER, symbol="AAPL", side="buy", quantity=1,
            order_type="market", reference_price=50.00,
        )
        proposal_id = proposal["proposal_id"]
        with order_gateway._locked_state(TradeMode.PAPER) as state:
            stored = state["proposals"][proposal_id]
            stored.update({"qty": "2", "limit_price": "50.01", "notional_usd": 100.02})
            stored["order_payload"]["qty"] = "2"
            stored["order_payload"]["limit_price"] = "50.01"
            phrase = order_gateway._approval_phrase(stored)
            stored["approval_hash"] = hashlib.sha256(phrase.encode()).hexdigest()

        with self.assertRaisesRegex(ValueError, r"\$100\.00.*\$100\.02"):
            order_gateway.approve_and_submit(proposal_id, phrase)
        self.assertEqual(mock_urlopen.call_count, 1)  # proposal account read only

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_propose_live_buy_limit_fails_if_disabled(self, mock_risk, mock_urlopen):
        with self.assertRaises(ValueError) as cm:
            paper_propose(
                mode=TradeMode.LIVE,
                symbol="AAPL",
                side="buy",
                quantity=1,
                order_type="limit",
                limit_price=50.00
            )
        self.assertIn("Only PAPER proposals", str(cm.exception))
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_approve_and_submit_paper(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True

        # 1. Propose
        mock_account_response = MagicMock()
        mock_account_response.read.return_value = json.dumps({
            "status": "ACTIVE",
            "trading_blocked": False,
            "buying_power": "1000.00"
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_account_response

        prop = paper_propose(
            mode=TradeMode.PAPER,
            symbol="AAPL",
            side="buy",
            quantity=1,
            order_type="market",
            reference_price=50.00
        )

        # 2. Approve and submit
        mock_submit_response = MagicMock()
        mock_submit_response.read.return_value = json.dumps({
            "id": "alpaca_id",
            "status": "accepted"
        }).encode()

        # URL open will be called twice: once for account check, once for POST order
        mock_urlopen.return_value.__enter__.side_effect = [mock_account_response, mock_submit_response]

        res = order_gateway.approve_and_submit(prop["proposal_id"], prop["approval_phrase"])

        self.assertEqual(res["status"], "SUBMITTED_TO_ALPACA_PAPER")
        self.assertEqual(res["broker_order_id"], "alpaca_id")
        submitted_request = mock_urlopen.call_args.args[0]
        submitted_payload = json.loads(submitted_request.data)
        self.assertEqual(submitted_payload["order_class"], "bracket")
        self.assertEqual(submitted_payload["take_profit"], {"limit_price": "52.00"})
        self.assertEqual(submitted_payload["stop_loss"], {"stop_price": "49.00"})

    def test_missing_broker_order_id_persists_unknown_submission(self):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True

        def mock_request(method, path, mode, payload=None):
            if method == "GET":
                return {"status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"}
            return {"status": "accepted"}  # An acknowledgement without an order ID is ambiguous.

        with patch("order_gateway.request", side_effect=mock_request), \
             patch("order_gateway.validate_risk"):
            proposal = paper_propose(
                mode=TradeMode.PAPER, symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00,
            )
            with self.assertRaisesRegex(RuntimeError, "Submission outcome is uncertain"):
                order_gateway.approve_and_submit(
                    proposal["proposal_id"], proposal["approval_phrase"]
                )

        persisted = order_gateway.read_state(TradeMode.PAPER)["proposals"][proposal["proposal_id"]]
        self.assertEqual(persisted["status"], "submission_unknown")
        self.assertNotIn("broker_order_id", persisted)

    def test_reconcile_recovers_a_crash_in_submitting_state(self):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        with patch("order_gateway.request") as mock_request, \
             patch("order_gateway.validate_risk"):
            mock_request.side_effect = [
                {"status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"},
                {"id": "mock-recovered-order", "status": "accepted"},
            ]
            proposal = paper_propose(
                mode=TradeMode.PAPER, symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00,
            )
            with order_gateway._locked_state(TradeMode.PAPER) as state:
                state["proposals"][proposal["proposal_id"]]["status"] = "submitting"

            result = order_gateway.reconcile(proposal["proposal_id"])

        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual(result["broker_order_id"], "mock-recovered-order")
        persisted = order_gateway.read_state(TradeMode.PAPER)["proposals"][proposal["proposal_id"]]
        self.assertEqual(persisted["status"], "submitted")

    def test_concurrent_approval_submits_once(self):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True
        submit_started = threading.Event()
        allow_submit = threading.Event()
        submit_count = []

        def fake_request(method, path, mode, payload=None):
            if method == "GET":
                return {"status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"}
            submit_count.append(1)
            submit_started.set()
            self.assertTrue(allow_submit.wait(5), "mock submission was not released")
            return {"id": "mock-paper-order", "status": "accepted"}

        with patch("order_gateway.request", side_effect=fake_request), \
             patch("order_gateway.validate_risk"):
            proposal = paper_propose(
                mode=TradeMode.PAPER, symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00,
            )
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(
                    order_gateway.approve_and_submit,
                    proposal["proposal_id"], proposal["approval_phrase"],
                )
                self.assertTrue(submit_started.wait(5), "first approval did not reach the mock broker")
                second = pool.submit(
                    order_gateway.approve_and_submit,
                    proposal["proposal_id"], proposal["approval_phrase"],
                )
                with self.assertRaisesRegex(RuntimeError, "currently locked"):
                    second.result(timeout=5)
                allow_submit.set()
                result = first.result(timeout=5)

        self.assertEqual(result["status"], "SUBMITTED_TO_ALPACA_PAPER")
        self.assertEqual(len(submit_count), 1)

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_incorrect_approval_phrase(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "status": "ACTIVE",
            "trading_blocked": False,
            "buying_power": "1000.00"
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        prop = paper_propose(
            mode=TradeMode.PAPER,
            symbol="AAPL",
            side="buy",
            quantity=1,
            order_type="market",
            reference_price=50.00
        )

        with self.assertRaises(ValueError) as cm:
            order_gateway.approve_and_submit(prop["proposal_id"], "WRONG PHRASE")
        self.assertIn("Approval phrase does not exactly match", str(cm.exception))

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_insufficient_shares_for_sell(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True

        # Mock account and positions
        mock_account = MagicMock()
        mock_account.read.return_value = json.dumps({
            "status": "ACTIVE",
            "trading_blocked": False,
            "buying_power": "1000.00"
        }).encode()

        mock_positions = MagicMock()
        mock_positions.read.return_value = json.dumps([
            {"symbol": "AAPL", "qty": "5"}
        ]).encode()

        mock_orders = MagicMock()
        mock_orders.read.return_value = json.dumps([]).encode()

        mock_urlopen.return_value.__enter__.side_effect = [mock_account, mock_positions, mock_orders]

        # Try to sell 10 shares when only 5 held
        with self.assertRaises(RuntimeError) as cm:
            paper_propose(
                mode=TradeMode.PAPER,
                symbol="AAPL",
                side="sell",
                quantity=10,
                order_type="market",
                reference_price=5.00
            )
        self.assertIn("Sell quantity exceeds available long position", str(cm.exception))

    def test_fingerprint_consistency(self):
        order = {
            "symbol": "AAPL",
            "side": "buy",
            "qty": "1",
            "type": "market",
            "time_in_force": "day",
            "client_order_id": "test-id"
        }
        fp1 = order_gateway.generate_fingerprint(order)

        # Changing a field not in ALPACA_FIELDS shouldn't change fingerprint
        order["why"] = "because"
        fp2 = order_gateway.generate_fingerprint(order)
        self.assertEqual(fp1, fp2)

        # Changing a field in ALPACA_FIELDS SHOULD change it
        order["qty"] = "2"
        fp3 = order_gateway.generate_fingerprint(order)
        self.assertNotEqual(fp1, fp3)

    @patch("subprocess.run")
    def test_validate_risk_pass(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="passed")

        order = {
            "symbol": "AAPL",
            "side": "buy",
            "qty": "1",
            "type": "market",
            "time_in_force": "day",
            "client_order_id": "test-id"
        }
        fp = order_gateway.generate_fingerprint(order)

        with patch("pathlib.Path.write_text"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=json.dumps({
                 "results": [{"fingerprint": fp, "verdict": "PASS"}]
             })), \
             patch("pathlib.Path.unlink"):

            res = order_gateway.validate_risk(order, TradeMode.PAPER)
            self.assertTrue(res)

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_live_market_buy_submission_is_blocked_even_if_flag_is_set(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_LIVE_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True

        with self.assertRaises(ValueError) as cm:
            paper_propose(
                mode=TradeMode.LIVE,
                symbol="MSFT",
                side="buy",
                quantity=1,
                order_type="market",
                reference_price=50.00
            )
        self.assertIn("Only PAPER proposals", str(cm.exception))
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_rejected_proposal_cannot_be_submitted(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True

        # Mock account
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "status": "ACTIVE",
            "trading_blocked": False,
            "buying_power": "1000.00"
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        prop = paper_propose(
            mode=TradeMode.PAPER,
            symbol="AAPL",
            side="buy",
            quantity=1,
            order_type="market",
            reference_price=50.00
        )

        # Reject it
        order_gateway.reject(prop["proposal_id"])

        # Try to submit
        with self.assertRaises(ValueError) as cm:
            order_gateway.approve_and_submit(prop["proposal_id"], prop["approval_phrase"])
        self.assertIn("Proposal is not pending", str(cm.exception))

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_expired_proposal_cannot_be_submitted(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True

        # Mock account
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "status": "ACTIVE",
            "trading_blocked": False,
            "buying_power": "1000.00"
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        prop = paper_propose(
            mode=TradeMode.PAPER,
            symbol="AAPL",
            side="buy",
            quantity=1,
            order_type="market",
            reference_price=50.00
        )

        # Manually expire it in state
        with order_gateway._locked_state(TradeMode.PAPER) as state:
            state["proposals"][prop["proposal_id"]]["expires_at"] = time.time() - 10

        # Try to submit
        with self.assertRaises(ValueError) as cm:
            order_gateway.approve_and_submit(prop["proposal_id"], prop["approval_phrase"])
        self.assertIn("Proposal expired", str(cm.exception))
        persisted = order_gateway.read_state(TradeMode.PAPER)["proposals"][prop["proposal_id"]]
        self.assertEqual(persisted["status"], "expired")

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_reconcile_found(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True

        # 1. Create a proposal in submission_unknown state manually
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "status": "ACTIVE",
            "trading_blocked": False,
            "buying_power": "1000.00"
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        prop = paper_propose(
            mode=TradeMode.PAPER,
            symbol="AAPL",
            side="buy",
            quantity=1,
            order_type="market",
            reference_price=50.00
        )

        with order_gateway._locked_state(TradeMode.PAPER) as state:
            state["proposals"][prop["proposal_id"]]["status"] = "submission_unknown"

        # 2. Mock Alpaca finding the order
        mock_order_response = MagicMock()
        mock_order_response.read.return_value = json.dumps({
            "id": "alpaca_id_123",
            "status": "filled"
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_order_response

        res = order_gateway.reconcile(prop["proposal_id"])
        self.assertEqual(res["status"], "SUBMITTED")
        self.assertEqual(res["broker_order_id"], "alpaca_id_123")

        # Verify state updated
        state = order_gateway.read_state(TradeMode.PAPER)
        self.assertEqual(state["proposals"][prop["proposal_id"]]["status"], "submitted")

    @patch("urllib.request.urlopen")
    @patch("order_gateway.validate_risk")
    def test_reconcile_not_found(self, mock_risk, mock_urlopen):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True

        # 1. Create proposal
        mock_account = MagicMock()
        mock_account.read.return_value = json.dumps({
            "status": "ACTIVE",
            "trading_blocked": False,
            "buying_power": "1000.00"
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_account

        prop = paper_propose(
            mode=TradeMode.PAPER,
            symbol="AAPL",
            side="buy",
            quantity=1,
            order_type="market",
            reference_price=50.00
        )

        with order_gateway._locked_state(TradeMode.PAPER) as state:
            state["proposals"][prop["proposal_id"]]["status"] = "submission_unknown"

        # 2. Mock Alpaca 404
        mock_404 = MagicMock()
        mock_404.read.return_value = b"Not Found"
        mock_404.code = 404
        # urllib.request.urlopen raises HTTPError for non-2xx
        from urllib.error import HTTPError
        mock_urlopen.return_value.__enter__.side_effect = HTTPError(
            "url", 404, "Not Found", {}, mock_404
        )

        res = order_gateway.reconcile(prop["proposal_id"])
        self.assertEqual(res["status"], "SUBMISSION_FAILED")
        self.assertIn("404", res["error"])

    def test_concurrent_lock(self):
        # Test that _locked_state prevents concurrent access
        import fcntl
        mode = TradeMode.PAPER
        lock_file = order_gateway.STATE_DIR / f"order_state_{mode.value}.lock"
        order_gateway.STATE_DIR.mkdir(parents=True, exist_ok=True)

        with open(lock_file, "w") as f:
            # Manually acquire lock
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Now try to use _locked_state - should fail
            with self.assertRaises(RuntimeError) as cm:
                with order_gateway._locked_state(mode):
                    pass
            self.assertIn("currently locked", str(cm.exception))

            fcntl.flock(f, fcntl.LOCK_UN)

if __name__ == "__main__":
    unittest.main()
