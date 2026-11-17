import json
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
import order_gateway
from order_gateway import TradeMode

mcp = FastMCP(
    "Day Trader AI",
    transport_security=TransportSecuritySettings(
        allowed_hosts=[
            "analysis-mcp:8000",
            "analysis-mcp:*",
            "localhost:*",
            "127.0.0.1:*",
        ]
    ),
)

ROOT = Path(__file__).resolve().parents[1]

SKILLS = {
    "scanner": ROOT / "trader-scanner" / "scan.py",
    "news": ROOT / "trader-news" / "news.py",
    "entry": ROOT / "trader-entry" / "entry.py",
    "exit": ROOT / "trader-exit" / "exit.py",
    "timemachine": ROOT / "trader-timemachine" / "timemachine.py",
    "risk": ROOT / "trader-risk" / "check.py",
    "budget": ROOT / "trader-budget" / "size.py",
    "broker": ROOT / "trader-broker" / "ticket.py",
    "alerts": ROOT / "trader-alerts" / "alerts.py",
    "analyst": ROOT / "trader-analyst" / "facts.py",
    "pelosi": ROOT / "trader-pelosi" / "ptr.py",
}


def run_skill(name, args, timeout=120, extra_env=None):
    # Only approved analysis commands may run through MCP.
    allowed_commands = {
        "scanner": {"daily", "orb", "universe"},
        "news": {"--tickers"},
        "entry": {"check"},
        "exit": {"plan"},
        "timemachine": {"run"},
        "broker": {"show"},
        "alerts": {"check"},
        "pelosi": {"index"},
    }

    if name not in SKILLS or not args:
        return {"ok": False, "error": "Skill command is not allowlisted"}

    if name in allowed_commands and args[0] not in allowed_commands[name]:
        return {"ok": False, "error": "Command is not allowlisted for this skill"}

    forbidden = {
        "--write", "approve", "decline", "result", "fill",
        "flatten", "place_order", "place_stock_order",
        "cancel_order", "cancel_all_orders", "close_all_positions",
    }

    if any(arg in forbidden or arg.startswith("--write=") for arg in args):
        # Allow --write ONLY for 'exit' skill to generate plans
        if name == "exit" and "--write" in args and "plan" in args:
             pass
        else:
             return {"ok": False, "error": "Safety guard blocked a write or order action"}

    script = SKILLS[name]
    if not script.is_file():
        return {"ok": False, "error": f"Skill script not found: {script}"}

    command = ["python3", str(script)] + args

    # Pass environment variables, especially SEC_USER_AGENT for SEC API calls
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"{name} timed out after {timeout} seconds"}

    output = result.stdout.strip()
    error = result.stderr.strip()

    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None

    if name == "scanner" and isinstance(parsed, dict) and parsed.get("scan_status"):
        scan_status = parsed["scan_status"]
        ok = scan_status in {"success_with_candidates", "success_zero_candidates", "partial"}
        response = {
            "ok": ok,
            "skill": name,
            "exit_code": result.returncode,
            "scan_status": scan_status,
            "result": parsed,
            "stderr": error or None,
        }
        if not ok:
            response["error"] = parsed.get("error") or f"Scanner could not complete: {scan_status}"
        elif scan_status == "partial":
            response["warning"] = "Scan completed with incomplete provider or confirmation data."
        return response

    if result.returncode != 0:
        # If the skill returned a non-zero exit code, it indicates an error.
        # Prioritize stderr if present, otherwise use stdout or a generic message.
        return {
            "ok": False,
            "skill": name,
            "exit_code": result.returncode,
            "error_type": "skill_error",
            "error": error or output or f"Skill '{name}' failed with exit code {result.returncode}",
        }

    return {
        "ok": True,
        "skill": name,
        "exit_code": result.returncode,
        "result": parsed if parsed is not None else output,
        "stderr": error or None,
    }


def clean_tickers(value):
    if not isinstance(value, str):
        raise ValueError("Provide ticker symbols as a comma-separated string")
    if not value:
        return []
    tickers = [item.strip().upper() for item in value.split(",") if item.strip()]
    if not tickers or any(not re.fullmatch(r"[A-Z0-9.-]{1,15}", t) for t in tickers):
        raise ValueError("Use comma-separated stock ticker symbols, such as AAPL,MSFT")
    return tickers


@mcp.tool()
def server_status():
    """Check MCP server status and trading configuration."""

    # Check if credentials are set (without exposing them)
    paper_key = order_gateway._ENV_VARS.get("ALPACA_PAPER_API_KEY") or order_gateway._ENV_VARS.get("ALPACA_API_KEY")
    live_key = order_gateway._ENV_VARS.get("ALPACA_LIVE_API_KEY")

    return {
        "server": "Day Trader AI MCP",
        "status": "running",
        "paper_account_configured": bool(paper_key),
        "live_account_configured": bool(live_key),
        "paper_trading_enabled": order_gateway.ALPACA_PAPER_TRADING_ENABLED,
        "live_trading_enabled": False,
        "live_trading_policy_enforced": True,
        "order_submission_enabled": order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED,
        "analysis_skills": len(SKILLS),
    }



@mcp.tool()
def get_account(mode: str = "paper"):
    """Read Alpaca account status and balances. Modes: paper, live. Read-only."""
    if not isinstance(mode, str):
        return {"error_type": "invalid_input", "error": "mode must be 'paper' or 'live'"}
    try:
        m = TradeMode(mode.lower())
    except ValueError:
        return {"error": f"Invalid mode: {mode}. Use 'paper' or 'live'."}

    data = order_gateway.request("GET", "/account", m)
    return {
        "status": data.get("status"),
        "currency": data.get("currency"),
        "cash": data.get("cash"),
        "portfolio_value": data.get("portfolio_value"),
        "buying_power": data.get("buying_power"),
        "trading_blocked": data.get("trading_blocked"),
        "mode": m.name.upper(),
    }


@mcp.tool()
def get_market_clock(mode: str = "paper"):
    """Read US stock market open/closed status. Modes: paper, live."""
    if not isinstance(mode, str):
        return {"error_type": "invalid_input", "error": "mode must be 'paper' or 'live'"}
    try:
        m = TradeMode(mode.lower())
    except ValueError:
        return {"error": f"Invalid mode: {mode}. Use 'paper' or 'live'."}
    return order_gateway.request("GET", "/clock", m)


@mcp.tool()
def get_positions(mode: str = "paper"):
    """Read current Alpaca positions. Modes: paper, live. Does not place orders."""
    if not isinstance(mode, str):
        return {"error_type": "invalid_input", "error": "mode must be 'paper' or 'live'"}
    try:
        m = TradeMode(mode.lower())
    except ValueError:
        return {"error": f"Invalid mode: {mode}. Use 'paper' or 'live'."}

    positions = order_gateway.request("GET", "/positions", m)

    if not isinstance(positions, list):
        raise RuntimeError(
            f"Unexpected Alpaca positions response: "
            f"expected list, got {type(positions).__name__}."
        )

    if not all(isinstance(position, dict) for position in positions):
        raise RuntimeError("Alpaca returned a malformed positions list.")

    return {
        "mode": m.name.upper(),
        "count": len(positions),
        "positions": positions,
    }


@mcp.tool()
def propose_order(mode: str, symbol: str, side: str, quantity: int, order_type: str,
                 limit_price: Optional[float] = None, reference_price: Optional[float] = None,
                 stop_loss_price: Optional[float] = None, take_profit_price: Optional[float] = None):
    """
    Propose a PAPER US stock order for human approval.
    Buy entries must use a limit price with a protective stop and take-profit bracket. Sells must reduce an existing long position.
    """
    if not isinstance(mode, str):
        return {"error_type": "invalid_input", "error": "mode must be 'paper' or 'live'"}
    try:
        m = TradeMode(mode.lower())
    except ValueError:
        return {"error": f"Invalid mode: {mode}. Use 'paper' or 'live'."}

    try:
        return order_gateway.propose(
            mode=m,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            reference_price=reference_price,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
        )
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def approve_and_submit_order(proposal_id: str, approval_phrase: str):
    """
    Submit a previously proposed order using its unique approval phrase.
    One approval authorizes exactly one order.
    """
    try:
        return order_gateway.approve_and_submit(proposal_id, approval_phrase)
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def reject_order(proposal_id: str):
    """Reject a pending order proposal."""
    try:
        return order_gateway.reject(proposal_id)
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def reconcile_order(proposal_id: str):
    """
    Reconcile an order with status 'submission_unknown'.
    Checks Alpaca to see if the order was actually received.
    """
    try:
        return order_gateway.reconcile(proposal_id)
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def list_order_proposals(mode: Optional[str] = None):
    """List pending, submitted, or expired order proposals. Optional mode filter."""
    m = None
    if mode is not None:
        if not isinstance(mode, str):
            return {"error_type": "invalid_input", "error": "mode must be 'paper' or 'live'"}
        if not mode:
            return {"error_type": "invalid_input", "error": "mode must be 'paper' or 'live'"}
        try:
            m = TradeMode(mode.lower())
        except ValueError:
            return {"error": f"Invalid mode: {mode}. Use 'paper' or 'live'."}

    proposals = order_gateway.list_proposals(m)

    if not isinstance(proposals, list):
        raise RuntimeError(
            f"Unexpected proposal response: expected list, "
            f"got {type(proposals).__name__}."
        )

    return {
        "mode": m.name.upper() if m else "ALL",
        "count": len(proposals),
        "proposals": proposals,
    }


@mcp.tool()
def scan_market(mode: str = "daily", symbols: str = "", limit: int = 25):
    """Scan US stocks using Yahoo's unofficial, delayed data. Daily/orb may initialize the symbol universe file."""
    if not isinstance(mode, str) or mode not in {"daily", "orb", "universe"}:
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input",
                "error": "mode must be daily, orb, or universe"}
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input",
                "error": "limit must be an integer between 1 and 200"}
    if not isinstance(symbols, str):
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input",
                "error": "symbols must be a comma-separated ticker string"}

    # Auto-initialize universe if missing and using a mode that needs it
    if mode != "universe" and not symbols:
        universe_path = ROOT / "trader" / "universe.txt"
        if not universe_path.exists():
            # Run universe command to generate the file
            init_res = run_skill("scanner", ["universe", "--json"], timeout=60)
            if not init_res.get("ok"):
                return {
                    "ok": False,
                    "error": "Missing trader/universe.txt and failed to auto-generate it. Run 'scan_market(mode=\"universe\")' first.",
                    "details": init_res.get("error")
                }

    args = [mode, "--no-write", "--json"]
    if mode != "universe":
        if symbols:
            try:
                tickers = clean_tickers(symbols)
            except ValueError as exc:
                return {"ok": False, "exit_code": 2, "error_type": "invalid_input", "error": str(exc)}
            args += ["--symbols", ",".join(tickers)]
        args += ["--limit", str(limit)]

    res = run_skill("scanner", args, timeout=240)

    return res


@mcp.tool()
def get_market_news(tickers: str, hours: int = 24):
    """Retrieve recent stock headlines. Dry-run mode does not update news state."""
    try:
        selected = clean_tickers(tickers)
    except ValueError as exc:
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input", "error": str(exc)}
    if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 168:
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input",
                "error": "hours must be between 1 and 168"}
    return run_skill(
        "news",
        ["--tickers", *selected, "--hours", str(hours), "--dry-run", "--json"],
        timeout=120,
    )


@mcp.tool()
def check_entry(symbol: str, setup: str = "orb"):
    """Check a ticker's entry conditions. Analysis only; does not save or trade."""
    try:
        selected = clean_tickers(symbol)
    except ValueError as exc:
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input", "error": str(exc)}
    if len(selected) != 1:
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input", "error": "Provide exactly one ticker"}
    if not isinstance(setup, str) or setup not in {"orb", "level"}:
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input", "error": "setup must be orb or level"}
    return run_skill("entry", ["check", selected[0], "--setup", setup, "--json"])


@mcp.tool()
def plan_exit(symbol: str = "", entry: float = 0, opening_high: float = 0,
              opening_low: float = 0):
    """Calculate an exit plan. Without inputs, reads the existing entry file. No writes."""
    args = ["plan", "--json"]
    if symbol or entry or opening_high or opening_low:
        try:
            selected = clean_tickers(symbol)
            prices = (entry, opening_high, opening_low)
            prices_valid = all(
                isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(float(value)) and value > 0 for value in prices
            )
        except (TypeError, ValueError, OverflowError):
            selected, prices_valid = [], False
        if len(selected) != 1 or not prices_valid:
            return {
                "ok": False,
                "exit_code": 2,
                "error_type": "invalid_input",
                "error": "Provide symbol, entry, opening_high and opening_low together, all positive",
            }
        if opening_high <= opening_low:
            return {"ok": False, "exit_code": 2, "error_type": "invalid_input",
                    "error": "opening_high must exceed opening_low"}
        args += [
            "--symbol", selected[0],
            "--entry", str(entry),
            "--or-high", str(opening_high),
            "--or-low", str(opening_low),
        ]
    return run_skill("exit", args)


@mcp.tool()
def backtest_strategy(symbol: str = ""):
    """Run the historical Time Machine analysis using the saved plan. No writes."""
    args = ["run", "--json"]
    if symbol:
        try:
            selected = clean_tickers(symbol)
        except ValueError as exc:
            return {"ok": False, "exit_code": 2, "error_type": "invalid_input", "error": str(exc)}
        if len(selected) != 1:
            return {"ok": False, "exit_code": 2, "error_type": "invalid_input", "error": "Provide exactly one ticker"}
        args += ["--symbol", selected[0]]
    return run_skill("timemachine", args, timeout=240)


@mcp.tool()
def check_risk():
    """Check proposed orders against configured risk rules. Does not save verdicts."""
    return run_skill("risk", ["--no-write", "--json"])


@mcp.tool()
def calculate_position_size(
    budget: float = 0,
    symbol: str = None,
    entry: float = None,
    stop: float = None,
    target: float = None,
    opening_high: float = None,
    opening_low: float = None
):
    """Calculate a proposed position size without writing an order or placing a trade.

    Requires an existing trade plan unless all plan inputs are supplied. Explicit
    inputs are written to a temporary file that is removed after sizing.
    """
    import tempfile
    from pathlib import Path
    if isinstance(budget, bool) or not isinstance(budget, (int, float)) or not math.isfinite(float(budget)):
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input", "error": "budget must be a finite number"}
    if budget < 0:
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input", "error": "budget cannot be negative"}

    explicit = (symbol, entry, stop, target, opening_high, opening_low)
    has_explicit = any(value is not None and value != "" for value in explicit)
    if has_explicit:
        if not symbol or any(value is None for value in (entry, stop, target, opening_high, opening_low)):
            return {"ok": False, "exit_code": 2, "error_type": "invalid_input",
                    "error": "Provide symbol, entry, stop, target, opening_high and opening_low together."}
        try:
            selected = clean_tickers(symbol)
            prices = (entry, stop, target, opening_high, opening_low)
            valid_prices = all(
                isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(float(value)) and value > 0 for value in prices
            )
        except (TypeError, ValueError, OverflowError):
            selected, valid_prices = [], False
        if len(selected) != 1 or not valid_prices:
            return {"ok": False, "exit_code": 2, "error_type": "invalid_input",
                    "error": "Plan inputs require one ticker and finite positive prices."}

    args = ["--json"]
    if budget > 0:
        args += ["--budget", str(budget)]

    if has_explicit:
        with tempfile.TemporaryDirectory(prefix="dtai-plan-") as temp_dir:
            plan_path = Path(temp_dir) / "plan.json"
            plan_args = [
                "plan", "--symbol", selected[0], "--entry", str(entry),
                "--or-high", str(opening_high), "--or-low", str(opening_low),
                "--stop", f"price:{stop}", "--target", f"price:{target}",
                "--write", str(plan_path), "--json",
            ]
            plan_result = run_skill("exit", plan_args)
            if not plan_result.get("ok"):
                return {"ok": False, "exit_code": plan_result.get("exit_code", 1),
                        "error_type": "invalid_plan", "error": plan_result.get("error", "Plan validation failed."),
                        "details": plan_result}
            return run_skill("budget", args + ["--plan", str(plan_path)])

    plan_path = ROOT / "trader" / "plan.json"
    if not plan_path.is_file():
        return {
            "ok": False,
            "exit_code": 2,
            "error_type": "missing_prerequisite",
            "error": "Missing required trade plan: trader/plan.json does not exist.",
            "required_file": str(plan_path),
        }
    return run_skill("budget", args + ["--plan", str(plan_path)])


@mcp.tool()
def show_order_tickets():
    """Display existing proposed order tickets. Does not approve or submit orders."""
    return run_skill("broker", ["show", "--json"])


@mcp.tool()
def check_price_alerts():
    """Check configured price alerts without saving alert state or placing orders."""
    return run_skill("alerts", ["check", "--no-write", "--json"], timeout=120)


@mcp.tool()
def get_company_fundamentals(tickers: str):
    """Retrieve company financial facts. Does not write metrics files.

    Requires the genuine user-supplied SEC contact name and email.
    """
    sec_ua = (os.environ.get("SEC_USER_AGENT") or order_gateway._ENV_VARS.get("SEC_USER_AGENT") or "").strip()
    low_ua = sec_ua.lower()
    if not sec_ua or "@" not in sec_ua or any(
        marker in low_ua for marker in ("example.com", "your name", "yourname", "placeholder")
    ):
        return {
            "ok": False,
            "exit_code": 2,
            "error_type": "missing_user_configuration",
            "error": "SEC_USER_AGENT requires the genuine user-supplied contact name and email; no placeholder identity is accepted.",
        }
    try:
        selected = clean_tickers(tickers)
    except ValueError as exc:
        return {"ok": False, "exit_code": 2, "error_type": "invalid_input", "error": str(exc)}
    return run_skill("analyst", [*selected, "--json"], timeout=180,
                     extra_env={"SEC_USER_AGENT": sec_ua})


@mcp.tool()
def check_congress_trades(year: int = 0, member: str = ""):
    """Search congressional trade disclosure index. Does not download or read PDFs."""
    args = ["index", "--json", "--limit", "50"]
    if year:
        if isinstance(year, bool) or not isinstance(year, int) or not 2000 <= year <= 2100:
            return {"ok": False, "exit_code": 2, "error_type": "invalid_input",
                    "error": "year is outside the allowed range"}
        args += ["--year", str(year)]
    if member:
        if not re.fullmatch(r"[A-Za-z .'-]{1,80}", member):
            return {"ok": False, "error": "Invalid member name"}
        args += ["--member", member]
    return run_skill("pelosi", args, timeout=180)


if __name__ == "__main__":
    mcp.settings.host = os.environ.get("ANALYSIS_MCP_HOST", "0.0.0.0")
    mcp.settings.port = int(os.environ.get("ANALYSIS_MCP_PORT", "8000"))
    mcp.run(transport="streamable-http")
