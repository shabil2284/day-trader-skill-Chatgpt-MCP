# 🛡️ trader-risk

*Pre-trade risk manager that validates every order against your limits and stops rule breaches before they reach the broker.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 🎯 What it does

The Risk Manager is the gatekeeper between a proposed trade plan and the broker. Every order written by `trader-budget` or `trader-broker`'s flatten tool passes through its pre-trade checks to ensure it complies with your account limits, risk tolerances, and trading schedule. A `BLOCK` verdict is final—the order is never sent to the broker and cannot be overridden, keeping losses small before a single dollar is risked.

## 🚀 Quick Start

```bash
# Check proposed orders in trader/orders.json and record verdicts in trader/state/risk.json
python3 check.py

# Inspect proposed orders without recording verdicts to disk
python3 check.py --no-write

# Output verification results in structured JSON format
python3 check.py --json

# Simulate and verify orders at a specific New York time (EDT/EST)
python3 check.py --now "2026-10-19 10:15"

# Run check with a custom orders file against a specific calendar date
python3 check.py --orders trader/orders.json --today "2026-10-19"
```

## 📂 What it reads & writes

| File | Purpose |
| --- | --- |
| `trader/orders.json` | Proposed orders to validate (from `trader-budget` or `trader-broker` flatten) |
| `trader/config.json` | Account limits, allowed instruments, position caps, and trading windows |
| `trader/portfolio.json` | Current account cash and holdings (defaults to a fresh budget-funded paper account) |
| `trader/prices.json` | Real-time prices used to value holdings and measure worst-case entry slip |
| `trader/state/broker.json` | Daily broker activity log (tracks duplicate orders, daily trade count, and total daily loss) |
| `trader/state/risk.json` | Output verdicts recording PASS/BLOCK decisions alongside order fingerprints |

## 🔄 Entries vs. Exits

- **Entries** (opening or adding to positions, or short sales): Checked against the full suite of risk limits, position caps, daily loss rules, and execution windows.
- **Exits** (reducing existing positions): Getting out of a trade must always be possible. Exits are checked strictly for order format, asset class, and short sale validity. All other checks (window, loss limits, order size, duplicate orders) become non-blocking warnings, never a `BLOCK`.

## 🔍 The Checks

Orders are checked sequentially in file order as if each passed order had filled, catching cumulative limit breaches across batches.

| Check | Blocks When |
| --- | --- |
| `format` | Missing symbol or side; invalid quantity/notional; notional on non-market/non-day orders; missing limit price; bracket order not whole shares, not `day`/`gtc`, or missing stop-loss/take-profit |
| `asset` | Option symbols when `allow_options` is false; crypto or non-US stock/ETF tickers |
| `short` | Selling more shares than currently held when `allow_short` is false |
| `blocked` | Symbol is on the `blocked` ticker list (entries only) |
| `size` | Order notional value is below `min_order_usd` or above `max_order_usd` (entries only) |
| `position` | Resulting position would exceed `max_position_pct` of account value (entries only) |
| `cash` | Buy order dips into `cash_buffer_pct` or requires margin without margin enabled (entries only) |
| `stop` | Stop-loss is missing when `require_stop` is true, or placed on the wrong side of entry (entries only) |
| `loss` | Potential loss at the stop (`qty × (entry - stop)`) exceeds `max_loss_per_trade_usd` (entries only) |
| `reward:risk` | Reward-to-risk ratio (`(target - entry) / (entry - stop)`) is below `min_reward_risk` (entries only) |
| `daily loss` | Cumulative max loss of today's placed entries plus this order exceeds `max_daily_loss_usd` (entries only) |
| `trades` | Number of entries placed today reaches `max_trades_per_day` (entries only) |
| `window` | Order placed before `no_entries_before`, after `no_entries_after` (NY time), or market is closed (entries only) |
| `pdt` | More than 3 day trades executed in the last 5 business days (`pdt_guard: true` only; entries only) |
| `duplicate` | Identical symbol and side in the same batch or already placed today (entries only) |
| `daily limit` | Total orders placed today reaches `max_orders_per_day` (entries only) |

## ⚙️ How Risk Is Calculated

- **Dynamic Entry Measurement**: For limit orders, risk is measured from the limit price. For market orders, risk is measured from the **higher** of the plan's entry price and a fresh quote in `trader/prices.json` (< 15 minutes old), preventing a stale plan from understating risk after price appreciation.
- **Cumulative Daily Loss**: Every entry placed today counts its full maximum potential loss at the stop toward `max_daily_loss_usd`, win or lose. Three full-size trade losses exhaust a $150 daily budget.
- **Trading Window (New York Time)**: Evaluated in America/New_York time with daylight saving support, NYSE holidays, and 1:00 PM early close adjustments. Set both `no_entries_*` to `null` to disable.
- **PDT Guard**: Optional protection (`pdt_guard: false` by default). Counts intraday round-trips plus new entries against the 5-day limit for brokers enforcing legacy pattern-day-trader rules.

## 📋 Execution Workflow

1. **Refresh Prices**: Update quotes if market prices moved (`python3 alerts.py quote TSLA --write`).
2. **Run Risk Check**: Run `check.py` (exit code `0` = all passed, `1` = one or more blocked).
3. **Review Verdicts**: Review the plain-language summary of risk, reward:risk, and daily limit usage.
4. **Broker Gate**: `trader-broker` matches orders against verdicts by exact SHA fingerprint; any modified order must be re-checked.

## 🚦 The Reel: PASS vs. BLOCK

The TSLA bracket order on Monday 2026-10-19 at 10:15 AM on a fresh $5,000 paper account:

```
PASS  #1 buy TSLA 8 shares, entry
          entry 364.18 (the plan's entry), stop 358.32, target 370.04: risk 5.86 a share
          max loss $46.88 (limit $50), reward:risk 1.00 (min 1)
          today before this: 0 of 3 trades, $0 of $150 daily loss

1 passed, 0 blocked at 2026-10-19 10:15 New York. Cash after the passed orders: $2,086.56 (paper account).
```

Adding just 1 additional share triggers a hard `BLOCK`:

```
BLOCK #1 buy TSLA 9 shares, entry
          entry 364.18 (the plan's entry), stop 358.32, target 370.04: risk 5.86 a share
          max loss $52.74 (limit $50), reward:risk 1.00 (min 1)
          today before this: 0 of 3 trades, $0 of $150 daily loss
        - loss: 9 shares x 5.86 risk a share = $52.74 at the stop, over your $50 max loss per trade
```

## 🔒 Safety & Rules

- **What it never does**: Never places an order, never modifies an order to force it to pass, never loosens limits, never blocks an exit sell, and never treats a `PASS` as user approval.
- **Three-lock authorization**: An order only reaches the broker when `trader-risk` passes that exact fingerprint today, the user types an explicit "yes" in chat, and the user approves the brokerage connector prompt.
- **Paper trading default**: Defaults to `"paper": true` in `trader/config.json`.
- **Education & tooling**: Tools and rules checking, not financial advice. A `PASS` is a parameter validation, not a recommendation.

---

[← Back to Day Trader Skill](../README.md)
