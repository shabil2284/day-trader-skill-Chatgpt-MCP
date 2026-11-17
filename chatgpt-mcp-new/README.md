# 🤖 **chatgpt-mcp-new**

*A strictly read-only FastMCP research server connecting ChatGPT and MCP clients to US stock market scanners, fundamentals, and trade analytics.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 🔍 What it does

**chatgpt-mcp-new** exposes a secure, read-only Model Context Protocol (MCP) server over Streamable HTTP for US equities research. It connects LLM interfaces like ChatGPT directly to the Day Trader suite to query technical chart scans, opening-range breakouts, company fundamentals, breaking news, market clock status, and risk parameters. Hardcoded safety guards actively prevent order execution, ticket modification, state mutation, and trade approvals.

## 🚀 Quick Start

```bash
# Navigate to the sub-project directory
cd chatgpt-mcp-new

# Install dependencies (requires FastMCP 1.26+)
pip install -r requirements.txt

# (Optional) Provide your SEC EDGAR user agent for fundamental data queries
export SEC_USER_AGENT="TradingBot YourName you@example.com"

# Launch the MCP server on http://127.0.0.1:8000/mcp
python3 server.py

# Alternatively, inspect and debug with the FastMCP CLI
mcp dev server.py
```

## 🛠️ Available MCP Tools

| Tool | Parameters | Description |
| --- | --- | --- |
| `server_status` | *None* | Verifies server operational status, HTTP endpoint, and safety configurations. |
| `get_market_clock` | *None* | Fetches current NYSE session status and opening/closing bell timings. |
| `get_quotes` | `symbols: str` | Retrieves delayed Yahoo Finance market quotes (up to 20 comma-separated symbols). |
| `scan_daily` | `symbols: str, limit: int = 10` | Executes daily technical setup scans without writing state files (limit 1-20). |
| `scan_opening_range` | `symbols: str, limit: int = 10` | Scans 5-minute bars for Opening Range Breakouts (ORB) without state writes. |
| `check_entry` | `symbol: str` | Checks whether an entry setup is triggered for a single ticker. |
| `check_risk` | *None* | Evaluates risk on proposed tickets against limits without writing verdicts. |
| `get_news` | `symbols: str` | Fetches recent ticker headlines and catalyst tags using `--dry-run`. |
| `get_existing_tickets` | *None* | Inspects existing proposed order tickets without approval or submission. |
| `get_decision_log` | *None* | Reads the chronological broker decision and execution audit log. |
| `get_exit_plan` | *None* | Displays current bracket stop-loss and target exit plans without changes. |
| `get_company_fundamentals` | `symbols: str` | Pulls fundamental financial facts and SEC EDGAR filing data. |

## 📂 What it reads & writes

| File | Purpose |
| --- | --- |
| `trader-scanner/scan.py` | Read-only scan engine for daily setups and opening-range breakouts |
| `trader-alerts/alerts.py` | Read-only feed for NYSE market session clock and delayed quotes |
| `trader-entry/entry.py` | Read-only evaluation of candle trigger setups |
| `trader-risk/check.py` | Read-only audit of risk allocations and account thresholds |
| `trader-news/news.py` | Read-only market news fetcher executed with `--dry-run` |
| `trader-broker/ticket.py` | Read-only viewer for proposed broker tickets and logs |
| `trader-analyst/facts.py` | Read-only SEC EDGAR company financial statements and facts |
| `trader-exit/exit.py` | Read-only viewer for active trade bracket plans |
| `trader/*` (State Files) | **No writes permitted.** All write flags (`--write`, `add`, `plan`, `fill`) are blocked |

## 🛡️ Safety & Guardrails

- **Strictly Read-Only Execution**: The server blocks forbidden commands including `--write`, `approve`, `decline`, `fill`, `flatten`, `reset`, `add`, `plan`, `place_order`, and `cancel_order`.
- **Enforced Non-Mutating Flags**: Subprocess executions automatically force safe flags such as `--no-write`, `--dry-run`, and `--json`.
- **Input Validation**: Tickers are validated against `^[A-Z0-9.-]{1,15}$` with a hard limit of 20 symbols per query to prevent argument injection and excessive load.
- **Process Timeouts**: Subprocess execution is strictly bounded (90s default, up to 180s for market scans) to prevent hung processes.
- **Delayed Data Disclaimer**: Market quotes from Yahoo Finance are delayed and not suitable for live order execution.

---

[← Back to Day Trader Skill](../README.md)
