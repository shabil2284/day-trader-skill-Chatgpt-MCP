# 🔌 **chatgpt-mcp**

*Model Context Protocol server connecting AI assistants to market scanning, trade planning, and guarded order execution.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 🎯 What it does

`chatgpt-mcp` exposes the Day Trader AI suite to AI assistants like ChatGPT and Claude via the Model Context Protocol (MCP) using Streamable HTTP. It wraps 11 specialized trading skills into allowlisted, read-only tools for chart scanning, breaking news retrieval, technical entry timing, exit planning, risk evaluation, and historical backtesting. For brokerage interactions, it integrates with Alpaca to provide read-only account telemetry and a guarded, human-in-the-loop order proposal workflow locked to paper trading.

## 🚀 Quick Start

```bash
# Run the Analysis MCP server (FastMCP on port 8000)
python3 chatgpt-mcp/server.py

# Run the Execution MCP server (FastMCP on port 8001)
python3 chatgpt-mcp/execution_server.py

# Or launch both MCP services via Docker Compose
docker compose up -d analysis-mcp execution-mcp

# Inspect server status and configuration
curl -s http://localhost:8000/status

# Run the MCP test suite
python3 -m unittest discover -s chatgpt-mcp/tests -v
```

## 📂 What it reads & writes

| File | Purpose |
| --- | --- |
| `.env` | Reads Alpaca credentials (`ALPACA_PAPER_API_KEY`), feature toggles, and `SEC_USER_AGENT` |
| `trader/universe.txt` | Reads stock universe list; automatically generated via `scan_market(mode="universe")` if missing |
| `trader/plan.json` | Reads exit trade plans when calculating position sizes without explicit input arguments |
| `chatgpt-mcp/state/order_state_paper.json` | Reads and writes active, pending, and completed paper order proposals |
| `chatgpt-mcp/state/order_state_paper.lock` | Atomic file lock preventing concurrent race conditions during order state updates |
| `chatgpt-mcp/state/order_state_live.json` | Live trading state storage (strictly locked and disabled by safety policy) |

## 🛠️ Available MCP Tools

### Analysis Tools (`server.py`)
- `server_status`: Check server health, active skills count, and account configuration.
- `get_account(mode)`: Read Alpaca account balances, buying power, and trading status (read-only).
- `get_market_clock(mode)`: Read US stock market open/closed status.
- `get_positions(mode)`: Inspect current open equity positions.
- `scan_market(mode, symbols, limit)`: Scan tickers for daily setups or opening-range breakouts (ORB).
- `get_market_news(tickers, hours)`: Fetch recent stock headlines in dry-run mode.
- `check_entry(symbol, setup)`: Validate technical entry conditions for a stock.
- `plan_exit(symbol, entry, opening_high, opening_low)`: Calculate protective stop-loss and take-profit targets.
- `backtest_strategy(symbol)`: Run historical 10,000-session Time Machine simulation.
- `check_risk()`: Verify proposed orders against configured risk parameters without mutating state.
- `calculate_position_size(...)`: Compute share quantity against risk budget without saving orders.
- `show_order_tickets()`: Display pending formatted order tickets.
- `check_price_alerts()`: Check price alert triggers without saving alert state.
- `get_company_fundamentals(tickers)`: Retrieve SEC EDGAR financial facts (requires genuine `SEC_USER_AGENT`).
- `check_congress_trades(year, member)`: Search congressional trade disclosure index.

### Execution & Order Tools (`execution_server.py` & `order_gateway.py`)
- `propose_order(...)`: Stage a paper bracket order with mandatory protective stop and target.
- `approve_and_submit_order(proposal_id, approval_phrase)`: Authorize and transmit an order using its unique one-time phrase.
- `reject_order(proposal_id)`: Discard a pending order proposal.
- `reconcile_order(proposal_id)`: Resolve uncertain broker submission outcomes with Alpaca.
- `list_order_proposals(mode)`: Query pending, filled, rejected, or expired proposals.

## 🛡️ Safety Guards & Execution Policy

- **Strict Command Allowlisting**: Only pre-approved analysis subcommands (`daily`, `orb`, `universe`, `--tickers`, `check`, `plan`, `run`, `show`, `index`) are permitted to run through the MCP subprocess runner.
- **Write-Action Blocking**: Sub-skill arguments including `--write`, `approve`, `decline`, `fill`, `flatten`, `place_order`, and `close_all_positions` are rejected to prevent unvetted file or broker modifications.
- **Paper Trading Enforcement**: `ALPACA_LIVE_TRADING_ENABLED` is hard-locked to `False` by policy; live orders are blocked.
- **Two-Step Human Approval**: Every order requires explicit two-phase staging (`propose_order` generates a cryptographic phrase that must be matched in `approve_and_submit_order`).
- **Safety Caps & Timeouts**: Enforces a strict $100.00 maximum notional cap per paper trade, a 300-second proposal expiration TTL, and 120–240 second subprocess timeouts.
- **Transport Security**: `TransportSecuritySettings` limits HTTP host access strictly to allowlisted endpoints (`analysis-mcp`, `localhost`, `127.0.0.1`).

---

[← Back to Day Trader Skill](../README.md)
