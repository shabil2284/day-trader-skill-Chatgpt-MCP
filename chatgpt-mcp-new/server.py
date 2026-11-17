import json
import os
import re
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
NEW_DIR = Path(__file__).resolve().parent

mcp = FastMCP(
    "Day Trader AI - Read Only",
    instructions=(
        "Read-only US stock market research assistant. "
        "Never place, approve, reject, modify, or cancel orders. "
        "Clearly identify delayed market data."
    ),
    host="127.0.0.1",
    port=8000,
    streamable_http_path="/mcp",
)

SCRIPTS = {
    "scanner": ROOT / "trader-scanner/scan.py",
    "news": ROOT / "trader-news/news.py",
    "entry": ROOT / "trader-entry/entry.py",
    "risk": ROOT / "trader-risk/check.py",
    "alerts": ROOT / "trader-alerts/alerts.py",
    "broker": ROOT / "trader-broker/ticket.py",
    "analyst": ROOT / "trader-analyst/facts.py",
    "exit": ROOT / "trader-exit/exit.py",
}

def run_readonly(name, args, timeout=90):
    if name not in SCRIPTS:
        return {"ok": False, "error": "Unknown skill"}

    script = SCRIPTS[name]
    if not script.is_file():
        return {"ok": False, "error": f"Script not found: {name}"}

    forbidden = {
        "--write", "approve", "decline", "result", "fill",
        "flatten", "reset", "add", "plan",
        "place_order", "place_stock_order",
        "cancel_order", "cancel_all_orders",
    }

    if any(a in forbidden or a.startswith("--write=") for a in args):
        return {"ok": False, "error": "Read-only safety guard blocked this command"}

    try:
        result = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "SEC_USER_AGENT": "TradingBot [Your Name] you@example.com"},
        )
        output = result.stdout.strip()
        try:
            output = json.loads(output) if output else None
        except json.JSONDecodeError:
            pass

        return {
            "ok": result.returncode == 0,
            "skill": name,
            "exit_code": result.returncode,
            "result": output,
            "error": result.stderr.strip()[:1500] or None,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"{name} timed out"}

def validate_symbols(symbols):
    if not isinstance(symbols, str) or not symbols.strip():
        raise ValueError("Provide symbols such as AAPL,MSFT")
    items = [s.strip().upper() for s in symbols.split(",")]
    if len(items) > 20 or any(not re.fullmatch(r"[A-Z0-9.-]{1,15}", s) for s in items):
        raise ValueError("Use up to 20 valid comma-separated ticker symbols")
    return ",".join(items)

@mcp.tool()
def server_status():
    """Check the new MCP server and its safety configuration."""
    return {
        "server": "Day Trader AI - Read Only",
        "status": "running",
        "market": "US equities",
        "order_submission": False,
        "approval_tools": False,
        "live_trading_tools": False,
        "transport": "Streamable HTTP",
        "endpoint": "http://127.0.0.1:8000/mcp",
    }

@mcp.tool()
def get_market_clock():
    """Get the NYSE market clock and session status."""
    return run_readonly("alerts", ["clock", "--json"])

@mcp.tool()
def get_quotes(symbols: str):
    """Get delayed Yahoo Finance quotes. Not suitable for order execution."""
    tickers = validate_symbols(symbols)
    return run_readonly("alerts", ["quote", *tickers.split(",") , "--json"])

@mcp.tool()
def scan_daily(symbols: str, limit: int = 10):
    """Run a read-only daily stock setup scan."""
    tickers = validate_symbols(symbols)
    if not 1 <= limit <= 20:
        raise ValueError("Limit must be between 1 and 20")
    return run_readonly(
        "scanner",
        ["daily", "--symbols", tickers, "--limit", str(limit),
         "--no-write", "--json"],
        timeout=180,
    )

@mcp.tool()
def scan_opening_range(symbols: str, limit: int = 10):
    """Run a read-only opening-range breakout scan."""
    tickers = validate_symbols(symbols)
    if not 1 <= limit <= 20:
        raise ValueError("Limit must be between 1 and 20")
    return run_readonly(
        "scanner",
        ["orb", "--symbols", tickers, "--limit", str(limit),
         "--no-write", "--json"],
        timeout=180,
    )

@mcp.tool()
def check_entry(symbol: str):
    """Check an entry setup without writing an entry file."""
    ticker = validate_symbols(symbol)
    if "," in ticker:
        raise ValueError("Provide one ticker")
    return run_readonly("entry", ["check", ticker, "--json"])

@mcp.tool()
def check_risk():
    """Evaluate existing proposed orders without writing risk verdicts."""
    return run_readonly("risk", ["--no-write", "--json"])

@mcp.tool()
def get_news(symbols: str):
    """Retrieve news for specified US stock symbols without updating state."""
    tickers = validate_symbols(symbols)
    return run_readonly(
        "news", ["--tickers", *tickers.split(","), "--dry-run", "--json"]
    )

@mcp.tool()
def get_existing_tickets():
    """Display existing proposed order tickets. Does not approve or submit them."""
    return run_readonly("broker", ["show", "--json"])

@mcp.tool()
def get_decision_log():
    """Read the existing broker decision log."""
    return run_readonly("broker", ["log", "--all"])

@mcp.tool()
def get_exit_plan():
    """Display the current exit plan without changing it."""
    return run_readonly("exit", ["show", "--json"])

@mcp.tool()
def get_company_fundamentals(symbols: str):
    """Retrieve company fundamentals for specified symbols."""
    tickers = validate_symbols(symbols)
    return run_readonly("analyst", [*tickers.split(","), "--json"], timeout=120)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
