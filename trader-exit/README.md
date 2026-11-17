# 🚪 **trader-exit**

*Sets your stop loss and profit target before you enter, so you always know when to get out.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 🎯 What it does

`trader-exit` is an intraday trade exit planner that predetermines your exact stop-loss and profit target before a trade is entered. It reads the entry trigger from `trader-entry` (or accepts manual price parameters), sets an opening-range midpoint stop by default with a 2R profit target, and rounds all levels away from the entry to the cent. By establishing risk-per-share, reward-to-risk ratios, and strict end-of-day exit deadlines upfront, it writes `trader/plan.json` for downstream position sizing, Monte Carlo simulation, and price alerts without ever placing an order.

## 🚀 Quick Start

```bash
# Plan an exit from trader/entry.json with default opening-range midpoint stop and 2R target
python3 exit.py plan

# Plan with midpoint stop and 1R target, saving the plan to trader/plan.json
python3 exit.py plan --stop or-mid --target 1R --write

# Plan with an opening-range low stop (wider cushion, fewer shares for the same risk)
python3 exit.py plan --stop or-low --target 2R --write

# Plan using an ATR-based stop (1.5x 14-bar ATR from session bars up to the entry)
python3 exit.py plan --stop atr:1.5

# Plan manually by supplying symbol, entry price, and opening range bounds
python3 exit.py plan --symbol TSLA --entry 364.18 --or-high 362.18 --or-low 354.47

# Plan a level breakout setup using a percentage-based stop
python3 exit.py plan --symbol NVDA --entry 190.25 --setup level --stop pct:1 --target 2R

# Inspect the active trade plan currently stored in trader/plan.json
python3 exit.py show

# Output the calculated exit plan directly as structured JSON
python3 exit.py plan --stop or-mid --target 2R --json
```

> **Testing Options**: Use `--now "YYYY-MM-DD HH:MM"` to pin the clock to a specific New York time, or `--offline <FILE>` to load saved Yahoo chart JSON for offline ATR stops.

## 📋 What it reads & writes

| File | Purpose |
| --- | --- |
| `trader/entry.json` | Reads the trigger from `trader-entry` (symbol, entry price, timestamp, bar index, opening range) |
| `trader/config.json` | Reads default exit settings (`flat_by`: 15:55 ET default, `min_reward_risk`: 1.0) |
| Yahoo Finance API | Fetches session bars up to the entry bar for ATR calculations (`atr:K` stop) |
| `trader/plan.json` | Writes the complete trade plan on `--write` (entry, stop, target, risk per share, reward:risk, flat by) |

## 🛑 Stop & Target Rules

### Stop Loss Rules
| Stop Rule | Location & Placement Logic |
| --- | --- |
| `or-mid` | Opening-range midpoint: `(high + low) / 2` (default for opening-range breakouts) |
| `or-low` | Opening-range low: wider stop requiring smaller position sizing for equal max loss |
| `price:X` | Explicit absolute stop price chosen by the trader |
| `pct:X` | `X` percent below the entry price |
| `atr:K` | `K` times the 14-bar ATR under the entry, measured on session bars up to the entry bar |

### Target Rules
| Target Rule | Location & Placement Logic |
| --- | --- |
| `2R` | Default: entry price + 2 × risk per share (`reward:risk` = 2.0) |
| `1R`, `1.5R`, `XR` | Custom multiple `X` times the risk per share (`entry + X × risk`) |
| `price:X` | Explicit absolute profit target chosen by the trader |

### Mathematical Precision & Guardrails
- **Cent Rounding**: The stop rounds away from the entry to the cent (downward for longs: floor). Target rounds half-up to the cent (`entry + R × risk`). Risk per share equals `entry - stop`.
- **Strict Refusals**: Refuses stops at or above entry, targets at or below entry, risk under 0.05% of entry price (too tight to survive the spread), unconfirmed entry files (unless `--entry` is passed), or short setups (v2 plans longs only).
- **Flat-By Deadline**: Defaults to 15:55 ET (or `flat_by` in config). Positions are closed by this time win or lose with no overnight hold. Automatically shifts to 12:55 ET on 1:00 PM early close days. Entries at or after the deadline are refused.
- **Level Setups**: Setups based on specific price levels have no opening range; an explicit stop (`price:X`, `pct:X`, or `atr:K`) is required.

## 🔄 Workflow Steps

1. **Trigger Handoff**: Run `exit.py plan` immediately after `/trader-entry` triggers, or pass `--entry PRICE` to plan ahead at an expected breakout level.
2. **Select Rules**: Use the default midpoint stop (`or-mid`) for opening-range breakouts, or choose an alternate stop rule. Level setups require a named stop.
3. **Write Plan**: Execute `exit.py plan --write` to validate thresholds and persist the plan to `trader/plan.json`.
4. **Downstream Execution**: Hand off to `/trader-timemachine` to simulate trade odds, `/trader-budget` to size shares to your maximum loss, and `/trader-alerts` to monitor stop and target levels.

## 📊 Example: The TSLA Reel

TSLA long on Monday, 2026-10-19. Entry at $364.18 at 10:15 AM ET (the 10:10 bar, bar 8) with an opening range of $354.47 to $362.18:

```bash
python3 exit.py plan --stop or-mid --target 1R --write
```

```
Exit plan: TSLA long, Mon 2026-10-19, opening-range breakout on 5-minute bars
  Entry         $364.18 at 10:15 AM (bar 8)
  Stop          $358.32  opening-range midpoint: ($362.18 + $354.47) / 2 = $358.325, rounded down
  Target        $370.04  1R (one times the risk)
  Risk a share  $5.86 (1.61% of the entry)
  Reward:risk   1.0
  Flat by       15:55 ET, win or lose: no overnight hold
```

*(The default 2R target would be $375.90. Downstream `/trader-budget` sizes the trade: a $50 max risk limit buys `floor(50 / 5.86) = 8` shares).*

## 🚫 What it never does

- **Never places an order**: Calculates exit boundaries only; order routing is strictly reserved for `/trader-broker`.
- **Never sizes a position**: Position sizing is strictly performed by `/trader-budget`.
- **Never widens stops**: Never widens a stop to make an invalid plan pass.
- **Never moves a stop during a trade**: Once planned, a stop is never moved further from the entry.
- **Never promises gains or guarantees fills**: A 1R or 2R target is not a prediction; a stop is a plan, not a guarantee against market gaps or fast slippage.

## 🛡️ Safety

- **Education and Tooling**: Systematic trade planning and tooling, not financial advice. A rules PASS is not a recommendation.
- **Paper Trading Default**: Operates in paper trading mode by default (`"paper": true`).
- **Triple-Gated Broker Protection**: Only `trader-broker` can place orders, requiring `/trader-risk` clearance, an explicit user "yes" in chat, and interactive tool approval.
- **No Leveraged Products**: No options, margin, short selling, or leverage unless explicitly configured and confirmed.
- **Secure Credentials**: Broker API keys must remain strictly in environment variables or desktop configuration files—never in chat.

---

[← Back to Day Trader Skill](../README.md)