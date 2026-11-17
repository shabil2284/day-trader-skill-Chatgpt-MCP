# 📈 The Day Trader skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.x](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Paper Trading Safe](https://img.shields.io/badge/Paper%20Trading-Safe-green.svg)](#)
[![11 Skills](https://img.shields.io/badge/11%20Skills-blue.svg)](#)

11 Claude skills for day trading: scan thousands of charts, track breaking news, time every entry and exit, and replay every outcome before you risk a dollar.

Free, MIT, no signup, no API key. The tools are plain Python that read free
public data: Yahoo Finance charts, Nasdaq Trader's symbol lists, SEC EDGAR
and the House Clerk.

One scans thousands of charts for setups. Another tracks breaking news on
every stock you watch. One watches a setup bar by bar and tells you the moment
to get in, and another sets your stop and your target before you do. And the
craziest one is the Time Machine: before you risk a dollar, it replays the
rest of the session 10,000 times from the stock's own recent bars, plus every
past day the same setup fired, and tells you the honest odds.

And no trade goes through until you say yes. Nothing in this pack can place
an order on its own. Paper trading is the default.

> **Looking for the original Trader skill?** Copy an investor's 13F, the
> stock screener, tax lots and rebalancing live in
> [github.com/Jakeschincariol/trader-skill](https://github.com/Jakeschincariol/trader-skill).
> This repo is its day-trading sequel: the Trader skill v2.

## 📥 Install

Paste this into Claude:

```
https://github.com/Jakeschincariol/day-trader-skill

install skill
```

Or as a plugin, in Claude Code:

```bash
/plugin marketplace add Jakeschincariol/day-trader-skill
/plugin install day-trader-skill@day-trader-skill
```

Claude Code namespaces plugin skills, so installed as a plugin they show up as
`/day-trader-skill:trader-scanner` and so on. Copy the folders instead if you want
plain `/trader-scanner`:

```bash
git clone https://github.com/Jakeschincariol/day-trader-skill.git
cp -r day-trader-skill/trader-* ~/.claude/skills/
```

Project-local instead of global: copy the same folders into your repo's
`.claude/skills/`. No Claude Code at all? Paste any single `SKILL.md` at the
top of a chat and it runs as a mode. You lose the Python tools, but the method
works.

The tools need Python 3.8 or newer. Nothing to pip install. The SEC tools
(news filings, the analyst) ask you to identify yourself: put your name and
email in `trader/config.json` (`"sec_user_agent": "Your Name you@example.com"`)
or in the `SEC_USER_AGENT` environment variable.

## 🛠️ The Eleven

| Command | Job | What It Does |
| --- | --- | --- |
| `/trader-scanner` | Chart Scanner | Scans thousands of charts for setups: opening-range breakouts, flags, oversold bounces. |
| `/trader-news` | News Monitor | Tracks breaking news on every stock you watch and flags what moves it. |
| `/trader-entry` | Entry Timer | Watches a setup bar by bar and tells you the moment to get in. |
| `/trader-exit` | Exit Planner | Sets your stop and your target before you enter, so you know when to get out. |
| `/trader-timemachine` | Time Machine | Replays every possible outcome of a trade before you risk a dollar: 10,000 simulated sessions plus every past time the setup fired. |
| `/trader-risk` | Risk Manager | Checks every trade against your limits and stops anything over them. |
| `/trader-budget` | Budget Manager | Sizes every position to your budget and your max loss per trade. |
| `/trader-broker` | Order Executor | Sends approved orders to your broker, paper trading by default, never without your yes. |
| `/trader-alerts` | Price Alerts | Rings when a price, a stop or the opening bell hits. |
| `/trader-analyst` | Earnings Analyst | Reads earnings reports and sums up what changed. |
| `/trader-pelosi` | Pelosi Tracker | Reads Congress's stock-trade disclosures the minute they are filed. |

## 🗺️ Skill Flow

```text
🔍 Scanner ──► 📰 News ──► ⏱️ Entry ──► 🎯 Exit / ⏳ Time Machine
                                                   │
🔔 Alerts ◄── 🤝 Broker ◄── 🛡️ Risk ◄── 💰 Budget ◄┘
```

```text
┌─────────────────┐
│   🔍 SCANNER    │  Scans 5,900+ US stocks for setups (ORB, flags, bounces)
└────────┬────────┘
         │
         ▼
┌────────┴────────┐
│     📰 NEWS     │  Filters breaking news & SEC filings to avoid catalysts
└────────┬────────┘
         │
         ▼
┌────────┴────────┐
│    ⏱️ ENTRY     │  Watches candles bar-by-bar to confirm exact breakout trigger
└────────┬────────┘
         │
         ▼
┌────────┴──────────────────────────────────────┐
│          🎯 EXIT / ⏳ TIME MACHINE            │
│  • Exit Planner : Sets stop-loss & 1R target  │
│  • Time Machine : Runs 10,000 bar replays     │
└────────┬──────────────────────────────────────┘
         │
         ▼
┌────────┴────────┐
│    💰 BUDGET    │  Sizes exact shares to your max dollar loss per trade
└────────┬────────┘
         │
         ▼
┌────────┴────────┐
│     🛡️ RISK     │  Enforces daily loss limits, PDT rules & reward-to-risk
└────────┬────────┘
         │ [PASS]
         ▼
┌────────┴────────┐
│    🤝 BROKER    │  Shows ticket in plain words; executes ONLY on your "yes"
└────────┬────────┘
         │ [ORDER PLACED]
         ▼
┌────────┴────────┐
│    🔔 ALERTS    │  Rings on stop, target, and 3:55 PM market-close flatten
└─────────────────┘

Scheduled & Fundamental Analysis:
• 📊 /trader-analyst ──► Quarterly financial statements, growth & EPS facts
• 🏛️ /trader-pelosi  ──► Congressional stock trade disclosures (STOCK Act PTRs)
```

## 🚀 How to Use It

Everything lands in a `trader/` folder in your project, and each skill reads
what the last one wrote:

```
scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker   (one trade)
alerts: stop, target, flat by the close                                       (while it is open)
news / analyst / pelosi                                                        (on a schedule)
```

An example, the trade in the reel: Tesla, Monday October 19 2026, real data.

1. **`/trader-scanner`** at 10:15 AM ET: of the 231 charts in the reel's
   scan, 42 had closed above their 15-minute opening range. TSLA is one: range 354.47 to 362.18,
   the 10:10 candle closed at 364.18, 0.55 % over the top.
2. **`/trader-news`**: the morning's TSLA headlines, in New York time
   ("Tesla-SpaceX Merger Mania Strikes Wall Street Ahead of Earnings", 8:04,
   tagged earnings and deal). Tesla reports this week: a day trade is out
   before the close, so it is not exposed to the report.
3. **`/trader-entry`** watched TSLA bar by bar. At 10:12 it said waiting (the
   10:10 bar was still forming). At 10:15 it said triggered: the first
   5-minute close above the range, 364.18.
4. **`/trader-exit`** set the plan before the entry: stop at the range's
   midpoint, 358.32, so 5.86 a share at risk; target one times that risk,
   370.04; flat by 3:55 PM either way.
5. **`/trader-timemachine`** replayed the rest of the day 10,000 times, each
   5-minute candle drawn from TSLA's own candles at that time of day over the
   previous 59 sessions (seed 19, so anyone can repeat it): target first
   29.4 %, stop first 25.5 %, still open at the close 45.1 %. It also re-ran
   the same rule on those 59 real sessions: it fired 33 times, 13 hit the
   target, 15 the stop, 5 neither. Its verdict: close to a coin flip. That is
   the point of looking before you risk a dollar.
6. **`/trader-budget`** with a $5,000 account and a $50 max loss per trade:
   50 / 5.86 = 8 shares ($2,913.44). If the stop fills at 358.32, the loss is
   $46.88. It writes one bracket order: buy 8 TSLA, stop-loss 358.32,
   take-profit 370.04.
7. **`/trader-risk`** checks it against your limits: the max loss, the daily
   loss limit, trades per day, reward to risk, the entry window, position
   size and cash. PASS or BLOCK, with the reason.
8. **`/trader-broker`** shows you the ticket in plain words. You type yes for
   that exact order. Claude calls your brokerage connector (Alpaca's MCP
   server, paper account by default), and Claude's own "Allow once / Deny"
   card asks you one more time.
9. **`/trader-alerts`** rings on the stop, the target and at 3:55 PM to
   flatten whatever is still open.

## 💻 The Tools

All standard-library Python. The data tools read public endpoints and are
polite about it.

```bash
# --- 1. Market Scanning & Setup Discovery ---
python3 trader-scanner/scan.py universe                                # Fetch ~5,900 US stock tickers from Nasdaq Trader
python3 trader-scanner/scan.py daily                                   # Screen whole universe for pre-market setups
python3 trader-scanner/scan.py orb --at 10:15                          # Scan for opening-range breakouts (ORB) up to 10:15

# --- 2. News & Filing Intelligence ---
python3 trader-news/news.py --tickers TSLA --hours 12                  # Track breaking headlines, 8-K filings & today's price action

# --- 3. Entry Timing & Confirmation ---
python3 trader-entry/entry.py check TSLA --setup orb                   # Inspect trigger status: waiting / triggered / expired
python3 trader-entry/entry.py watch TSLA --every 30                    # Stream & watch candles bar-by-bar until trigger fires

# --- 4. Exit Planning & Simulation ---
python3 trader-exit/exit.py plan --stop or-mid --target 1R --write     # Set midpoint stop & 1R target -> trader/plan.json
python3 trader-timemachine/timemachine.py run --write                  # Run 10,000 Monte Carlo replays + historical base rates

# --- 5. Budgeting & Risk Management ---
python3 trader-budget/size.py --write                                  # Size exact shares to max loss limit -> trader/orders.json
python3 trader-risk/check.py                                           # Enforce risk limits & PDT guard (PASS / BLOCK)

# --- 6. Brokerage Execution & Alerts ---
python3 trader-broker/ticket.py show                                   # Review plain-language order tickets (READY / not)
python3 trader-alerts/alerts.py add --from-plan                        # Arm alerts: stop, target, and 3:55 PM market-close flatten
python3 trader-alerts/alerts.py check                                  # Check active alerts and chime on triggered levels

# --- 7. Fundamentals & Political Disclosures ---
python3 trader-analyst/facts.py TSLA                                   # Parse quarterly SEC financial statements, growth & EPS
python3 trader-pelosi/ptr.py index --member pelosi                     # Query Congressional stock transactions (STOCK Act PTRs)

# --- Run Offline Test Suite ---
python3 -m unittest discover -s tests -v
```

The tests run offline, on fixtures cut from real data: TSLA's 5-minute bars
for the 60 days to October 19 2026, the 10:15 AM opening-range scan, Yahoo's
TSLA headlines that morning, the House Clerk's 2026 index, real PTR text and
real XBRL facts. They reproduce every number in the example above.

## ⚠️ Fine Print

**Not financial advice.** This is software that reads public data and does
arithmetic. It does not know your situation and it cannot see the future.
Most people who day trade lose money. You can lose money. Decide for
yourself, and talk to a licensed professional if you need advice.

**No trade goes through until you say yes.** Only `/trader-broker` can lead to
an order, and only after `/trader-risk` passes that exact order and you type
yes for it in the chat. Set your brokerage tool to "Needs approval" in Claude
(Customize, Connectors, tool permissions), never "Always allow", so Claude's
own "Allow once / Deny" card is a second check. No options, margin, short
selling or leverage unless you turn them on.

**Paper first.** `"paper": true` is the default in `config.example.json`, and
Alpaca's MCP server defaults to its paper account. Keys live in environment
variables, never in the chat.

**The Time Machine is a simulation, not a prediction.** It is built from the
stock's own last 60 days of 5-minute bars. The future can do things those 60
days never did: an earnings report, a halt, a headline. Treat its odds as a
reality check, never as a promise.

**A stop is a plan, not a guarantee.** In a fast market or across a gap, a
stop order can fill well past its price. The max loss shown is the loss at
the stop price.

**The data is free and unofficial.** Yahoo Finance's chart endpoint is not an
official API: it can lag, change or rate-limit you. The scanner and the entry
timer read 1-minute or 5-minute bars, not every tick. Check anything that
matters against your broker before you act on it.

**Day-trading rules.** FINRA removed the $25,000 pattern-day-trader minimum
on June 4, 2026 (Regulatory Notice 26-10), and brokers may phase the change
in until October 20, 2027, so yours may still apply the old rule. If it does,
set `"pdt_guard": true` and `/trader-risk` counts your day trades.

**Congress's trades are public, not inside information.** Members must disclose
trades over $1,000 within 45 days (the STOCK Act). The Pelosi skill reads those
public filings the minute they post.

**Taxes.** Day-trading gains are short-term gains, and frequent trading makes
wash sales likely. Nothing here is tax advice.

## 📦 Modules

| Module | Description | Link |
| --- | --- | --- |
| `trader-scanner` | Scan thousands of charts for setups | [README.md](trader-scanner/README.md) |
| `trader-news` | Track breaking news on watched stocks | [README.md](trader-news/README.md) |
| `trader-entry` | Bar-by-bar entry timer | [README.md](trader-entry/README.md) |
| `trader-exit` | Plan stop, target and risk | [README.md](trader-exit/README.md) |
| `trader-timemachine` | 10,000 replay simulations before risking a dollar | [README.md](trader-timemachine/README.md) |
| `trader-budget` | Position sizing | [README.md](trader-budget/README.md) |
| `trader-risk` | Order risk gate | [README.md](trader-risk/README.md) |
| `trader-broker` | Order tickets | [README.md](trader-broker/README.md) |
| `trader-alerts` | Price alerts | [README.md](trader-alerts/README.md) |
| `trader-analyst` | Fundamental facts | [README.md](trader-analyst/README.md) |
| `trader-pelosi` | Congressional trade disclosures | [README.md](trader-pelosi/README.md) |

MIT. Made by [Jake Schincariol](https://opusjake.ai).
