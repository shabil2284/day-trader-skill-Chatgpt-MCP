# 📡 trader-scanner

*High-throughput chart scanner that filters thousands of US equities for opening-range breakouts, bull flags, and oversold bounces.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 🔍 What It Does

`trader-scanner` is the first step in the day trading pipeline, automating the identification of actionable technical chart setups across the market. It curates a universe of US-listed common stocks and ADRs from Nasdaq symbol directories, runs pre-market scans on daily closes, and performs live intraday scans for 5-minute opening-range breakouts. Qualifying symbols are exported directly to `trader/watchlist.json` to feed downstream sentiment analysis (`trader-news`) and execution planning (`trader-entry`).

## ⚡ Quick Start

```bash
# 1. Build the universe of ~5,900 US common stocks & ADRs
python3 scan.py universe

# 2. Run pre-market scan on daily closes (breakouts, flags, bounces)
python3 scan.py daily

# Scan a custom symbol list with liquidity filters
python3 scan.py daily --symbols TSLA,NVDA,AMD --limit 200 --min-price 5 --min-volume 1000000

# 3. Run intraday Opening-Range Breakout (ORB) scan (after 9:50 AM ET)
python3 scan.py orb

# Run ORB cut off at a specific time against an existing watchlist
python3 scan.py orb --at 10:15 --watchlist trader/watchlist.json --json
```

### Key CLI Options

- `--min-price <N>`: Minimum share price filter (default: `5`).
- `--min-volume <N>`: Minimum volume filter (default: `1,000,000` for daily, `0` for ORB).
- `--or-minutes <N>`: Length of the opening range window in minutes (default: `15`).
- `--max-confirm <N>`: Max candidates to verify with full v8 bars in ORB stage 2 (default: `200`, `0` for all).
- `--now "YYYY-MM-DD HH:MM"`: Lock the clock to a specific historical New York time.
- `--offline <PATH>`: Read cached Yahoo finance response files instead of querying live.
- `--show <N>` / `--json` / `--no-write`: Output formatting and write suppression options.
- **Exit Codes**: Returns `0` if setups were found, `1` if no hits or the scan could not run.

## 📂 What It Reads & Writes

| File | Purpose |
| --- | --- |
| `trader/universe.txt` | Output of `universe` (`SYMBOL\|Name` per line); input for `daily` and `orb` scans. |
| `trader/watchlist.json` | Output of `daily` and `orb` scans (`mode`, `as_of`, `hits[]`); consumed by `trader-news` and `trader-entry`. |
| `trader/config.json` | Configuration file read by `orb` for session rules (e.g., `no_entries_after: "15:30"`). |

## 🎯 Daily Setup Rules

Calculated from daily closing prices before market open:

| Setup | Definition |
| --- | --- |
| `breakout_20d` | Last close is higher than every close of the previous 20 trading sessions. |
| `bull_flag` | Gained > 10% over the 10 sessions prior to the last 5, followed by a 5-day consolidation within a 5% range. |
| `reclaim_ma20` | Prior session closed below the 20-day moving average; last close finished back above it. |
| `oversold` | 14-period Wilder RSI drops below 30. |
| `oversold_bounce` | 14-period Wilder RSI was below 30 yesterday and today closed green. |

## ⏱️ Intraday Opening-Range Breakout (ORB)

Evaluates the first `--or-minutes` (default 15 minutes: 9:30, 9:35, and 9:40 AM ET bars) to flag the first completed 5-minute bar closing above the range high:

1. **Stage 1 (Spark Fast Filter):** Batch-scans 5-minute bar closes (20 symbols per request) to identify charts closing at or above the range's highest close.
2. **Stage 2 (High/Low Confirmation):** Pulls full v8 chart data with true highs and lows for top candidates (up to `--max-confirm`, ordered by traded dollar volume) to confirm true breakouts above the range high.
3. **Bar Quality Checks:** Bars must be complete (start + 5 min) and on the 5-minute grid. Incomplete series, trading halts, or off-grid ticks are dropped. Scans are barred outside trading windows or after `no_entries_after`.

## 🌐 Universe Filtering

Downloads `nasdaqlisted.txt` and `otherlisted.txt` from Nasdaq Trader and systematically cleans the roster:
- **Excluded:** Test symbols, ETFs, NextShares, warrants, SPAC units/rights, notes, ETNs, debentures, preferreds (`$` or suffixes like `.U`, `.W`, `.R`), and fixed coupons.
- **Included:** US common stocks, ordinary shares, shares of beneficial interest, and major ADRs/ADS (~5,900 liquid symbols).

## ⚠️ Data & Limits

- **Data Source:** Uses free Yahoo Finance endpoints queried bar-by-bar (not tick-by-tick) with request pacing (0.3s pause) and automatic backoff on HTTP 429.
- **Reporting Integrity:** Partial results are explicitly disclosed (e.g., `"Fetched 4,980 of 5,259 charts"`). Scans never round partial data up to whole-market coverage.
- **Trading Reality:** A scan is a rule-based filter that saves hours of manual charting—it is not a list of stocks to buy, and chart setups are not predictive guarantees. Most day traders lose money; this scanner merely automates pattern discovery.

---

[← Back to Day Trader Skill](../README.md)
