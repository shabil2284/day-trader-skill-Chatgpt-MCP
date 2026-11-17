# 🔔 trader-alerts

*Automated price, stop-loss, target, and NYSE market clock alerts so you never have to stare at a chart.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 💡 What it does

`trader-alerts` tracks price thresholds, stops, targets, percentage moves, and the NYSE opening bell, alerting you the moment a level is hit. It transforms trade plans from `trader-exit` into three synchronized alerts—stop-loss, profit target, and flat-by-close—with each rule ringing exactly once to prevent notification spam. All alerts are purely informational and never place or alter orders, keeping you informed while broker bracket orders handle automated trade management.

## 🚀 Quick Start

```bash
# Check NYSE session status and next opening time
python3 alerts.py clock

# Generate stop, target, and flat-by-close alerts from trader/plan.json
python3 alerts.py add --from-plan

# Alert when the NYSE regular session opens
python3 alerts.py add --opening-bell

# Set price threshold alerts for stops and targets
python3 alerts.py add --symbol TSLA --stop 358.32
python3 alerts.py add --symbol TSLA --target 370.04

# Schedule a flat-by-close alert (automatically adjusts 3h early on 1:00 PM closes)
python3 alerts.py add --at 15:55 --label "flat by close" --before-close

# Alert on percentage moves from prior close
python3 alerts.py add --symbol KO --pct 3

# Check all active rules against current quotes (exits with 0 if any alert fired)
python3 alerts.py check

# Fetch delayed quotes and update trader/prices.json for risk and sizing checks
python3 alerts.py quote TSLA --write
python3 alerts.py quote --holdings --write

# List configured alerts and reset a triggered rule
python3 alerts.py list
python3 alerts.py reset tsla-plan-stop
```

> **Testing Options**: Use `--now "YYYY-MM-DD HH:MM"` to pin the clock to a specific New York time, or `--offline <DIR>` to test using local quote files without network requests.

## 📂 What it reads & writes

| File | Purpose |
| --- | --- |
| `trader/plan.json` | Input trade setup from `trader-exit` used by `add --from-plan` |
| `trader/alerts.json` | Configured alert rule definitions and parameters |
| `trader/state/alerts.json` | Runtime state recording which alerts have triggered to prevent repeat notifications |
| `trader/prices.json` | Latest delayed market prices merged for consumption by `trader-budget` and `trader-risk` |
| `trader/portfolio.json` | Current position holdings for `--holdings` batch quote updates |

## 🎯 Rule Types

| Type | Rings When | Rearm / Rings Again |
| --- | --- | --- |
| `above` / `target` | Price is at or above target `price` | After manual `reset`, or automatically if `"rearm": true` and price retreats |
| `below` / `stop` | Price is at or below stop `price` | After manual `reset`, or automatically if `"rearm": true` and price recovers |
| `pct_move` | Price changes by `pct` percent from previous close (or `ref`) | At most once per trading day |
| `time` | New York clock reaches `at` time (e.g., `15:55`) on a trading day | Once per trading day (shifts 3 hours early on 1:00 PM early close days if `before_close` is set) |
| `opening_bell` | NYSE market session opens | Once per trading day |

Rules tagged with `"date"` are only evaluated on that specific New York calendar date. Rules created with `--from-plan` automatically inherit the plan's date so past stops never trigger on subsequent trading days.

## 🕒 Quotes & Market Clock

- **NYSE Session Calendar**: Tracks regular trading hours (9:30 AM – 4:00 PM New York time) with built-in holiday schedules for 2026 and 2027, including scheduled 1:00 PM early closes. Eastern Daylight Time transitions are computed internally without external timezone dependencies.
- **Quote Feeds**: Fetches free delayed quotes via Yahoo Finance (`query2` / `query1` chart JSON, rate-limited at 0.5s intervals with automatic retries) and Stooq CSV.
- **Broker Fallback**: If public endpoints fail, quotes can be sourced from broker connectors (Alpaca `get_stock_snapshot` or IBKR `get_price_snapshot`) and written to `trader/prices.json`.
- **Quote Freshness**: Free quotes are delayed and intended strictly for alerting and sizing checks, not high-frequency order timing. `trader-risk` only accepts quotes under 15 minutes old.

## 🔄 Workflow

1. **Import Plan**: Run `python3 alerts.py add --from-plan` immediately after `trader-exit` creates a plan to register stop, target, and flat-by-close alerts.
2. **Periodic Checks**: Schedule `python3 alerts.py check` periodically (e.g., every few minutes via loop or cron) while positions remain open.
3. **Notify & Act**: When an alert fires, check open positions via `trader-broker`. A "flat by close" alert prompts manual position closing via `trader-broker flatten` followed by `trader-risk` review.

## 🛡️ Safety & Guardrails

- **Information Only**: Alerts report objective price and clock facts. This tool never places, modifies, or cancels orders, and never predicts price movement.
- **Execution Safeguards**: Only `trader-broker` can place orders, and only when three conditions hold: `trader-risk` passes the exact order, the user explicitly confirms with "yes" in chat, and tool permissions require interactive approval.
- **Paper Trading Default**: Safe simulation mode by default (`"paper": true`).
- **No Leveraged Products**: No options, margin, short selling, or leverage unless explicitly configured and confirmed.
- **Credential Protection**: Broker API keys must remain strictly in environment variables or configuration files—never in chat.

---

[← Back to Day Trader Skill](../README.md)
