# 📈 **day-trader-skill-Chatgpt-MCP**

*11 Claude & ChatGPT skills for day trading: scan thousands of charts, track breaking news, time entries/exits, simulate outcomes 10,000 times, and route orders through a triple-gated broker.*

---

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)
![FastMCP](https://img.shields.io/badge/FastMCP-00A67E?style=flat-square&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)

---

## 🚀 Overview

**day-trader-skill-Chatgpt-MCP** bridges advanced Large Language Models (Claude and ChatGPT) directly to financial markets via the Model Context Protocol (MCP), establishing an institutional-grade, risk-managed day trading environment. Powered by 11 modular Python skills, the system continuously scans 5,900+ US equity charts for setups, filters real-time SEC EDGAR filings and breaking news, and pinpoints high-conviction breakout entries with protective exits. Before any trade is executed, the built-in Monte Carlo Time Machine replays 10,000 session paths against historical intraday distributions to compute empirical edge and win probabilities. All execution routes through Alpaca paper trading by default, safeguarded by a triple-layer security model requiring automated risk checks, cryptographic approval tokens, and mandatory human confirmation. By marrying autonomous quantitative scanning with strict human-in-the-loop controls, it turns conversational AI into an analytical, disciplined trading partner without sacrificing safety.

---

## 🛠️ Tech Stack

| Technology | Category | Purpose |
| :--- | :--- | :--- |
| **Python** | Language & Runtime | Core algorithmic calculations, data processing, and asynchronous execution |
| **MCP (Model Context Protocol)** | Open Protocol | Standardized AI interface enabling dynamic tool discovery and function invocation |
| **FastMCP** | Server Framework | High-throughput Streamable HTTP architecture hosting analysis and execution servers |
| **Claude** | AI Assistant | Native integration via Claude Code skills and Claude Desktop configurations |
| **ChatGPT** | AI Assistant | Custom GPT integration and remote MCP server tool discovery |
| **Alpaca API** | Brokerage Execution | Paper-trading default sandbox, order telemetry, and position management |
| **Yahoo Finance** | Market Data | Real-time and historical intraday candle bars, tick feeds, and pricing data |
| **SEC EDGAR** | Regulatory Filings | Real-time 8-K catalyst feeds, quarterly 10-Q statements, and financial facts |
| **Docker** | Containerization | Multi-service isolation for analysis and execution MCP server environments |

---

## ✨ Features

- 🔍 **Full-Universe Market Scanner**: Scans 5,900+ US equities across Nasdaq Trader and Yahoo Finance in seconds to identify opening-range breakouts (ORB), bull flags, and oversold bounces (`/trader-scanner`).
- 📰 **Catalyst & News Intelligence**: Filters breaking financial headlines and real-time SEC EDGAR 8-K filings to steer intraday trades away from surprise earnings or unexpected corporate events (`/trader-news`).
- ⏱️ **Bar-by-Bar Precision Timing**: Monitors intraday candlestick developments bar by bar, triggering entries only on confirmed closes while locking in mathematically defined 1R targets and midpoint stop-losses (`/trader-entry`, `/trader-exit`).
- ⏳ **10,000-Replay Time Machine**: Simulates 10,000 Monte Carlo session replays using 60 days of historical intraday bars and identical past setups to report empirical win rates before risking capital (`/trader-timemachine`).
- 💰 **Mathematical Position Sizing & Budgeting**: Computes exact share quantities tailored to current account equity and fixed dollar risk tolerance, preventing overleveraging or emotional sizing (`/trader-budget`).
- 🛡️ **Rule-Enforced Risk Gatekeeper**: Evaluates max daily drawdown limits, pattern-day-trader (PDT) limits, and reward-to-risk thresholds to issue an automated `PASS` or `BLOCK` verdict before an order is staged (`/trader-risk`).
- 🤝 **Triple-Gated Broker Execution**: Secures order routing to Alpaca Paper Trading through three mandatory gates: automated risk checks, cryptographic verification tokens, and explicit human confirmation (`/trader-broker`).
- 🏛️ **Fundamental & Congressional Alpha**: Queries SEC EDGAR for quarterly EPS growth and financial statements while monitoring US Congressional stock trade disclosures under the STOCK Act in real time (`/trader-analyst`, `/trader-pelosi`).

### 🧩 The 11 Modular Trading Skills

> Every skill in this repository operates standalone via CLI or MCP, and each includes its own dedicated `README.md`.

| Command | Skill | Primary Responsibility | Documentation |
| :--- | :--- | :--- | :--- |
| `/trader-scanner` | **Chart Scanner** | Scans 5,900+ US equities for ORB, flag, and bounce setups | [`trader-scanner/README.md`](trader-scanner/README.md) |
| `/trader-news` | **News Monitor** | Tracks breaking headlines, earnings dates, and SEC 8-K filings | [`trader-news/README.md`](trader-news/README.md) |
| `/trader-entry` | **Entry Timer** | Confirms breakout candle closes and trigger signals bar by bar | [`trader-entry/README.md`](trader-entry/README.md) |
| `/trader-exit` | **Exit Planner** | Computes protective stop-losses, 1R profit targets, and time stops | [`trader-exit/README.md`](trader-exit/README.md) |
| `/trader-timemachine` | **Time Machine** | Simulates 10,000 Monte Carlo replays using historical intraday data | [`trader-timemachine/README.md`](trader-timemachine/README.md) |
| `/trader-budget` | **Budget Manager** | Sizes share limits based on account balance and dollar risk limits | [`trader-budget/README.md`](trader-budget/README.md) |
| `/trader-risk` | **Risk Gatekeeper** | Enforces daily loss limits, PDT guard rules, and R:R thresholds | [`trader-risk/README.md`](trader-risk/README.md) |
| `/trader-broker` | **Order Gateway** | Generates plain-language tickets; routes to Alpaca paper sandbox | [`trader-broker/README.md`](trader-broker/README.md) |
| `/trader-alerts` | **Alert System** | Monitors stop/target levels and flags the 3:55 PM ET market flatten | [`trader-alerts/README.md`](trader-alerts/README.md) |
| `/trader-analyst` | **Earnings Analyst** | Parses SEC EDGAR 10-Q/10-K financial statements and revenue facts | [`trader-analyst/README.md`](trader-analyst/README.md) |
| `/trader-pelosi` | **Pelosi Tracker** | Monitors US Congressional stock trade disclosures (STOCK Act PTRs) | [`trader-pelosi/README.md`](trader-pelosi/README.md) |

### 🛡️ Triple-Gated Broker Protection

To protect capital and guarantee peace of mind, every order passes through three non-negotiable security layers:

```text
[ Proposed Order ]
       │
       ▼
 ┌───────────┐
 │  GATE 1   │ ──► Algorithmic Risk Check (/trader-risk validates drawdown, PDT, and R:R)
 └─────┬─────┘
       │ PASS
       ▼
 ┌───────────┐
 │  GATE 2   │ ──► One-Time Cryptographic Token (Generates random approval phrase with 300s TTL)
 └─────┬─────┘
       │ TOKEN VALID
       ▼
 ┌───────────┐
 │  GATE 3   │ ──► Explicit Human Confirmation (You review ticket & type "yes" in chat/terminal)
 └─────┬─────┘
       │ CONFIRMED
       ▼
[ Alpaca Paper Sandbox Fill ]
```

---

## ⚡ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/shabil2284/day-trader-skill-Chatgpt-MCP.git
cd day-trader-skill-Chatgpt-MCP
```

### 2. Configure Environment

Copy the configuration template and populate your Alpaca Paper Trading API keys and SEC EDGAR identification:

```bash
cp .env.example .env
```

Ensure `.env` contains your credentials:

```bash
# Alpaca Paper API (Paper trading safe default)
ALPACA_PAPER_API_KEY=your_alpaca_paper_key
ALPACA_PAPER_SECRET_KEY=your_alpaca_paper_secret

# SEC EDGAR Requirements (Name and Email for compliance)
SEC_USER_AGENT="YourName your_email@example.com"
```

### 3. Launch MCP Servers

Start the dual FastMCP microservices (Analysis on port 8000, Execution on port 8001):

```bash
# Option A: Run containerized with Docker Compose (Recommended)
docker compose up -d

# Option B: Run locally via Python
python3 chatgpt-mcp/server.py &
python3 chatgpt-mcp/execution_server.py &
```

Verify that the servers are running:

```bash
curl -s http://localhost:8000/status
```

### 4. Connect to Claude or ChatGPT

Install the skills for Claude Code:

```bash
# Copy skill modules to Claude Code configuration
cp -r trader-* ~/.claude/skills/
```

For ChatGPT, add your server URL (e.g., `http://localhost:8000/mcp` or your secure tunnel URL) under **Custom GPTs** or **Developer Settings** > **Add MCP Server**.

### 5. Run CLI Execution & Strategy Tests

Test the standalone skill scripts directly from your terminal:

```bash
# 1. Scan for opening-range breakouts
python3 trader-scanner/scan.py orb --at 10:15

# 2. Check breaking news and catalysts
python3 trader-news/news.py --tickers TSLA --hours 12

# 3. Simulate 10,000 session replays in Time Machine
python3 trader-timemachine/timemachine.py run --write

# 4. Run offline unit and regression test suite
python3 -m unittest discover -s tests -v
```

---

## 📁 Project Structure

```text
day-trader-skill-Chatgpt-MCP/
├── chatgpt-mcp/            # FastMCP servers (Analysis & Execution) and order gateway
│   ├── server.py           # Analysis MCP server (Port 8000)
│   ├── execution_server.py # Execution MCP server (Port 8001)
│   └── order_gateway.py    # Triple-gated Alpaca paper order router
├── trader/                 # Central configuration and shared trading state
├── trader-scanner/         # 5,900+ equity scanner for ORB & breakout setups
├── trader-news/            # Real-time financial headlines & SEC 8-K monitoring
├── trader-entry/           # Bar-by-bar candlestick breakout confirmation
├── trader-exit/            # Protective stop-loss and 1R profit target planner
├── trader-timemachine/     # 10,000 Monte Carlo session replay simulator
├── trader-budget/          # Max dollar-risk and share sizing calculator
├── trader-risk/            # Drawdown limits, PDT guards, and R:R validator
├── trader-broker/          # Plain-language ticket generator & order gatekeeper
├── trader-alerts/          # Stop/target price alerts & 3:55 PM EOD flatten trigger
├── trader-analyst/         # SEC EDGAR 10-Q/10-K financial fact parser
├── trader-pelosi/          # US Congressional stock disclosure tracker (STOCK Act)
├── tests/                  # Offline unit test suite with historical fixtures
├── docker-compose.yml      # Multi-container orchestration for MCP services
├── Dockerfile.mcp          # Container image definition for MCP services
├── .env.example            # Environment variable configuration template
└── README.md               # Repository documentation
```

---

## 📸 Screenshots

> 🖼️ Add screenshots here

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.