# 📊 **trader-analyst**

*Reads audited numbers straight from SEC EDGAR to reveal what actually changed in quarterly earnings, margins, and growth before you trade.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 💡 What It Does

Earnings move stocks more than almost any other catalyst, but corporate press releases often highlight selective metrics. `trader-analyst` extracts standardized XBRL company facts straight from SEC EDGAR (10-Q, 10-K, and 8-K filings) to line up revenue, gross/operating/net margins, net income, and diluted EPS quarter-by-quarter against the prior year. For day traders, it answers two crucial questions before entering a position: what did the last report actually say, and does the next earnings release fall inside the planned trade window?

## ⚡ Quick Start

Runs entirely on standard library Python with no API keys or external dependencies required. Set your SEC User-Agent before calling the tool.

```bash
# Set the required SEC User-Agent (Name email@example.com)
export SEC_USER_AGENT="Your Name you@example.com"

# Analyze the latest earnings report for a ticker (e.g. TSLA)
python3 facts.py TSLA

# Compare multiple stocks across 8 quarters (2 years)
python3 facts.py TSLA NVDA AMD --quarters 8

# Merge TTM metrics (revenue, EPS, margins, growth) into a JSON summary
python3 facts.py AAPL AXP GOOGL KO BAC --metrics trader/metrics.json

# Output full machine-readable JSON format
python3 facts.py AAPL --json

# Look up a company directly by its SEC Central Index Key (CIK)
python3 facts.py --cik 0001318605
```

## 📁 What It Reads & Writes

| File / Resource | Purpose |
| :--- | :--- |
| `trader/config.json` | Reads `sec_user_agent` ("Your Name you@example.com") required by SEC EDGAR (or reads `SEC_USER_AGENT` environment variable). |
| SEC EDGAR XBRL API | Fetches tagged XBRL company facts (`CIK##########.json`), submissions lists, and 8-K Item 2.02 filings with EX-99 earnings press releases. |
| `trader/watchlist.json` | Reads monitored watchlist tickers for batch processing when no symbols are passed on the command line. |
| Earnings Call Transcripts | Ingests user-pasted transcripts to extract management guidance changes, margin trends, and demand commentary. |
| `trader/metrics.json` | Writes trailing twelve months (TTM) revenue, net income, EPS, margins, and YoY growth per ticker when `--metrics` is specified. |

## 📐 The Rules

- **Filed numbers first**: The facts table is built directly from official XBRL filings. Press releases provide supplementary context (guidance, segment color), and the source of each figure is explicitly cited.
- **Compare like with like**: Growth is measured against the same quarter from the previous year to eliminate distortion from seasonal patterns (e.g., holiday retail quarters).
- **Identify derived periods**: Companies do not file a Q4 10-Q. Fourth-quarter figures are derived by subtracting Q1–Q3 from the annual 10-K and are marked "derived" (derived EPS is approximate).
- **Flag filing lag**: If SEC facts data lags behind a newly filed 10-Q or 10-K, the tool emits a note with direct links so you can inspect the filing directly.
- **Highlight one-offs**: When net income exceeds operating income, non-operational items (investment marks, tax credits) are called out. Financial institutions without gross margins are left blank rather than zeroed.
- **Check calendar risk**: If an upcoming earnings release falls inside the planned trade window, it flags the date before stops are placed—stop orders cannot protect against overnight gap risk.

## 🚫 What It Never Does

- Never offers buy or sell opinions, price targets, or valuation judgments (never labels a stock cheap or expensive).
- Never fabricates figures or estimates quarters that cannot be derived from official filings.
- Never queries SEC servers without a valid User-Agent, and strictly respects the 10 requests-per-second limit.

## 🛡️ Safety

Education and tooling, not financial advice. This skill only reads SEC filings. Nothing places an order except `/trader-broker`, after `/trader-risk` passes and the user types an explicit confirmation for that order.

---
[← Back to Day Trader Skill](../README.md)
