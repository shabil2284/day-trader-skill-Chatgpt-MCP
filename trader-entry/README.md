# ⏱️ **trader-entry**

*Watches a setup bar by bar and signals the exact moment a breakout confirms.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## ⚡ What It Does

`trader-entry` is an intraday entry timer that monitors stock setups bar by bar and detects the precise moment a trade triggers. It reads free 1-minute or 5-minute Yahoo Finance bars and waits for a completed bar to close strictly above an opening range high or a specified breakout level. When triggered, it logs the exact time and price to `trader/entry.json` for downstream risk and exit planning without ever placing an order.

## 🚀 Quick Start

```bash
# Check TSLA against a 15-minute opening range using 5-minute bars
python3 entry.py check TSLA

# Check TSLA and save trigger details to trader/entry.json for /trader-exit
python3 entry.py check TSLA --write

# Check breakout against an explicit price level (e.g. 20-day high)
python3 entry.py check TSLA --setup level --level 371.20

# Check 1-minute bars requiring trigger volume 1.5x the opening range average
python3 entry.py check TSLA --interval 1m --min-volume-x 1.5

# Watch bar by bar in real time, stopping automatically on trigger
python3 entry.py watch TSLA --until 15:30

# Check every candidate found in trader/watchlist.json
python3 entry.py watchlist

# Replay an intraday session offline with simulated time
python3 entry.py watch TSLA --offline tsla_bars.json --now "2026-10-19 10:15"
```

## 📂 What It Reads & Writes

| File | Purpose |
| --- | --- |
| `trader/watchlist.json` | Reads scanner candidates (`hits[].symbol`) when running `entry.py watchlist` |
| `trader/config.json` | Reads optional session entry windows (`no_entries_before`: 09:45, `no_entries_after`: 15:30 ET) |
| Yahoo Finance Chart API | Fetches free intraday 1m or 5m price and volume bars (unofficial, subject to latency) |
| `trader/entry.json` | Writes trigger state on `--write` or when `watch` triggers (symbol, setup, status, time, price, level, opening range) |

## 📐 Entry Rules

- **Opening Range Breakout (ORB):** Uses the high and low of the first 15 minutes (9:30–9:45 AM ET: three 5m bars or fifteen 1m bars). The hurdle to beat is the range high.
- **Specific Level:** An absolute price ceiling provided via `--level` (such as a multi-day resistance from `/trader-scanner`).
- **Closed Bars Only:** Only fully completed bars qualify. Intra-bar wicks and live tick penetrations do not count.
- **Strict Trigger:** The bar must **close strictly above** the level. Closing exactly at the level is not a trigger.
- **Volume Confirmation (Optional):** When `--min-volume-x` is configured, trigger bar volume must exceed the opening range average volume by the specified multiple.
- **Time Window:** Entries are rejected before 09:45 AM ET (range formation) and after 15:30 PM ET (or 12:30 PM on early-close days).
- **Long Side Only:** Focuses solely on long breakout setups.
- **Single Trigger:** Triggers once per setup per day on the initial qualifying close.

## 🔄 Workflow Steps

1. **Pick a Symbol:** Identify a candidate from `/trader-scanner` or run `entry.py watchlist`. Check `/trader-news` first.
2. **Check Status:** Run `entry.py check SYMBOL` to see whether the setup is waiting, triggered, or expired.
3. **Monitor Live:** Run `entry.py watch SYMBOL --until 15:30` in the background to alert on the first closed bar breakout.
4. **Handoff to Exit:** Once triggered, hand off immediately to `/trader-exit` to calculate stops and profit targets before executing any order.

## 🚫 What It Never Does

- **Never places orders:** Generates informational signals only; never executes broker transactions.
- **Never sizes positions:** Position sizing is reserved for `/trader-budget`.
- **Never sets stop losses:** Stop loss and target calculations belong strictly to `/trader-exit`.
- **Never anticipates closes:** Will never jump the gun on an incomplete bar that looks like it might close above.
- **Never modifies levels post-breakout:** Levels remain fixed once determined.

## 🛡️ Safety

- **Educational Tooling:** Provided for education and systematic trade timing, not financial advice.
- **Paper Trading Default:** Default system configuration operates with `"paper": true`.
- **Explicit Human Approval:** No tool in the Day Trader suite places live orders except `/trader-broker`, requiring explicit confirmation and human verification.
- **Conservative Guardrails:** No options, margin, short selling, or leverage without explicit configuration and confirmation.
- **Secure Credentials:** Broker API keys belong in environment variables or desktop app config, never exposed in chat.

---
[← Back to Day Trader Skill](../README.md)