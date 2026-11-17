import fcntl
import hashlib
import json
import math
import os
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
STATE_DIR = Path(os.environ.get("ORDER_STATE_DIR", Path(__file__).resolve().parent / "state"))

PAPER_URL = "https://paper-api.alpaca.markets/v2"
LIVE_URL = "https://api.alpaca.markets/v2"
MAX_NOTIONAL_USD = 100.00
PROPOSAL_TTL_SECONDS = 300

# Control switches (defaults to disabled)
ALPACA_PAPER_TRADING_ENABLED = False
ALPACA_ORDER_SUBMISSION_ENABLED = False
ALPACA_LIVE_TRADING_ENABLED = False

ALPACA_FIELDS = ("symbol", "side", "qty", "notional", "type", "time_in_force", "limit_price",
                 "stop_price", "trail_price", "trail_percent", "extended_hours", "client_order_id",
                 "order_class", "take_profit_limit_price", "stop_loss_stop_price",
                 "stop_loss_limit_price", "advanced_instructions")


class TradeMode(Enum):
    PAPER = "paper"
    LIVE = "live"


def _load_env_vars():
    """Loads environment variables from .env file, then overlays process environment."""
    values = {}

    # Read from .env file as fallback
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip('"').strip("'")

    # Overlay process environment (higher priority)
    for k, v in os.environ.items():
        if v is not None:
            values[k] = v

    return values


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse boolean environment variable from _ENV_VARS."""
    value = _ENV_VARS.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"true", "1", "yes", "on"}


_ENV_VARS = _load_env_vars()

# Initialize control switches from environment variables using boolean parser
ALPACA_PAPER_TRADING_ENABLED = _env_bool("ALPACA_PAPER_TRADING_ENABLED", False)
ALPACA_ORDER_SUBMISSION_ENABLED = _env_bool("ALPACA_ORDER_SUBMISSION_ENABLED", False)
ALPACA_LIVE_TRADING_ENABLED = _env_bool("ALPACA_LIVE_TRADING_ENABLED", False)


def credentials(mode: TradeMode):
    """Retrieves Alpaca credentials and endpoint for the specified mode."""
    key = None
    secret = None
    url = None

    if mode == TradeMode.PAPER:
        if not ALPACA_PAPER_TRADING_ENABLED:
            raise RuntimeError("Paper trading is not enabled in the configuration.")

        # Support APCA_API_KEY_ID / ALPACA_PAPER_API_KEY / ALPACA_API_KEY for PAPER mode
        key = (_ENV_VARS.get("APCA_API_KEY_ID") or
               _ENV_VARS.get("ALPACA_PAPER_API_KEY") or
               _ENV_VARS.get("ALPACA_API_KEY"))
        secret = (_ENV_VARS.get("APCA_API_SECRET_KEY") or
                  _ENV_VARS.get("ALPACA_PAPER_SECRET_KEY") or
                  _ENV_VARS.get("ALPACA_SECRET_KEY"))
        # PAPER credentials must never be sent to a user-configured LIVE host.
        # The broker endpoint is fixed for this deployment.
        url = PAPER_URL

        if not key or not secret:
            raise RuntimeError("Alpaca PAPER credentials missing.")

    elif mode == TradeMode.LIVE:
        if not ALPACA_LIVE_TRADING_ENABLED:
            raise RuntimeError("Live trading is not enabled in the configuration.")
        if not ALPACA_ORDER_SUBMISSION_ENABLED:
            raise RuntimeError("Order submission is globally disabled. Enable ALPACA_ORDER_SUBMISSION_ENABLED.")

        key = _ENV_VARS.get("ALPACA_LIVE_API_KEY")
        secret = _ENV_VARS.get("ALPACA_LIVE_SECRET_KEY")
        url = LIVE_URL

        if not key or not secret:
            raise RuntimeError("Alpaca LIVE credentials missing.")

    if not key or not secret or not url:
        raise RuntimeError(f"Alpaca credentials or URL missing for {mode.name} mode.")

    return key, secret, url


def request(method: str, path: str, mode: TradeMode, payload: Optional[dict] = None):
    """Makes an authenticated request to the Alpaca API."""
    if mode == TradeMode.LIVE and method.upper() != "GET":
        raise RuntimeError("LIVE broker mutations are disabled in this build.")
    key, secret, base_url = credentials(mode)
    data = None if payload is None else json.dumps(payload).encode()

    # Normalize base_url and path to ensure /v2 prefix exactly once
    base_url = base_url.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path

    if base_url.endswith("/v2"):
        if path.startswith("/v2/"):
            path = path[3:] # Strip leading /v2
    else:
        if not path.startswith("/v2/"):
            path = "/v2" + path

    req = urllib.request.Request(
        base_url + path,
        data=data,
        method=method,
        headers={
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        # Check if this is a broker rejection (e.g., 403 Forbidden or 422 Unprocessable Entity)
        if exc.code in [403, 422]:
            raise ValueError(f"Alpaca {exc.code} Broker Rejected: {detail}") from None
        raise RuntimeError(f"Alpaca HTTP {exc.code}: {detail}") from None


def _get_state_file_path(mode: TradeMode) -> Path:
    return STATE_DIR / f"order_state_{mode.value}.json"


@contextmanager
def _locked_state(mode: TradeMode):
    """Context manager for atomic state operations with file locking."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = STATE_DIR / f"order_state_{mode.value}.lock"
    state_file = _get_state_file_path(mode)

    with open(lock_file, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(f"State file for {mode.name} is currently locked by another process.") from None

        try:
            state = json.loads(state_file.read_text()) if state_file.exists() else {"proposals": {}}
            if not isinstance(state, dict) or not isinstance(state.get("proposals"), dict):
                raise RuntimeError(f"State file for {mode.name} has an invalid format.")
            try:
                yield state
            finally:
                # Persist lifecycle changes even when the operation raises after
                # changing a status (expired, rejected by broker, or unknown).
                temp = state_file.with_suffix(".tmp")
                temp.write_text(json.dumps(state, indent=2) + "\n")
                os.chmod(temp, 0o600)
                temp.replace(state_file)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def read_state(mode: TradeMode):
    """Reads the state file for the given trading mode (WITHOUT LOCKING - use ONLY for read-only listings)."""
    state_file = _get_state_file_path(mode)
    if not state_file.exists():
        return {"proposals": {}}
    return json.loads(state_file.read_text())


def write_state(state: dict, mode: TradeMode):
    """Writes the state to the state file for the given trading mode (UNSAFE - use _locked_state instead)."""
    state_file = _get_state_file_path(mode)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temp = state_file.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2) + "\n")
    temp.replace(state_file)


def generate_fingerprint(order: dict) -> str:
    """Exact implementation of the order fingerprint algorithm."""
    core = {k: order[k] for k in ALPACA_FIELDS if k in order and order[k] is not None}
    blob = json.dumps(core, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _approval_phrase(proposal: dict) -> str:
    price = proposal.get("limit_price")
    if price is None:
        price = f"{float(proposal['reference_price']):.2f} REF"
    mode = str(proposal.get("mode", "")).upper()
    protection = ""
    if proposal.get("stop_loss_price") is not None or proposal.get("take_profit_price") is not None:
        protection = (
            f" STOP {float(proposal['stop_loss_price']):.2f}"
            f" TARGET {float(proposal['take_profit_price']):.2f}"
        )
    return (
        f"APPROVE {proposal['id']} {mode} {str(proposal['side']).upper()} "
        f"{int(proposal['qty'])} {proposal['symbol']} {str(proposal['type']).upper()} "
        f"{price}{protection} DAY"
    )


def _risk_payload_for_proposal(proposal: dict) -> dict:
    """Adapt the broker's nested bracket payload to trader-risk's input schema."""
    payload = dict(proposal["order_payload"])
    if proposal.get("side") == "buy":
        entry = proposal.get("limit_price") if proposal.get("type") == "limit" else proposal.get("reference_price")
        stop = proposal.get("stop_loss_price")
        target = proposal.get("take_profit_price")
        payload.update({
            "order_class": "bracket",
            "stop_loss_stop_price": f"{float(stop):.2f}",
            "take_profit_limit_price": f"{float(target):.2f}",
            "plan": {
                "entry": f"{float(entry):.2f}",
                "stop": f"{float(stop):.2f}",
                "target": f"{float(target):.2f}",
            },
        })
    return payload


def _validated_proposal_notional(proposal: dict) -> float:
    """Recompute notional from persisted order inputs and reject altered state."""
    try:
        quantity = int(proposal["qty"])
        order_type = proposal["type"]
        price_value = proposal["limit_price"] if order_type == "limit" else proposal["reference_price"]
        price = float(price_value)
        notional = round(quantity * price, 2)
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ValueError("Proposal has invalid quantity or price data.") from None
    if quantity < 1 or not math.isfinite(price) or price <= 0 or not math.isfinite(notional):
        raise ValueError("Proposal has invalid quantity or price data.")
    if notional > MAX_NOTIONAL_USD:
        raise ValueError(f"Paper test cap is ${MAX_NOTIONAL_USD:.2f}. Proposed notional: ${notional:.2f}")

    expected_payload = {
        "symbol": proposal.get("symbol"),
        "qty": str(quantity),
        "side": proposal.get("side"),
        "type": order_type,
        "time_in_force": "day",
        "client_order_id": proposal.get("client_order_id"),
    }
    if order_type == "limit":
        expected_payload["limit_price"] = f"{price:.2f}"
    if proposal.get("side") == "buy":
        try:
            stop = float(proposal["stop_loss_price"])
            target = float(proposal["take_profit_price"])
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError("Buy proposal is missing its protective stop or target.") from None
        if not math.isfinite(stop) or not math.isfinite(target) or not 0 < stop < price < target:
            raise ValueError("Buy proposal has invalid protective stop/target prices.")
        expected_payload.update({
            "order_class": "bracket",
            "take_profit": {"limit_price": f"{target:.2f}"},
            "stop_loss": {"stop_price": f"{stop:.2f}"},
        })
    elif proposal.get("stop_loss_price") is not None or proposal.get("take_profit_price") is not None:
        raise ValueError("Sell-to-close proposals cannot carry buy bracket prices.")
    if proposal.get("order_payload") != expected_payload:
        raise ValueError("Proposal order details changed after approval was requested.")
    if proposal.get("notional_usd") != notional:
        raise ValueError("Proposal notional changed after approval was requested.")
    phrase_hash = hashlib.sha256(_approval_phrase(proposal).encode()).hexdigest()
    if not secrets.compare_digest(phrase_hash, str(proposal.get("approval_hash", ""))):
        raise ValueError("Proposal approval record does not match its order details.")
    return notional


def validate_risk(order: dict, mode: TradeMode):
    """Runs the authoritative trader-risk/check.py against a proposed order."""
    temp_dir = Path(tempfile.gettempdir()) / "dtai_risk"
    temp_dir.mkdir(parents=True, exist_ok=True)

    orders_file = temp_dir / f"orders_{secrets.token_hex(4)}.json"
    risk_file = temp_dir / f"risk_{secrets.token_hex(4)}.json"

    try:
        # 1. Build the proposed orders file
        orders_doc = {
            "created_by": "order-gateway",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "proposed",
            "paper": mode == TradeMode.PAPER,
            "orders": [order]
        }
        orders_file.write_text(json.dumps(orders_doc, indent=2))

        # 2. Run trader-risk/check.py
        risk_check_script = ROOT / "trader-risk" / "check.py"
        if not risk_check_script.exists():
             raise RuntimeError("trader-risk/check.py not found")

        config_path = ROOT / "trader" / "config.json"
        if not config_path.exists():
            config_path = ROOT / "trader-budget" / "config.example.json"

        cmd = [
            "python3", str(risk_check_script),
            "--orders", str(orders_file),
            "--config", str(config_path),
            "--out", str(risk_file),
            "--json"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        if result.returncode != 0 and not result.stdout:
            raise RuntimeError(f"Risk check failed to execute: {result.stderr}")

        # 3. Parse and verify the risk verdict
        if not risk_file.exists():
            raise RuntimeError("Risk check did not produce a verdict file.")

        risk_data = json.loads(risk_file.read_text())
        order_result = risk_data["results"][0]
        fp = generate_fingerprint(order)

        if order_result["fingerprint"] != fp:
            raise RuntimeError(f"Risk verdict fingerprint mismatch: {order_result['fingerprint']} != {fp}")

        if order_result["verdict"] != "PASS":
            reasons = "; ".join(order_result.get("reasons", ["Unknown reason"]))
            raise RuntimeError(f"Risk validation BLOCKED: {reasons}")

        return True

    finally:
        if orders_file.exists(): orders_file.unlink()
        if risk_file.exists(): risk_file.unlink()


def propose(mode: TradeMode, symbol: str, side: str, quantity: int, order_type: str,
            limit_price: Optional[float] = None, reference_price: Optional[float] = None,
            stop_loss_price: Optional[float] = None, take_profit_price: Optional[float] = None):
    if mode != TradeMode.PAPER:
        raise ValueError("Only PAPER proposals are allowed; LIVE trading is disabled.")
    symbol = symbol.strip().upper()
    side = side.strip().lower()

    if side not in ["buy", "sell"]:
        raise ValueError("Side must be 'buy' or 'sell'.")
    if not symbol.isalnum() or not 1 <= len(symbol) <= 10:
        raise ValueError("Invalid stock ticker symbol.")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise ValueError("Quantity must be a positive whole number.")
    if order_type not in ["market", "limit"]:
        raise ValueError("Order type must be 'market' or 'limit'.")
    if order_type == "limit" and (
        limit_price is None or isinstance(limit_price, bool)
        or not isinstance(limit_price, (int, float))
        or not math.isfinite(float(limit_price)) or limit_price <= 0
    ):
        raise ValueError("Limit orders require a valid positive limit_price.")
    if order_type == "market" and (
        reference_price is None or isinstance(reference_price, bool)
        or not isinstance(reference_price, (int, float))
        or not math.isfinite(float(reference_price)) or reference_price <= 0
    ):
        raise ValueError("Market orders require a valid positive reference_price for estimation.")

    price_for_notional = limit_price if order_type == "limit" else reference_price
    price_for_notional = float(f"{float(price_for_notional):.2f}")
    notional = round(quantity * price_for_notional, 2)

    if side == "buy":
        if order_type != "limit":
            raise ValueError("PAPER buy entries must use a limit order to enforce the $100 notional cap.")
        if stop_loss_price is None or take_profit_price is None:
            raise ValueError("PAPER buy proposals require both stop_loss_price and take_profit_price.")
        prices = (stop_loss_price, take_profit_price)
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(float(value)) or value <= 0 for value in prices):
            raise ValueError("Protective stop and target must be finite positive prices.")
        stop_loss_price = float(f"{float(stop_loss_price):.2f}")
        take_profit_price = float(f"{float(take_profit_price):.2f}")
        if not 0 < stop_loss_price < price_for_notional < take_profit_price:
            raise ValueError("For a PAPER buy, require stop_loss_price < entry price < take_profit_price.")
    elif stop_loss_price is not None or take_profit_price is not None:
        raise ValueError("Protective bracket prices are only accepted for PAPER buy entries.")

    if not math.isfinite(notional) or notional > MAX_NOTIONAL_USD:
        raise ValueError(f"Paper test cap is ${MAX_NOTIONAL_USD:.2f}. Proposed notional: ${notional:.2f}")

    # Verify the credentials still resolve to an active account for the given mode.
    account = request("GET", "/account", mode)
    if account.get("status") != "ACTIVE" or account.get("trading_blocked"):
        raise RuntimeError(f"{mode.name} account is not active or trading is blocked.")

    # Check buying power for BUY orders, and available shares for SELL orders
    if side == "buy":
        buying_power = float(account.get("buying_power", 0))
        if notional > buying_power:
            raise RuntimeError(f"Insufficient buying power: ${notional:.2f} > ${buying_power:.2f}")
    else: # side == "sell"
        positions = request("GET", "/positions", mode)
        symbol_position = next((p for p in positions if p["symbol"] == symbol), None)
        if not symbol_position:
            raise RuntimeError(f"No long position found for {symbol}. Short selling is not supported.")

        available_qty = int(symbol_position["qty"])
        orders = request("GET", "/orders?status=open&side=sell", mode)
        open_sell_qty = sum(int(o["qty"]) for o in orders if o["symbol"] == symbol)

        if quantity > (available_qty - open_sell_qty):
            raise RuntimeError(f"Sell quantity exceeds available long position: {quantity} > {available_qty - open_sell_qty} (Total: {available_qty}, Open Sells: {open_sell_qty})")

    # Unique proposal ID based on order parameters to prevent duplicates
    # Generate fingerprint of the payload to use as base for proposal ID
    order_payload = {
        "symbol": symbol,
        "qty": str(quantity),
        "side": side,
        "type": order_type,
        "time_in_force": "day",
    }
    if order_type == "limit":
        order_payload["limit_price"] = f"{float(limit_price):.2f}"

    # We use a hash of the order parameters as a deterministic base for proposal ID
    # But we want to allow multiple proposals if desired.
    # The requirement asks for auditability of the *proposal* lifecycle.
    # Let's keep existing behavior (random ID) as it's safer for sequential proposals.
    # The user's prompt asked to "audit... idempotency".
    # I will leave the ID as random as it is, as re-proposing an order with
    # the same parameters is a valid action in many trading workflows.
    proposal_id = secrets.token_hex(8)
    client_order_id = "dtai-" + proposal_id

    order_payload = {
        "symbol": symbol,
        "qty": str(quantity),
        "side": side,
        "type": order_type,
        "time_in_force": "day",
        "client_order_id": client_order_id,
    }
    if order_type == "limit":
        order_payload["limit_price"] = f"{float(limit_price):.2f}"

    if side == "buy":
        order_payload.update({
            "order_class": "bracket",
            "take_profit": {"limit_price": f"{take_profit_price:.2f}"},
            "stop_loss": {"stop_price": f"{stop_loss_price:.2f}"},
        })

    risk_payload = dict(order_payload)
    if side == "buy":
        risk_payload.update({
            "stop_loss_stop_price": f"{stop_loss_price:.2f}",
            "take_profit_limit_price": f"{take_profit_price:.2f}",
            "plan": {
                "entry": f"{price_for_notional:.2f}",
                "stop": f"{stop_loss_price:.2f}",
                "target": f"{take_profit_price:.2f}",
            },
        })
    validate_risk(risk_payload, mode)

    price_text = f"{float(limit_price):.2f}" if limit_price is not None else f"{float(reference_price):.2f} REF"
    mode_text = mode.name.upper()
    side_text = side.upper()
    order_type_text = order_type.upper()
    protection_text = (
        f" STOP {stop_loss_price:.2f} TARGET {take_profit_price:.2f}"
        if side == "buy" else ""
    )

    approval_phrase = (
        f"APPROVE {proposal_id} {mode_text} {side_text} {quantity} {symbol} "
        f"{order_type_text} {price_text}{protection_text} DAY"
    )

    proposal = {
        "id": proposal_id,
        "mode": mode.value,
        "symbol": symbol,
        "side": side,
        "qty": str(quantity),
        "type": order_type,
        "limit_price": (f"{float(limit_price):.2f}" if limit_price is not None else None),
        "reference_price": (f"{float(reference_price):.2f}" if reference_price is not None else None),
        "stop_loss_price": (f"{stop_loss_price:.2f}" if stop_loss_price is not None else None),
        "take_profit_price": (f"{take_profit_price:.2f}" if take_profit_price is not None else None),
        "time_in_force": "day",
        "notional_usd": notional,
        "client_order_id": client_order_id,
        "created_at": time.time(),
        "expires_at": time.time() + PROPOSAL_TTL_SECONDS,
        "status": "pending",
        "approval_hash": hashlib.sha256(approval_phrase.encode()).hexdigest(),
        "order_payload": order_payload
    }

    with _locked_state(mode) as state:
        state["proposals"][proposal_id] = proposal

    return {
        "status": "PENDING_APPROVAL",
        "proposal_id": proposal_id,
        "mode": mode.name.upper(),
        "symbol": symbol,
        "side": side.upper(),
        "quantity": quantity,
        "order_type": order_type.upper(),
        "limit_price": (f"{float(limit_price):.2f}" if limit_price is not None else None),
        "reference_price": (f"{float(reference_price):.2f}" if reference_price is not None else None),
        "time_in_force": "DAY",
        "estimated_value_usd": notional,
        "expires_in_seconds": PROPOSAL_TTL_SECONDS,
        "approval_phrase": approval_phrase,
        "risk_verdict": "PASS",
        "paper_trading_enabled": ALPACA_PAPER_TRADING_ENABLED,
        "live_trading_enabled": False,
        "live_trading_policy_enforced": True,
        "order_submission_enabled": ALPACA_ORDER_SUBMISSION_ENABLED,
        "message": "No order has been submitted.",
    }


def approve_and_submit(proposal_id: str, approval_phrase: str):
    if not isinstance(proposal_id, str) or not proposal_id:
        raise ValueError("A valid proposal ID is required.")
    if not isinstance(approval_phrase, str) or not approval_phrase:
        raise ValueError("The exact approval phrase is required.")
    # First, find the mode without locking
    mode = None
    for m in [TradeMode.PAPER, TradeMode.LIVE]:
        state = read_state(m)
        if proposal_id in state["proposals"]:
            mode = m
            break

    if not mode:
        raise ValueError("Unknown proposal ID or proposal not found in any mode.")

    # Now perform the locked operation
    with _locked_state(mode) as state:
        proposal = state["proposals"].get(proposal_id)
        if not proposal:
             raise ValueError("Proposal disappeared while acquiring lock.")

        if mode == TradeMode.LIVE:
            raise RuntimeError("LIVE order submission is disabled in this build.")
        if not ALPACA_ORDER_SUBMISSION_ENABLED:
            raise RuntimeError("Order submission is globally disabled in this build.")
        if mode == TradeMode.PAPER and not ALPACA_PAPER_TRADING_ENABLED:
            raise RuntimeError("Paper order submission is disabled in this build.")

        if proposal["status"] != "pending":
            raise ValueError(f"Proposal is not pending: {proposal['status']}.")

        if time.time() >= proposal["expires_at"]:
            proposal["status"] = "expired"
            raise ValueError("Proposal expired; create a new proposal.")

        if proposal.get("id") != proposal_id:
            raise ValueError("Proposal ID does not match its persisted approval record.")
        notional = _validated_proposal_notional(proposal)
        supplied_hash = hashlib.sha256(approval_phrase.encode()).hexdigest()
        if not secrets.compare_digest(supplied_hash, str(proposal.get("approval_hash", ""))):
            raise ValueError("Approval phrase does not exactly match this proposal.")

        # Re-check account immediately before consuming approval.
        account = request("GET", "/account", mode)
        if account.get("status") != "ACTIVE" or account.get("trading_blocked"):
            raise RuntimeError(f"{mode.name} account is not active or trading is blocked.")

        # Check available buying power or positions again just before submission
        if proposal["side"] == "buy":
            buying_power = float(account.get("buying_power", 0))
            if notional > buying_power:
                 raise RuntimeError(f"Insufficient buying power just before submission: ${notional:.2f} > ${buying_power:.2f}")
        else: # sell
            positions = request("GET", "/positions", mode)
            symbol_position = next((p for p in positions if p["symbol"] == proposal["symbol"]), None)
            if not symbol_position or int(symbol_position["qty"]) < int(proposal["qty"]):
                raise RuntimeError(f"Insufficient long position for {proposal['symbol']} just before submission.")

        # Re-check risk verdict immediately before submission
        validate_risk(_risk_payload_for_proposal(proposal), mode)
        _validated_proposal_notional(proposal)

        # Mark as SUBMITTING and persist before the broker call. If the process
        # dies during the request, reconciliation can query by client_order_id.
        proposal["status"] = "submitting"
        proposal["approved_at"] = time.time()
        state_file = _get_state_file_path(mode)
        temp = state_file.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2) + "\n")
        os.chmod(temp, 0o600)
        temp.replace(state_file)

        # Recompute again immediately before submission so corrupted or stale
        # proposal state cannot bypass the hard notional ceiling.
        try:
            _validated_proposal_notional(proposal)
        except ValueError as exc:
            proposal["status"] = "submission_failed"
            proposal["error"] = str(exc)
            raise

        try:
            result = request("POST", "/orders", mode, proposal["order_payload"])
            if not isinstance(result, dict) or not result.get("id"):
                raise RuntimeError("Alpaca returned no order ID; submission outcome is uncertain.")
            proposal["status"] = "submitted"
            proposal["broker_order_id"] = result.get("id")
            proposal["broker_status"] = result.get("status")
            proposal["submitted_at"] = time.time()
            return {
                "status": f"SUBMITTED_TO_ALPACA_{mode.name.upper()}",
                "proposal_id": proposal_id,
                "broker_order_id": result.get("id"),
                "broker_status": result.get("status"),
                "mode": mode.name.upper(),
            }
        except ValueError as exc:
            # This catches broker rejections (403, 422) which we treat as BROKER_REJECTED
            proposal["status"] = "broker_rejected"
            proposal["error"] = str(exc)
            raise exc
        except Exception as exc:
            # Never retry automatically. A timeout may mean Alpaca received it.
            proposal["status"] = "submission_unknown"
            proposal["error"] = str(exc)
            raise RuntimeError(
                "Submission outcome is uncertain. Do not retry. "
                f"Check Alpaca {mode.name} orders using client_order_id "
                + proposal["client_order_id"]
            ) from None


def reject(proposal_id: str):
    # First, find the mode without locking
    mode = None
    for m in [TradeMode.PAPER, TradeMode.LIVE]:
        state = read_state(m)
        if proposal_id in state["proposals"]:
            mode = m
            break

    if not mode:
        raise ValueError("Unknown proposal ID or proposal not found in any mode.")

    with _locked_state(mode) as state:
        proposal = state["proposals"].get(proposal_id)
        if not proposal:
            raise ValueError("Proposal disappeared while acquiring lock.")

        if proposal["status"] != "pending":
            raise ValueError(f"Cannot reject proposal in status {proposal['status']}.")

        if time.time() >= proposal.get("expires_at", 0):
            proposal["status"] = "expired"
            raise ValueError("Proposal expired; it cannot be rejected as pending.")

        proposal["status"] = "rejected"
        proposal["rejected_at"] = time.time()
        return {"status": "REJECTED", "proposal_id": proposal_id, "mode": mode.name.upper()}


def list_proposals(mode: Optional[TradeMode] = None):
    """Lists all proposals, or proposals for a specific mode if provided."""
    all_proposals = []
    modes_to_check = [mode] if mode else [TradeMode.PAPER, TradeMode.LIVE]

    for m in modes_to_check:
        # For listing, we can try to lock but let's just read (it's okay if it's slightly stale)
        # Actually, we need to update 'expired' status, so we should lock.
        try:
            with _locked_state(m) as state:
                now = time.time()
                for proposal_id, proposal in state["proposals"].items():
                    if proposal["status"] == "pending" and now > proposal["expires_at"]:
                        proposal["status"] = "expired"

                    proposal_copy = proposal.copy()
                    proposal_copy["proposal_id"] = proposal_id
                    proposal_copy["mode"] = m.name.upper()
                    all_proposals.append({
                        k: v for k, v in proposal_copy.items()
                        if k != "approval_hash" and k != "order_payload"
                    })
        except Exception:
            # Fallback to read-only if lock fails
            state = read_state(m)
            for proposal_id, proposal in state["proposals"].items():
                proposal_copy = proposal.copy()
                proposal_copy["proposal_id"] = proposal_id
                proposal_copy["mode"] = m.name.upper()
                all_proposals.append({
                    k: v for k, v in proposal_copy.items()
                    if k != "approval_hash" and k != "order_payload"
                })

    all_proposals.sort(key=lambda p: p.get("created_at", 0), reverse=True)
    return all_proposals


def reconcile(proposal_id: str):
    """
    Reconcile an order that had an uncertain submission outcome.
    Queries Alpaca by client_order_id to see if it was actually placed.
    """
    # 1. Find the mode
    mode = None
    for m in [TradeMode.PAPER, TradeMode.LIVE]:
        state = read_state(m)
        if proposal_id in state["proposals"]:
            mode = m
            break

    if not mode:
        raise ValueError("Unknown proposal ID.")

    with _locked_state(mode) as state:
        proposal = state["proposals"].get(proposal_id)
        if not proposal:
            raise ValueError("Proposal disappeared.")

        if proposal["status"] not in {"submission_unknown", "submitting"}:
            return {"status": proposal["status"], "info": "Proposal does not need reconciliation."}

        # Query Alpaca
        try:
            client_order_id = proposal["client_order_id"]
            order_data = request("GET", f"/orders/by_client_order_id/{client_order_id}", mode)

            # If we get here, it means Alpaca has the order
            proposal["status"] = "submitted"
            proposal["broker_order_id"] = order_data["id"]
            proposal["broker_status"] = order_data["status"]
            return {
                "status": "SUBMITTED",
                "broker_order_id": order_data["id"],
                "broker_status": order_data["status"],
                "mode": mode.name.upper()
            }
        except Exception as exc:
            # If it's a 404 from Alpaca, it means the order definitely doesn't exist
            if "HTTP 404" in str(exc):
                proposal["status"] = "submission_failed"
                proposal["error"] = "Alpaca confirmed order was not received (404)."
                return {
                    "status": "SUBMISSION_FAILED",
                    "error": proposal["error"],
                    "mode": mode.name.upper()
                }

            # Other errors (timeout, 500) mean it's still unknown
            raise RuntimeError(f"Broker status check failed: {str(exc)}")


def get_broker_status(proposal_id: str) -> dict:
    """
    Retrieve the broker status for a given proposal ID.

    Args:
        proposal_id: The ID of the proposal to check.

    Returns:
        A dictionary containing the broker order ID and status, or an error message.
    """
    # Find the mode without locking
    mode = None
    for m in [TradeMode.PAPER, TradeMode.LIVE]:
        state = read_state(m)
        if proposal_id in state["proposals"]:
            mode = m
            break

    if not mode:
        raise ValueError(f"Proposal {proposal_id} not found in any mode.")

    # Get the proposal details
    with _locked_state(mode) as state:
        proposal = state["proposals"][proposal_id]

    # Check if the proposal has a broker_order_id (submitted order)
    if "broker_order_id" not in proposal:
        return {
            "status": "UNKNOWN",
            "error": "Broker order ID not found. Proposal may not have been submitted yet.",
            "mode": mode.name.upper()
        }

    # Query Alpaca for the broker order status
    try:
        broker_order_id = proposal["broker_order_id"]
        order_data = request("GET", f"/orders/{broker_order_id}", mode)
        return {
            "broker_order_id": broker_order_id,
            "status": order_data.get("status", "UNKNOWN"),
            "mode": mode.name.upper()
        }
    except Exception as exc:
        return {
            "status": "ERROR",
            "error": str(exc),
            "mode": mode.name.upper()
        }
