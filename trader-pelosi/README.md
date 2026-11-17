# 🏛️ **trader-pelosi**

*Track, fetch, and parse public congressional stock trade disclosures under the STOCK Act as soon as they are filed.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 🔍 What it does

Monitors the House Clerk's public disclosure feed and alerts the moment members of Congress file new Periodic Transaction Reports (PTRs). It downloads and parses filing PDFs into clean, structured records detailing the filer, asset, transaction type, options contracts, dollar ranges, and disclosure delays. Built with standard library Python and zero external dependencies, it provides rapid visibility into public disclosures with built-in awareness that trades are days or weeks old.

## ⚡ Quick Start

```bash
# Check filings for a specific member in the current year
python3 ptr.py index --member pelosi

# Check all member filings since a date or search a previous year
python3 ptr.py index --since 2026-10-01
python3 ptr.py index --member "Josh Gottheimer" --year 2025

# Check for new unseen filings, download PDFs, and parse rows (exit code 1 if none)
python3 ptr.py new --member pelosi --read

# Download a specific PTR PDF by DocID and display parsed rows
python3 ptr.py fetch 20035143

# Parse pdftotext layout output into structured JSON
python3 ptr.py parse ptr.txt --filed 2026-08-21 --json
```

## 📂 What it reads & writes

| File | Purpose |
| --- | --- |
| `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/<YEAR>FD.zip` | Annual disclosure ZIP index containing `<YEAR>FD.xml` with member filings |
| `https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/<YEAR>/<DocID>.pdf` | Individual Periodic Transaction Report (PTR) PDF documents |
| `trader/state/pelosi.json` | State tracking processed DocIDs to ensure each PTR alerts only once |
| `trader/state/ptr-pdfs/` | Local cache directory storing downloaded PTR PDF files |
| `trader/portfolio.json` | Optional portfolio file read to flag congressional trades matching your holdings |

## 📜 Filing Rules & Interpretations

- **Quote the filing, not a tracker**: Every row comes directly from the official PTR PDF on the Clerk's site with its DocID and link. Third-party trackers can introduce date and value errors; the official PTR always wins.
- **Amounts are ranges**: Stated in statutory valuation bands (e.g., "$1,000,001 - $5,000,000"), never as an exact dollar figure.
- **Owner matters**: Identifies ownership (`SP` for spouse, `JT` for joint, `DC` for dependent child, blank for the member).
- **Say the delay**: Calculates elapsed days between transaction date and filing date; flags trades disclosed past 45 days as late.
- **Options are options**: Explicitly parses contracts, strike prices, expiration dates, and exercises rather than treating them as underlying share purchases.

## 🔔 Alert Example

```
NEW Periodic Transaction Report: Hon. Nancy Pelosi (CA11) filed 2026-08-21, doc 20035143
  - spouse purchase, Bloom Energy Corporation Class A Common Stock (BE): 100 call
    options, $100 strike, expires 2027-06-17, $1,000,001 - $5,000,000, traded
    2026-07-24, disclosed 28 days later
```

> **Note**: Disclosures reflect trades made weeks earlier. A filing provides historical context to evaluate a chart, not an immediate trade setup.

## 🏛️ Senate Filings (Manual Route)

Senate reports at `https://efdsearch.senate.gov` require users to manually accept terms before accessing records. To respect site agreements:

1. Open `https://efdsearch.senate.gov/search/` and accept the agreement.
2. Select **Periodic Transactions**, enter the senator's last name, and set the date range.
3. Open the electronic filing table or scanned PDF report.
4. Paste the table or screenshot into the chat to parse into standard rows with report links and the 45-day delay calculation.

## 🚫 What It Never Does

- Never claims or implies a member has inside information, or that copying politicians beats the market.
- Never presents value ranges as exact dollar totals or third-party tracker dates as execution dates.
- Never executes trades or replicates options positions automatically.
- Never automates terms-of-service agreements, CAPTCHAs, or site logins.

## 🛡️ Safety & Workflow

- **Education and tooling only**: Nothing in this pack is financial advice or a recommendation to buy or sell securities.
- **Paper trading by default**: Enabled via `"paper": true` in `trader/config.json`.
- **Strict execution guardrails**: Orders require validation across `/trader-scanner`, `/trader-entry`, `/trader-budget`, and `/trader-risk`. Orders are sent only via `/trader-broker` after explicit user chat confirmation and approval prompts.
- **Public STOCK Act data only**: Filings are historical disclosures submitted up to 45 days after execution; the tool reads them quickly with zero inside information.

---

[← Back to Day Trader Skill](../README.md)
