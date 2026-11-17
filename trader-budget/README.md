# 💰 **trader-budget**

*Sizes every position to your budget and max loss per trade, turning trade plans into safe, risk-bounded bracket orders.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 💡 What it does

`trader-budget` converts trade plans into exact, whole-share position sizes governed by your predefined risk parameters and account limits. It evaluates four financial boundaries—maximum loss per trade, position allocation percentage, maximum order amount, and available cash after your safety buffer—and selects the most conservative share count, explicitly stating which constraint decided the size. Sizing outputs a single proposed bracket order formatted for Alpaca's `place_stock_order` (entry, stop-loss, and take-profit) written to `trader/orders.json` for downstream risk verification without executing transactions.

## 🚀 Quick Start

```bash
# Calculate position size using trader/plan.json and trader/config.json
python3 size.py

# Calculate size and write proposed bracket order to trader/orders.json
python3 size.py --write

# Size as a limit order at the plan's entry price instead of a market order
python3 size.py --limit --write

# Specify an explicit limit price and output machine-readable JSON
python3 size.py --limit 364.00 --json

# Pin the clock to a specific New York timestamp to test historical plans
python3 size.py --now "2026-10-19 10:15" --write

# Weights mode: split budget across multiple tickers by percentage
python3 size.py --weights AAPL=40,KO=60 --config split.json

# Rebalance from a target allocation file using whole shares and fresh quotes
python3 size.py --targets targets.example.json --whole-shares --prices trader/prices.json
```

## 📂 What it reads & writes

| File | Purpose |
| --- | --- |
| `trader/config.json` | Account rules: budget, cash buffer percentage, max loss per trade, position/order limits, and trading windows. |
| `trader/plan.json` | Intraday trade plan from `trader-exit`: entry, stop, target, setup type, and flat-by time. |
| `trader/prices.json` | *(Optional)* Fresh quote from `trader-alerts`; higher market prices widen stop risk and reduce share count. |
| `trader/portfolio.json` | *(Optional)* Account cash balance from `trader-broker` to cap order size to available funds. |
| `trader/orders.json` | Proposed bracket order payload (entry, stop-loss, take-profit) written when invoked with `--write`. |

## ⚖️ The Four Sizing Limits

Alpaca bracket orders require whole shares. The final position size is strictly the smallest share count derived from four independent limits:

| Limit | Formula | Description |
| --- | --- | --- |
| **Max Loss** | `max_loss_per_trade_usd / (entry - stop)` | Limits total loss at the stop price to your predefined risk threshold. |
| **Position Cap** | `(budget * max_position_pct) / entry` | Restricts concentration so no single trade exceeds the portfolio cap. |
| **Max Order** | `max_order_usd / entry` | Caps the gross dollar exposure per single order. |
| **Cash Buffer** | `(budget - cash_buffer) / entry` | Preserves a cash buffer (never exceeding cash in `trader/portfolio.json`). |

## 🚫 Refusal Conditions

`trader-budget` refuses to generate an order and outputs a single-line explanation when:
- **Stop too wide:** Risk per share exceeds `max_loss_per_trade_usd`, resulting in zero shares (it never shrinks a stop to force a fit).
- **Below minimum order:** Total order value is less than `min_order_usd` ($5).
- **Sub-par reward-to-risk:** Reward:risk ratio is below `min_reward_risk` (e.g. if the market price ran up toward the target).
- **Invalid geometry:** Stop is not strictly below the entry price, or target is not strictly above the entry.
- **Outdated plan:** The plan is dated for another calendar day.
- **Disallowed trade:** The symbol is in the `blocked` list, or the setup specifies a short position.

## 📊 Weights Mode (Portfolio Allocation)

`size.py` supports multi-asset allocations using `--weights` or `--targets FILE` (such as `targets.example.json`):
- Automatically deducts the cash buffer off the top.
- Renormalizes allocation weights to 100%.
- Caps any single holding at `max_position_pct` and redistributes the excess across remaining assets.
- Discards slices falling below `min_order_usd` and rounds amounts to whole dollars or whole shares (`--whole-shares`).

## 🛑 What it never does

- **Never places or approves orders:** Creates proposals only; never interacts directly with broker APIs.
- **Never widens limits:** Never overrides user budget, cash buffer, or loss thresholds.
- **Never shrinks stops:** Will refuse a trade rather than compress a stop to squeeze into share limits.
- **Never trades complex instruments:** No options, margin, short selling, or leverage sizing.
- **Never guesses data:** Every parameter is strictly sourced from configuration, plan, or price files.

## 🛡️ Safety

- **Education & Tooling:** Provided for systematic trade planning, not financial advice. A sizing pass is a mathematical check, not a trade recommendation.
- **Paper Trading by Default:** Configuration defaults to `"paper": true`. Live deployment requires explicit user configuration.
- **Three-Gate Execution:** No order is submitted until `trader-risk` passes the order, the user explicitly confirms "yes" in chat, and Claude's tool approval prompt is accepted.
- **Credential Protection:** Broker API keys must remain in local environment variables or Desktop configuration, never transmitted in conversation.

---
[← Back to Day Trader Skill](../README.md)