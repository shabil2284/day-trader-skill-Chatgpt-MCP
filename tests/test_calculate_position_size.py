import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "chatgpt-mcp"))

import server
from server import calculate_position_size


def setup_test_environment():
    test_dir = tempfile.mkdtemp(prefix="dtai-position-size-")
    trader_dir = Path(test_dir) / "trader"
    trader_dir.mkdir(parents=True)
    plan = {
        "symbol": "TSLA", "entry": 364.18, "stop": 358.32, "target": 370.04,
        "setup": "orb", "entry_time": "10:15 AM", "flat_by": "15:55",
        "or_high": 362.18, "or_low": 354.47,
    }
    config = {
        "budget": 5000, "cash_buffer_pct": 10, "max_position_pct": 75,
        "max_order_usd": 4000, "min_order_usd": 5,
        "max_loss_per_trade_usd": 50, "max_daily_loss_usd": 150,
        "max_trades_per_day": 3, "max_orders_per_day": 10,
        "min_reward_risk": 1.0, "require_stop": True,
        "no_entries_before": "09:45", "no_entries_after": "15:30",
        "flat_by": "15:55", "fractional": False, "broker": "alpaca",
        "paper": True, "blocked": [],
    }
    (trader_dir / "plan.json").write_text(json.dumps(plan))
    (trader_dir / "config.json").write_text(json.dumps(config))
    return test_dir


def test_missing_plan_json():
    test_dir = setup_test_environment()
    original_root, original_cwd = server.ROOT, os.getcwd()
    try:
        (Path(test_dir) / "trader" / "plan.json").unlink()
        server.ROOT = Path(test_dir)
        result = calculate_position_size(budget=5000)
        assert result.get("ok") is False
        assert result.get("error_type") == "missing_prerequisite"
        assert "Missing required trade plan" in result.get("error", "")
    finally:
        server.ROOT = original_root
        os.chdir(original_cwd)
        shutil.rmtree(test_dir)


def test_existing_and_explicit_plans_are_sized_without_persistent_writes():
    test_dir = setup_test_environment()
    original_root, original_cwd = server.ROOT, os.getcwd()
    plan_path = Path(test_dir) / "trader" / "plan.json"
    original_plan = plan_path.read_text()
    try:
        server.ROOT = Path(test_dir)
        os.chdir(test_dir)

        existing = calculate_position_size(budget=5000)
        assert existing.get("ok") is True, existing

        explicit = calculate_position_size(
            budget=5000, symbol="TSLA", entry=364.18, stop=358.32,
            target=370.04, opening_high=362.18, opening_low=354.47,
        )
        assert explicit.get("ok") is True, explicit
        assert plan_path.read_text() == original_plan
        assert not (Path(test_dir) / "trader" / "orders.json").exists()
    finally:
        server.ROOT = original_root
        os.chdir(original_cwd)
        shutil.rmtree(test_dir)
