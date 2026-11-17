import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from _load import ROOT, load

scan = load("trader-scanner", "scan")
sys.path.insert(0, str(Path(ROOT) / "chatgpt-mcp"))
import server


class TestScannerUniverseHandlingAndMCP(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="dtai-scanner-")
        self.d = self.temp_dir.name
        self.nonexistent = os.path.join(self.d, "missing_universe.txt")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_symbols_missing_universe_file(self):
        args = type("args", (), {"symbols": None, "watchlist": None, "universe": self.nonexistent,
                                 "offline": None, "limit": None})
        with self.assertRaises(scan.ScanError) as cm:
            scan.read_symbols(args)
        self.assertIn(f"no {self.nonexistent} yet", str(cm.exception))

    def test_read_symbols_empty_universe_file(self):
        empty_file = os.path.join(self.d, "empty_universe.txt")
        with open(empty_file, "w") as fh:
            fh.write("\n# comment only\n")
        args = type("args", (), {"symbols": None, "watchlist": None, "universe": empty_file,
                                 "offline": None, "limit": None})
        with self.assertRaises(scan.ScanError) as cm:
            scan.read_symbols(args)
        self.assertIn("no symbols to scan", str(cm.exception))

    def test_mcp_invalid_symbols_return_structured_input_error(self):
        result = server.scan_market(mode="daily", symbols="NOT A TICKER")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "invalid_input")
        self.assertIn("ticker", result["error"])

    def test_mcp_scanner_offline_error_does_not_use_network(self):
        result = server.run_skill("scanner", ["universe", "--offline", self.d, "--json"])
        self.assertFalse(result["ok"])
        self.assertEqual(result["scan_status"], "invalid_universe")
        self.assertIn("error", result)

    def test_daily_diagnostics_cover_each_symbol_and_expose_previous_close(self):
        fixture = os.path.join(ROOT, "tests", "fixtures", "trader-scanner", "daily-spark-2026-10-19.json")
        data, failures = scan.load_offline(fixture)
        symbols = sorted(data)
        diagnostics = []
        hits, counts, last_date = scan.scan_daily(
            data, symbols, scan.parse_now("2026-10-19 09:00"), 5, 1_000_000,
            diagnostics=diagnostics, failures=failures,
        )
        self.assertEqual(len(diagnostics), len(symbols))
        self.assertEqual(counts["requested"], len(symbols))
        self.assertIsNotNone(last_date)
        self.assertTrue(all(d["source"] == "Yahoo Finance" for d in diagnostics))
        self.assertTrue(all("rejection_reason" in d and "result" in d for d in diagnostics))
        self.assertTrue(all(d["freshness"] == "previous_session_or_older" for d in diagnostics if d["bar_date"]))
        self.assertTrue(all(d["strategy_evaluated"] for d in diagnostics if d["liquidity_pass"] and d["result"] != "insufficient_market_data"))


if __name__ == "__main__":
    unittest.main()
