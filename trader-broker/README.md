# 🏛️ **trader-broker**

*The triple-gated order executor that safely routes approved trades to your broker—paper trading by default, never without your explicit yes.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 🎯 What it does

`trader-broker` is the execution gateway for the Day Trader skill pack, rendering plain-text order tickets, validating explicit confirmations, and submitting trades to your broker. It enforces a strict three-gate safety standard where no order reaches the market without a risk clearance, an exact user confirmation in chat, and an interactive permission card approval. Additionally, it automates end-of-day position flattening by your deadline, logs fills, and tracks maximum risk exposure to maintain strict daily loss limits.

## 🚀 Quick Start

```bash
# Render all proposed order tickets with current status (READY, NOT READY, or BLOCKED)
python3 "${CLAUDE_SKILL_DIR}/ticket.py" show

# Record the user's explicit confirmation for an order (strict verbatim check)
python3 "${CLAUDE_SKILL_DIR}/ticket.py" approve --index 1 --reply "yes"

# Record the execution outcome after Claude's permission prompt is confirmed
python3 "${CLAUDE_SKILL_DIR}/ticket.py" result --index 1 --status placed --broker-id "alp_ord_101" --filled-qty 8 --filled-price 364.20

# Log a fill when a bracket stop-loss or take-profit leg is triggered at the broker
python3 "${CLAUDE_SKILL_DIR}/ticket.py" fill --symbol TSLA --side sell --qty 8 --price 370.04

# Generate an exit ticket to close an open position before the end of the session
python3 "${CLAUDE_SKILL_DIR}/ticket.py" flatten --symbol TSLA --qty 8

# Review today's audit trail of tickets, approvals, rejections, and executions
python3 "${CLAUDE_SKILL_DIR}/ticket.py" log
```

## 📂 What it reads & writes

| File | Purpose |
| --- | --- |
| `trader/orders.json` | Proposed order payloads created by `trader-budget` (or overwritten by `flatten`) |
| `trader/state/risk.json` | Risk evaluation results from `trader-risk`; only a same-day `PASS` marks an order `READY` |
| `trader/state/broker.json` | Immutable audit log of every yes, no, placed, failed, and filled order with max loss records |
| `trader/portfolio.json` | Cash balance and share holdings, updated on fill confirmations and execution results |
| `trader/plan.json` | Daily trading plan parameters, including the mandatory `flat_by` market-close cutoff |

## 🛡️ The Three Gates of Execution

Because `trader-broker` can trigger market orders, an order reaches a broker only after passing three sequential, independent checkpoints:

1. **Rule Validation (`trader-risk`)**: The exact order fingerprint must have received a `PASS` verdict today.
2. **Explicit Chat Confirmation**: The user must explicitly type "yes" for that specific single order in the chat conversation.
3. **Interactive Client Card**: The user must click **Allow once** on the MCP tool execution card triggered by setting order tools to *"Needs approval"*.

> **Two yeses from the user, one PASS from the rules. No yes, no order.**

## 🔌 Supported Broker Connectors

### Setup A: Alpaca (Official MCP Server)

Runs locally via `uvx alpaca-mcp-server` inside Claude Desktop. Configured to trade on a **paper** account by default.

Add the following to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "alpaca": {
      "command": "uvx",
      "args": ["alpaca-mcp-server"],
      "env": {
        "ALPACA_API_KEY": "YOUR_PAPER_KEY_HERE",
        "ALPACA_SECRET_KEY": "YOUR_PAPER_SECRET_HERE",
        "ALPACA_PAPER_TRADE": "true",
        "ALPACA_TOOLSETS": "account,trading,stock-data"
      }
    }
  }
}
```

* **Tool Permissions**:
  * `place_stock_order`: Set to **Needs approval** (never *Always allow*).
  * Order management (`cancel_order_by_id`, `replace_order_by_id`, `close_position`, `update_account_config`): **Needs approval**.
  * Dangerous or leveraged tools (`place_option_order`, `place_crypto_order`, `close_all_positions`, `cancel_all_orders`): **Blocked**.
  * Read-only tools (`get_account_info`, `get_all_positions`, `get_orders`, `get_clock`): **Always allow**.
* **Bracket Orders**: When `take_profit_limit_price` and `stop_loss_stop_price` are specified, Alpaca sets `order_class` to "bracket" with one-cancels-other (OCO) exit legs.

### Setup B: Interactive Brokers (Verified Connector)

Available via Claude's directory (`claude.ai/directory/interactive-brokers`).
* Uses MCP endpoint `https://api.ibkr.com/v1/api/mcp`.
* Drafts trade instructions sent directly to your IBKR account for final review and approval.
* Configured by setting `"broker": "ibkr"` in `trader/config.json`.

## 🔄 Entry & Flattening Workflow

### Order Entry
1. **Render Tickets**: Execute `ticket.py show`. Only `READY` tickets are shown to the user.
2. **Prompt User**: Present a single ticket and request explicit confirmation ("yes" or "no"). Never batch approvals.
3. **Record Approval**: Run `ticket.py approve --index N --reply "<verbatim reply>"`.
4. **Trigger Tool**: Call `place_stock_order` with the exact ticket JSON payload upon recording approval.
5. **Log Execution**: Record the broker response via `ticket.py result --status placed` (or `--status denied` / `--status failed`).

### End-of-Day Flattening
- By the designated `flat_by` time (e.g., 15:55 ET), all open day positions must be closed.
- Retrieve open share quantities using `get_open_position`.
- Generate the closing sell ticket using `ticket.py flatten --symbol <SYM> --qty <N>`.
- Cancel existing open bracket stop/target orders using `cancel_order_by_id` so Alpaca frees the shares.
- Re-run `trader-risk` and obtain the user's explicit confirmation before placing the closing market order.

## 🚫 What It Never Does

* **Never executes without all three gates**: No orders are placed without risk clearance and two user approvals.
* **Never runs autonomously in background tasks**: Scheduled jobs cannot approve orders without a human present.
* **Never leaks credentials**: API keys and secrets belong strictly in environment variables or configuration files, never in chat.
* **Never flips paper accounts to live**: Switching to live accounts must be done deliberately by the user.
* **Never calls bulk-action or crypto/options tools**: Tools like `close_all_positions` and `cancel_all_orders` remain blocked.
* **Never guarantees execution price**: Market and stop orders fill at prevailing market rates.

## ⚠️ Safety Principles

* **Tooling, not financial advice**: A risk `PASS` indicates compliance with programmed limits, not an investment recommendation.
* **Paper trading by default**: Live trading is an intentional decision requiring explicit configuration changes.
* **Tool isolation**: Order-placing tools must always remain configured with **Needs approval**.
* **Cash-only equity trading**: No shorting, margin borrowing, options, or leverage unless explicitly configured and approved.

---
[← Back to Day Trader Skill](../README.md)