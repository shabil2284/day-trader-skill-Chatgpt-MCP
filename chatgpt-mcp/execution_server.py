import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
import order_gateway
from order_gateway import TradeMode

# Fix typo in order_gateway reference for get_order_proposal
GateMode = TradeMode  # Backward compatibility alias

mcp = FastMCP(
    "Execution Server",
    transport_security=TransportSecuritySettings(
        allowed_hosts=[
            "execution-mcp:8001",
            "execution-mcp:*",
            "localhost:*",
            "127.0.0.1:*",
        ]
    ),
)

@mcp.tool()
def get_execution_server_status():
    """Get the Execution MCP server status and trading configuration. Read-only."""
    # Check if credentials are set (without exposing them)
    paper_key = order_gateway._ENV_VARS.get("ALPACA_PAPER_API_KEY") or order_gateway._ENV_VARS.get("ALPACA_API_KEY")
    live_key = order_gateway._ENV_VARS.get("ALPACA_LIVE_API_KEY")

    return {
        "server": "Execution Server",
        "status": "running",
        "paper_account_configured": bool(paper_key),
        "live_account_configured": bool(live_key),
        "broker_connection_configured": bool(paper_key) or bool(live_key),
        "paper_trading_enabled": order_gateway.ALPACA_PAPER_TRADING_ENABLED,
        "live_trading_enabled": False,
        "live_trading_policy_enforced": True,
        "order_submission_enabled": order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED,
    }

@mcp.tool()
def get_execution_status(proposal_id: Optional[str] = None):
    """Get the Execution MCP server status and operational state, optionally for a specific proposal."""
    state = order_gateway.read_state(order_gateway.TradeMode.PAPER)
    proposals = state.get("proposals", {})
    if not isinstance(proposals, dict):
        raise RuntimeError("PAPER proposal state has an invalid format.")
    status = {
        "server": "Execution Server",
        "status": "running",
        "paper_trading_enabled": order_gateway.ALPACA_PAPER_TRADING_ENABLED,
        "live_trading_enabled": False,
        "live_trading_policy_enforced": True,
        "order_submission_enabled": order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED,
        "active_proposals": sum(p.get("status") in {"pending", "submitting", "submission_unknown"} for p in proposals.values()),
        "pending_proposals": sum(p.get("status") == "pending" for p in proposals.values()),
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }

    if proposal_id:
        # If a proposal_id is provided, query its broker status
        try:
            status["proposal_broker_status"] = order_gateway.get_broker_status(proposal_id)
        except Exception as exc:
            status["proposal_broker_status"] = {"error": str(exc)}

    return status

@mcp.tool()
def get_order_proposal(proposal_id: str):
    """Retrieve a specific order proposal by ID. Returns proposal details or 404 if not found."""
    # Check both paper and live modes for the proposal
    for mode in [order_gateway.TradeMode.PAPER, order_gateway.TradeMode.LIVE]:
        state = order_gateway.read_state(mode)
        if proposal_id in state["proposals"]:
            proposal = state["proposals"][proposal_id]
            public_proposal = {
                k: v for k, v in proposal.items()
                if k not in {"approval_hash", "order_payload"}
            }
            public_proposal["proposal_id"] = proposal_id
            return public_proposal

    # Proposal not found
    return {
        "error": f"Proposal {proposal_id} not found or not accessible",
        "proposal_id": proposal_id,
        "status": "NOT_FOUND"
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

    normalized = []
    for position in positions:
        if not isinstance(position, dict):
            raise RuntimeError("Alpaca returned a malformed positions list.")

        normalized.append({
            "symbol": position.get("symbol"),
            "quantity": position.get("qty"),
            "market_value": position.get("market_value"),
            "unrealized_pl": position.get("unrealized_pl"),
        })

    return {
        "mode": m.name.upper(),
        "count": len(normalized),
        "positions": normalized,
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
        if not isinstance(mode, str) or not mode:
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


if __name__ == "__main__":
    mcp.settings.host = os.environ.get("EXECUTION_MCP_HOST", "0.0.0.0")
    mcp.settings.port = int(os.environ.get("EXECUTION_MCP_PORT", "8001"))
    mcp.run(transport="streamable-http")
