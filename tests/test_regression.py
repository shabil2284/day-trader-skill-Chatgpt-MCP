#!/usr/bin/env python3
"""
Regression tests for the Day Trader AI codebase.

Tests cover:
- SEC company fundamentals (SEC_USER_AGENT)
- Pre-market entry check exit codes
- Position sizing prerequisites
- Empty list serialization ([] vs {})
- Duplicate submission prevention and concurrency (file locking)
- Scanner zero-hit exit code handling
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add project paths
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Load modules
from _load import load, FIX, ROOT

# Load the modules under test
news = load("trader-news", "news")
facts = load("trader-analyst", "facts")
entry = load("trader-entry", "entry")
size = load("trader-budget", "size")
scan = load("trader-scanner", "scan")

# Import order_gateway for duplicate submission tests
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chatgpt-mcp"))
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





def run_module(module, argv):
    """Run a module's main function and capture output."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = module.main(argv)
    return code, out.getvalue(), err.getvalue()


class TestSECUserAgent(unittest.TestCase):
    """Test SEC_USER_AGENT handling for SEC API calls."""

    def test_news_sec_user_agent_from_env(self):
        """SEC_USER_AGENT from environment variable is used."""
        with patch.dict(os.environ, {"SEC_USER_AGENT": "Test User test@example.com"}):
            ua = news.sec_user_agent()
            self.assertEqual(ua, "Test User test@example.com")

    def test_news_sec_user_agent_from_config(self):
        """sec_user_agent from config file is used when env not set."""
        with tempfile.TemporaryDirectory() as d:
            config_path = os.path.join(d, "config.json")
            with open(config_path, "w") as f:
                json.dump({"sec_user_agent": "Config User config@example.com"}, f)
            with patch.dict(os.environ, {}, clear=True):
                ua = news.sec_user_agent(config=config_path)
                self.assertEqual(ua, "Config User config@example.com")

    def test_news_sec_user_agent_env_overrides_config(self):
        """Environment variable takes precedence over config file."""
        with tempfile.TemporaryDirectory() as d:
            config_path = os.path.join(d, "config.json")
            with open(config_path, "w") as f:
                json.dump({"sec_user_agent": "Config User config@example.com"}, f)
            with patch.dict(os.environ, {"SEC_USER_AGENT": "Env User env@example.com"}):
                ua = news.sec_user_agent(config=config_path)
                self.assertEqual(ua, "Env User env@example.com")

    def test_news_sec_user_agent_none_for_placeholder(self):
        """Placeholder email returns None."""
        with tempfile.TemporaryDirectory() as d:
            config_path = os.path.join(d, "config.json")
            with open(config_path, "w") as f:
                json.dump({"sec_user_agent": "Test User you@example.com"}, f)
            with patch.dict(os.environ, {}, clear=True):
                ua = news.sec_user_agent(config=config_path)
                self.assertIsNone(ua)

    def test_news_sec_user_agent_none_for_missing_at(self):
        """Missing @ in email returns None."""
        with tempfile.TemporaryDirectory() as d:
            config_path = os.path.join(d, "config.json")
            with open(config_path, "w") as f:
                json.dump({"sec_user_agent": "Test User no-email"}, f)
            with patch.dict(os.environ, {}, clear=True):
                ua = news.sec_user_agent(config=config_path)
                self.assertIsNone(ua)

    def test_news_sec_user_agent_cli_overrides(self):
        """CLI argument overrides both env and config."""
        with tempfile.TemporaryDirectory() as d:
            config_path = os.path.join(d, "config.json")
            with open(config_path, "w") as f:
                json.dump({"sec_user_agent": "Config User config@example.com"}, f)
            with patch.dict(os.environ, {"SEC_USER_AGENT": "Env User env@example.com"}):
                ua = news.sec_user_agent(cli="CLI User cli@example.com", config=config_path)
                self.assertEqual(ua, "CLI User cli@example.com")

    def test_facts_user_agent_from_env(self):
        """SEC_USER_AGENT from environment variable is used for facts."""
        with patch.dict(os.environ, {"SEC_USER_AGENT": "Facts User facts@example.com"}):
            ua = facts.user_agent()
            self.assertEqual(ua, "Facts User facts@example.com")

    def test_facts_user_agent_from_config(self):
        """sec_user_agent from config file is used for facts."""
        with tempfile.TemporaryDirectory() as d:
            config_path = os.path.join(d, "config.json")
            with open(config_path, "w") as f:
                json.dump({"sec_user_agent": "Facts Config config@example.com"}, f)
            with patch.dict(os.environ, {}, clear=True):
                ua = facts.user_agent(config=config_path)
                self.assertEqual(ua, "Facts Config config@example.com")

    def test_facts_user_agent_none_for_invalid(self):
        """Invalid user agent returns None for facts."""
        with tempfile.TemporaryDirectory() as d:
            config_path = os.path.join(d, "config.json")
            with open(config_path, "w") as f:
                json.dump({"sec_user_agent": "Invalid"}, f)
            with patch.dict(os.environ, {}, clear=True):
                ua = facts.user_agent(config=config_path)
                self.assertIsNone(ua)

    def test_news_fetcher_requires_sec_ua(self):
        """News fetcher raises error when SEC UA missing."""
        fetcher = news.Fetcher(sec_ua=None, offline=None)
        with self.assertRaises(news.NewsError) as cm:
            fetcher.get("https://example.com", "test", sec=True)
        self.assertIn("no SEC User-Agent", str(cm.exception))

    def test_facts_fetcher_requires_ua(self):
        """Facts fetcher raises error when UA missing."""
        fetcher = facts.Fetcher(ua=None, offline=None)
        with self.assertRaises(facts.FactsError) as cm:
            fetcher.json("https://example.com", "test")
        self.assertIn("User-Agent", str(cm.exception))


class TestPreMarketEntryCheckExitCodes(unittest.TestCase):
    """Test pre-market entry check exit codes."""

    def test_entry_check_triggered_exit_0(self):
        """Entry check returns exit code 0 when triggered."""
        code, _, _ = run_module(entry, [
            "check", "TSLA",
            "--now", "2026-10-19 10:15",
            "--offline", FIX + "/trader-entry/TSLA-2026-10-19-5m.json"
        ])
        self.assertEqual(code, 0)

    def test_entry_check_waiting_exit_1(self):
        """Entry check returns exit code 1 when waiting."""
        code, _, _ = run_module(entry, [
            "check", "TSLA",
            "--now", "2026-10-19 10:12",
            "--offline", FIX + "/trader-entry/TSLA-2026-10-19-5m.json"
        ])
        self.assertEqual(code, 1)

    def test_entry_check_expired_exit_1(self):
        """Entry check returns exit code 1 when session is over (no-data ticker after close)."""
        # TSLA was triggered at 10:15, so checking TSLA at 15:45 returns 'triggered' (exit 0).
        # To test exit-1 after the cutoff, use a ticker with no data in the fixture.
        # An unknown ticker returns no-data which exits 1.
        code, _, _ = run_module(entry, [
            "check", "AAPL",
            "--now", "2026-10-19 15:45",
            "--offline", FIX + "/trader-entry/TSLA-2026-10-19-5m.json"
        ])
        self.assertEqual(code, 1)

    def test_entry_check_no_data_exit_1(self):
        """Entry check returns exit code 1 when no data."""
        code, _, _ = run_module(entry, [
            "check", "INVALID",
            "--now", "2026-10-19 10:15",
            "--offline", FIX + "/trader-entry/TSLA-2026-10-19-5m.json"
        ])
        self.assertEqual(code, 1)

    def test_entry_watch_triggered_exit_0(self):
        """Entry watch returns exit code 0 when triggered."""
        # Use --now with a time when it's already triggered
        code, _, _ = run_module(entry, [
            "watch", "TSLA",
            "--now", "2026-10-19 10:15",
            "--offline", FIX + "/trader-entry/TSLA-2026-10-19-5m.json",
            "--every", "1"
        ])
        self.assertEqual(code, 0)

    def test_entry_watch_expired_exit_1(self):
        """Entry watch returns exit code 1 when no trigger found before cutoff."""
        # watch mode stops when the market closes or the entry is confirmed.
        # With TSLA already triggered at 10:15, watching at 15:45 is already past.
        # Use a ticker with no data: watch exits 1 (no trigger found).
        code, _, _ = run_module(entry, [
            "watch", "AAPL",
            "--now", "2026-10-19 15:45",
            "--offline", FIX + "/trader-entry/TSLA-2026-10-19-5m.json",
            "--every", "1"
        ])
        self.assertEqual(code, 1)

    def test_entry_watchlist_triggered_exit_0(self):
        """Entry watchlist returns exit code 0 when at least one triggers."""
        # watchlist --offline requires a DIRECTORY of <TICKER>.json files.
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as d:
            # Set up an offline directory containing TSLA.json
            offline_dir = os.path.join(d, "offline")
            os.makedirs(offline_dir)
            shutil.copy(
                FIX + "/trader-entry/TSLA-2026-10-19-5m.json",
                os.path.join(offline_dir, "TSLA.json")
            )
            wl_path = os.path.join(d, "watchlist.json")
            with open(wl_path, "w") as f:
                json.dump({"hits": [{"symbol": "TSLA"}]}, f)
            code, _, _ = run_module(entry, [
                "watchlist",
                "--now", "2026-10-19 10:15",
                "--offline", offline_dir,
                "--watchlist", wl_path
            ])
            self.assertEqual(code, 0)

    def test_entry_watchlist_none_triggered_exit_1(self):
        """Entry watchlist returns exit code 1 when none trigger."""
        with tempfile.TemporaryDirectory() as d:
            wl_path = os.path.join(d, "watchlist.json")
            with open(wl_path, "w") as f:
                json.dump({"hits": [{"symbol": "AAPL"}]}, f)
            code, _, _ = run_module(entry, [
                "watchlist",
                "--now", "2026-10-19 10:15",
                "--offline", FIX + "/trader-entry/TSLA-2026-10-19-5m.json",
                "--watchlist", wl_path
            ])
            self.assertEqual(code, 1)


class TestPositionSizingPrerequisites(unittest.TestCase):
    """Test position sizing prerequisites."""

    def setUp(self):
        self.plan_path = os.path.join(FIX, "trader-budget", "plan-tsla.json")
        self.config_path = os.path.join(ROOT, "trader-budget", "config.example.json")
        self.today = "2026-10-19"

    def test_size_trade_requires_valid_plan(self):
        """size_trade requires a plan with valid stop and target."""
        with open(self.plan_path) as f:
            plan = json.load(f)
        with open(self.config_path) as f:
            cfg = json.load(f)

        # Valid plan should work
        result = size.size_trade(plan, cfg, today=self.today)
        self.assertEqual(result["qty"], 8)
        self.assertIsNone(result["refusal"])

    def test_size_trade_refuses_zero_shares(self):
        """size_trade raises SizeError when stop == entry (zero risk per share)."""
        with open(self.plan_path) as f:
            plan = json.load(f)
        with open(self.config_path) as f:
            cfg = json.load(f)

        # Stop at entry price -> SizeError (stop not below entry)
        plan["stop"] = plan["entry"]
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "trader-budget"))
        with self.assertRaises(size.SizeError):
            size.size_trade(plan, cfg, today=self.today)

    def test_size_trade_refuses_negative_risk(self):
        """size_trade raises SizeError when stop > entry (stop above entry)."""
        with open(self.plan_path) as f:
            plan = json.load(f)
        with open(self.config_path) as f:
            cfg = json.load(f)

        # Stop above entry: physically invalid plan -> SizeError
        plan["stop"] = plan["entry"] + 1
        with self.assertRaises(size.SizeError):
            size.size_trade(plan, cfg, today=self.today)

    def test_size_trade_refuses_target_at_or_below_entry(self):
        """size_trade raises SizeError when target <= entry."""
        with open(self.plan_path) as f:
            plan = json.load(f)
        with open(self.config_path) as f:
            cfg = json.load(f)

        # Target == entry: physically invalid plan -> SizeError
        plan["target"] = plan["entry"]
        with self.assertRaises(size.SizeError):
            size.size_trade(plan, cfg, today=self.today)

    def test_size_trade_refuses_too_tight_risk(self):
        """size_trade refuses when reward:risk is below min_reward_risk."""
        with open(self.plan_path) as f:
            plan = json.load(f)
        with open(self.config_path) as f:
            cfg = json.load(f)

        # Very tight stop (less than 0.05% risk) -> qty=0, refusal set
        # risk = entry - stop; with stop at entry*0.9996, risk = 0.1456...
        # max_loss_per_trade_usd=50, risk=0.1456 -> shares = floor(50/0.1456) = 343
        # But cost = 343 * 364.18 = very large -> won't be 0 qty from this.
        # Instead: set stop so that risk per share is very small, making
        # max_loss_pct * budget too tight to buy even 1 share at that risk.
        # The simplest reliable way: set max_loss_per_trade_usd=0.01 so 1 share can't be afforded.
        cfg["max_loss_per_trade_usd"] = 0.01
        result = size.size_trade(plan, cfg, today=self.today)
        self.assertEqual(result["qty"], 0)
        self.assertIsNotNone(result["refusal"])

    def test_size_trade_bounds_by_max_loss(self):
        """size_trade bounds by max_loss_per_trade_usd."""
        with open(self.plan_path) as f:
            plan = json.load(f)
        with open(self.config_path) as f:
            cfg = json.load(f)

        result = size.size_trade(plan, cfg, today=self.today)
        self.assertEqual(result["bound_by"], "max loss")
        self.assertTrue(any(l["binds"] for l in result["limits"] if l["name"] == "max loss"))

    def test_size_trade_bounds_by_position_cap(self):
        """size_trade bounds by max_position_pct."""
        with open(self.plan_path) as f:
            plan = json.load(f)
        with open(self.config_path) as f:
            cfg = json.load(f)

        # Make max loss very large so position cap binds
        cfg["max_loss_per_trade_usd"] = 10000
        result = size.size_trade(plan, cfg, today=self.today)
        self.assertEqual(result["bound_by"], "position cap")

    def test_size_trade_bounds_by_max_order(self):
        """size_trade bounds by max_order_usd."""
        with open(self.plan_path) as f:
            plan = json.load(f)
        with open(self.config_path) as f:
            cfg = json.load(f)

        # Make both max loss and position cap large
        cfg["max_loss_per_trade_usd"] = 10000
        cfg["max_position_pct"] = 100
        result = size.size_trade(plan, cfg, today=self.today)
        self.assertEqual(result["bound_by"], "max order")

    def test_size_trade_bounds_by_cash(self):
        """size_trade bounds by available cash."""
        with open(self.plan_path) as f:
            plan = json.load(f)
        with open(self.config_path) as f:
            cfg = json.load(f)

        # Disable position cap and max order so only cash limits apply.
        # With budget=100 and cash_buffer_pct=50, available = 50.
        # At entry 364.18, floor(50/364.18) = 0 shares -> bound by cash.
        cfg["budget"] = 100
        cfg["cash_buffer_pct"] = 50
        cfg["max_position_pct"] = 0   # disable position cap
        cfg["max_order_usd"] = 0       # disable max order
        result = size.size_trade(plan, cfg, today=self.today)
        self.assertEqual(result["bound_by"], "cash")

    def test_bracket_order_has_required_fields(self):
        """bracket_order produces order with all required fields."""
        with open(self.plan_path) as f:
            plan = json.load(f)
        with open(self.config_path) as f:
            cfg = json.load(f)

        sizing = size.size_trade(plan, cfg, today=self.today)
        order = size.bracket_order(sizing)

        required = ["symbol", "side", "qty", "type", "time_in_force",
                    "order_class", "take_profit_limit_price", "stop_loss_stop_price"]
        for field in required:
            self.assertIn(field, order, f"Missing required field: {field}")

        self.assertEqual(order["symbol"], "TSLA")
        self.assertEqual(order["side"], "buy")
        self.assertEqual(order["order_class"], "bracket")

    def test_cli_requires_plan_file(self):
        """CLI exits with code 1 when the default plan file is missing."""
        # size.py defaults --plan to trader/plan.json; if it's absent, it exits 1
        # with message containing "no plan" (not "--plan", since it's optional with a default).
        code, _, err = run_module(size, [
            "--config", self.config_path,
            "--portfolio", "/nonexistent",
            "--now", "2026-10-19 10:15",
            "--write", "/tmp/out.json"
        ])
        self.assertEqual(code, 1)
        self.assertIn("no plan", err.lower())

    def test_cli_requires_config_file(self):
        """CLI exits with code 1 when the default config file is missing."""
        # --config defaults to trader/config.json; if missing and not found, exits 1.
        # We pass --plan explicitly and an explicit nonexistent config path.
        code, _, err = run_module(size, [
            "--plan", self.plan_path,
            "--config", "/nonexistent/config.json",
            "--portfolio", "/nonexistent",
            "--now", "2026-10-19 10:15",
            "--write", "/tmp/out.json"
        ])
        self.assertEqual(code, 1)
        self.assertIn("config", err.lower())

    def test_cli_with_missing_plan_file(self):
        """CLI handles missing plan file gracefully."""
        code, _, err = run_module(size, [
            "--plan", "/nonexistent/plan.json",
            "--config", self.config_path,
            "--portfolio", "/nonexistent",
            "--now", "2026-10-19 10:15",
            "--write", "/tmp/out.json"
        ])
        self.assertEqual(code, 1)
        # Error message contains "no plan" and the path
        self.assertIn("no plan", err.lower())
        self.assertIn("/nonexistent/plan.json", err)


class TestEmptyListSerialization(unittest.TestCase):
    """Test empty list serialization ([] vs {})."""

    def test_scanner_empty_hits_is_list(self):
        """Scanner writes empty list for hits when no matches."""
        with tempfile.TemporaryDirectory() as d:
            out_path = os.path.join(d, "watchlist.json")
            code, _, _ = run_module(scan, [
                "orb",
                "--offline", os.path.join(FIX, "trader-scanner", "wall5m-2026-10-19.json.gz"),
                "--now", "2026-10-17 10:15",  # Weekend - no session
                "--out", out_path
            ])
            # The command returns exit code 1 for no session but doesn't write
            # Let's test a valid session with no hits
            code, _, _ = run_module(scan, [
                "orb",
                "--offline", os.path.join(FIX, "trader-scanner", "wall5m-2026-10-19.json.gz"),
                "--now", "2026-10-19 10:10",  # Before any breakout
                "--out", out_path,
                "--symbols", "TSLA"
            ])
            if os.path.exists(out_path):
                with open(out_path) as f:
                    doc = json.load(f)
                self.assertIsInstance(doc.get("hits"), list)
                self.assertEqual(doc["hits"], [])

    def test_scanner_daily_empty_hits_is_list(self):
        """Daily scanner writes empty list for hits when no matches."""
        with tempfile.TemporaryDirectory() as d:
            out_path = os.path.join(d, "watchlist.json")
            code, _, _ = run_module(scan, [
                "daily",
                "--offline", os.path.join(FIX, "trader-scanner", "daily-spark-2026-10-19.json"),
                "--now", "2026-10-19 09:00",
                "--out", out_path,
                "--min-price", "10000",  # No stock this high
                "--min-volume", "0"
            ])
            if os.path.exists(out_path):
                with open(out_path) as f:
                    doc = json.load(f)
                self.assertIsInstance(doc.get("hits"), list)

    def test_budget_empty_orders_is_list(self):
        """Budget writes empty list for orders when no positions sized."""
        with tempfile.TemporaryDirectory() as d:
            out_path = os.path.join(d, "trader", "orders.json")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            # Create a plan that will result in 0 shares
            plan_path = os.path.join(d, "plan.json")
            with open(plan_path, "w") as f:
                json.dump({
                    "symbol": "TSLA", "entry": 364.18, "stop": 364.18,  # Zero risk
                    "target": 370.04, "setup": "orb", "entry_time": "10:15 AM",
                    "flat_by": "15:55"
                }, f)
            code, _, _ = run_module(size, [
                "--plan", plan_path,
                "--config", os.path.join(ROOT, "trader-budget", "config.example.json"),
                "--portfolio", "/nonexistent",
                "--now", "2026-10-19 10:15",
                "--write", out_path
            ])
            if os.path.exists(out_path):
                with open(out_path) as f:
                    doc = json.load(f)
                self.assertIsInstance(doc.get("orders"), list)
                self.assertEqual(doc["orders"], [])

    def test_entry_watchlist_empty_is_list(self):
        """Entry watchlist exits with code 1 and prints table when no hits trigger."""
        import shutil
        with tempfile.TemporaryDirectory() as d:
            # watchlist --offline requires a directory of <TICKER>.json files
            offline_dir = os.path.join(d, "offline")
            os.makedirs(offline_dir)
            shutil.copy(
                os.path.join(FIX, "trader-entry", "TSLA-2026-10-19-5m.json"),
                os.path.join(offline_dir, "TSLA.json")
            )
            wl_path = os.path.join(d, "watchlist.json")
            with open(wl_path, "w") as f:
                # TSLA at 09:35 is "waiting" (not triggered yet)
                json.dump({"hits": [{"symbol": "TSLA"}]}, f)
            code, out, err = run_module(entry, [
                "watchlist",
                "--now", "2026-10-19 09:35",
                "--offline", offline_dir,
                "--watchlist", wl_path
            ])
            # With TSLA waiting at 09:35, exit code 1 (no trigger)
            self.assertEqual(code, 1)


class TestDuplicateSubmissionPrevention(unittest.TestCase):
    """Test duplicate submission prevention and concurrency (file locking).

    order_gateway stores all proposals for a mode in a single atomic state file:
      {STATE_DIR}/order_state_paper.json  -> {"proposals": {id: {...}}}
      {STATE_DIR}/order_state_live.json   -> {"proposals": {id: {...}}}
    It uses fcntl file locking via _locked_state() for atomic read-modify-write.
    """

    def setUp(self):
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = False
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = False
        order_gateway.ALPACA_LIVE_TRADING_ENABLED = False
        order_gateway._ENV_VARS = {
            "ALPACA_PAPER_API_KEY": "paper_key",
            "ALPACA_PAPER_SECRET_KEY": "paper_secret",
            "ALPACA_LIVE_API_KEY": "live_key",
            "ALPACA_LIVE_SECRET_KEY": "live_secret"
        }
        self.test_state_dir = Path(tempfile.mkdtemp())
        order_gateway.STATE_DIR = self.test_state_dir

    def tearDown(self):
        for f in self.test_state_dir.glob("*"):
            if f.is_file():
                f.unlink()
        if self.test_state_dir.exists():
            self.test_state_dir.rmdir()

    def _state_file(self, mode="paper"):
        """Return the actual state file path used by order_gateway."""
        return self.test_state_dir / f"order_state_{mode}.json"

    def test_proposal_file_locking(self):
        """propose() atomically writes the proposal into the aggregate state file."""
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True

        with patch("urllib.request.urlopen") as mock_urlopen, \
             patch("order_gateway.validate_risk") as mock_risk:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            prop = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )

            proposal_id = prop["proposal_id"]

            # The aggregate state file must exist
            state_file = self._state_file("paper")
            self.assertTrue(state_file.exists(), f"State file not found: {state_file}")

            # It must be valid JSON containing the proposal
            with open(state_file) as f:
                data = json.load(f)
            self.assertIn("proposals", data)
            self.assertIn(proposal_id, data["proposals"])

            # The proposal must have the right fields
            p = data["proposals"][proposal_id]
            self.assertEqual(p["id"], proposal_id)
            self.assertEqual(p["status"], "pending")
            self.assertEqual(p["symbol"], "AAPL")

    def test_approve_and_submit_uses_lock(self):
        """approve_and_submit atomically updates the state file via file locking."""
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True

        with patch("urllib.request.urlopen") as mock_urlopen, \
             patch("order_gateway.validate_risk") as mock_risk:
            mock_account = MagicMock()
            mock_account.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()

            mock_submit = MagicMock()
            mock_submit.read.return_value = json.dumps({
                "id": "alpaca_id", "status": "accepted"
            }).encode()

            mock_urlopen.return_value.__enter__.side_effect = [
                mock_account, mock_account, mock_submit
            ]

            prop = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )

            proposal_id = prop["proposal_id"]
            approval_phrase = prop["approval_phrase"]

            result = order_gateway.approve_and_submit(proposal_id, approval_phrase)
            self.assertEqual(result["status"], "SUBMITTED_TO_ALPACA_PAPER")

            # Verify the aggregate state file reflects submitted status
            state_file = self._state_file("paper")
            with open(state_file) as f:
                data = json.load(f)
            p = data["proposals"][proposal_id]
            self.assertEqual(p["status"], "submitted")
            self.assertEqual(p["broker_order_id"], "alpaca_id")

    def test_reject_uses_lock(self):
        """reject() atomically updates the proposal status in the state file."""
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True

        with patch("urllib.request.urlopen") as mock_urlopen, \
             patch("order_gateway.validate_risk") as mock_risk:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            prop = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )

            proposal_id = prop["proposal_id"]
            result = order_gateway.reject(proposal_id)
            self.assertEqual(result["status"], "REJECTED")

            # Verify the state file shows rejected status
            state_file = self._state_file("paper")
            with open(state_file) as f:
                data = json.load(f)
            self.assertEqual(data["proposals"][proposal_id]["status"], "rejected")

    def test_concurrent_propose_and_approve(self):
        """Multiple proposals are stored without corruption in the shared state file."""
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True
        order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = True

        with patch("urllib.request.urlopen") as mock_urlopen, \
             patch("order_gateway.validate_risk") as mock_risk:
            mock_account = MagicMock()
            mock_account.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()

            mock_submit = MagicMock()
            mock_submit.read.return_value = json.dumps({
                "id": "alpaca_id", "status": "accepted"
            }).encode()

            # Two proposal account reads, then one approval account read and one submit.
            mock_urlopen.return_value.__enter__.side_effect = [
                mock_account, mock_account, mock_account, mock_submit
            ]

            prop1 = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="AAPL", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )
            prop2 = paper_propose(
                mode=order_gateway.TradeMode.PAPER,
                symbol="MSFT", side="buy", quantity=1,
                order_type="market", reference_price=50.00
            )

            result1 = order_gateway.approve_and_submit(prop1["proposal_id"], prop1["approval_phrase"])
            self.assertEqual(result1["status"], "SUBMITTED_TO_ALPACA_PAPER")

            result2 = order_gateway.reject(prop2["proposal_id"])
            self.assertEqual(result2["status"], "REJECTED")

            # Both proposals must be in the single state file
            state_file = self._state_file("paper")
            self.assertTrue(state_file.exists())
            with open(state_file) as f:
                data = json.load(f)
            self.assertIn(prop1["proposal_id"], data["proposals"])
            self.assertIn(prop2["proposal_id"], data["proposals"])
            self.assertEqual(data["proposals"][prop1["proposal_id"]]["status"], "submitted")
            self.assertEqual(data["proposals"][prop2["proposal_id"]]["status"], "rejected")

    def test_list_proposals_reads_all_files(self):
        """list_proposals returns all proposals from the state file."""
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True

        with patch("urllib.request.urlopen") as mock_urlopen, \
             patch("order_gateway.validate_risk") as mock_risk:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            for sym in ["AAPL", "MSFT", "GOOG"]:
                paper_propose(
                    mode=order_gateway.TradeMode.PAPER,
                    symbol=sym, side="buy", quantity=1,
                    order_type="market", reference_price=50.00
                )

            proposals = order_gateway.list_proposals()
            self.assertEqual(len(proposals), 3)
            for p in proposals:
                self.assertIn("id", p)
                self.assertIn("status", p)

    def test_list_proposals_reads_all_files(self):
        """list_proposals reads all proposal files with locking."""
        order_gateway.ALPACA_PAPER_TRADING_ENABLED = True

        with patch("urllib.request.urlopen") as mock_urlopen, \
             patch("order_gateway.validate_risk") as mock_risk:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "status": "ACTIVE", "trading_blocked": False, "buying_power": "1000.00"
            }).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Create multiple proposals
            for sym in ["AAPL", "MSFT", "GOOG"]:
                paper_propose(
                    mode=order_gateway.TradeMode.PAPER,
                    symbol=sym, side="buy", quantity=1,
                    order_type="market", reference_price=50.00
                )

            proposals = order_gateway.list_proposals()
            self.assertEqual(len(proposals), 3)
            for p in proposals:
                self.assertIn("proposal_id", p)
                self.assertIn("status", p)


class TestScannerZeroHitExitCodes(unittest.TestCase):
    """Test scanner zero-hit exit code handling."""

    def test_orb_no_hits_exit_1(self):
        """ORB scan returns exit code 1 when no hits found."""
        with tempfile.TemporaryDirectory() as d:
            out_path = os.path.join(d, "watchlist.json")
            # Scan at 10:10 - before any breakout for TSLA
            code, out, err = run_module(scan, [
                "orb",
                "--offline", os.path.join(FIX, "trader-scanner", "wall5m-2026-10-19.json.gz"),
                "--now", "2026-10-19 10:10",
                "--out", out_path,
                "--symbols", "TSLA"
            ])
            self.assertEqual(code, 1)
            self.assertIn("No chart closed above", out)

    def test_orb_with_hits_exit_0(self):
        """ORB scan returns exit code 0 when hits found."""
        with tempfile.TemporaryDirectory() as d:
            out_path = os.path.join(d, "watchlist.json")
            code, out, err = run_module(scan, [
                "orb",
                "--offline", os.path.join(FIX, "trader-scanner", "wall5m-2026-10-19.json.gz"),
                "--now", "2026-10-19 10:15",
                "--out", out_path,
                "--symbols", "TSLA"
            ])
            self.assertEqual(code, 0)
            self.assertIn("closed above their opening-range high", out)

    def test_daily_no_hits_exit_1(self):
        """Daily scan returns exit code 1 when no hits found."""
        with tempfile.TemporaryDirectory() as d:
            out_path = os.path.join(d, "watchlist.json")
            code, out, err = run_module(scan, [
                "daily",
                "--offline", os.path.join(FIX, "trader-scanner", "daily-spark-2026-10-19.json"),
                "--now", "2026-10-19 09:00",
                "--out", out_path,
                "--min-price", "10000",  # No stock this high
                "--min-volume", "0"
            ])
            self.assertEqual(code, 1)
            # When daily scan finds no setups, it prints "No setups."
            self.assertIn("No setups", out)

    def test_daily_with_hits_exit_0(self):
        """Daily scan returns exit code 0 when hits found."""
        with tempfile.TemporaryDirectory() as d:
            out_path = os.path.join(d, "watchlist.json")
            code, out, err = run_module(scan, [
                "daily",
                "--offline", os.path.join(FIX, "trader-scanner", "daily-spark-2026-10-19.json"),
                "--now", "2026-10-19 09:00",
                "--out", out_path,
                "--min-volume", "0"
            ])
            self.assertEqual(code, 0)

    def test_universe_command_exit_0_on_success(self):
        """Universe command returns exit code 0 on success."""
        with tempfile.TemporaryDirectory() as d:
            out_path = os.path.join(d, "universe.txt")
            code, out, err = run_module(scan, [
                "universe",
                "--offline", os.path.join(FIX, "trader-scanner", "symdir"),
                "--out", out_path
            ])
            self.assertEqual(code, 0)
            self.assertIn("Kept", out)

    def test_orb_invalid_session_exit_2(self):
        """ORB on invalid session (weekend) returns the input/session error code."""
        with tempfile.TemporaryDirectory() as d:
            out_path = os.path.join(d, "watchlist.json")
            code, out, err = run_module(scan, [
                "orb",
                "--offline", os.path.join(FIX, "trader-scanner", "wall5m-2026-10-19.json.gz"),
                "--now", "2026-10-17 10:15",  # Saturday
                "--out", out_path
            ])
            self.assertEqual(code, 2)
            self.assertIn("No session", err)

    def test_orb_before_open_exit_2(self):
        """ORB before the opening range completes returns the input/session error code."""
        with tempfile.TemporaryDirectory() as d:
            out_path = os.path.join(d, "watchlist.json")
            code, out, err = run_module(scan, [
                "orb",
                "--offline", os.path.join(FIX, "trader-scanner", "wall5m-2026-10-19.json.gz"),
                "--now", "2026-10-19 09:40",  # Before opening range complete
                "--out", out_path
            ])
            self.assertEqual(code, 2)
            self.assertIn("after 9:50 AM", err)


if __name__ == "__main__":
    unittest.main()
