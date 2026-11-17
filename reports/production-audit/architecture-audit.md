# Architecture & Dependency Audit Report

## System Architecture
The Day Trader AI system follows a decoupled dual-server Model Context Protocol (MCP) architecture:
1. **Analysis MCP Server (`chatgpt-mcp/server.py`)**: Runs on port 8000. Exposes 20 read-only analysis tools (market scanners, news, entry checks, exits, fundamentals, pricing, alerts, congress trades) and read-only market data/account readers.
2. **Execution MCP Server (`chatgpt-mcp/execution_server.py`)**: Runs on port 8001. Exposes 11 execution and state-management tools (positions, order proposals, submission approval with crypto-hashing, reconciliation, broker status).
3. **Tunnel Clients (`analysis-tunnel`, `execution-tunnel`)**: OpenAI MCP tunnel-client v0.0.20 instances expose local streamable HTTP endpoints securely to ChatGPT via the control plane.

## Dependency Map
- **Python**: 3.11-slim container base.
- **MCP Framework**: `mcp` SDK with `FastMCP` and `streamable_http` transport.
- **External Broker API**: Alpaca Paper Trading REST API (`https://paper-api.alpaca.markets/v2`).
- **Data Sources**: Yahoo Finance (unofficial chart APIs), SEC EDGAR XBRL facts API (`data.sec.gov`).
- **State Management**: Atomic JSON file-based locking (`fcntl.flock`) in `trader/` directory.

## Verified Architecture Properties
- **Isolation**: Analysis and Execution capabilities are cleanly separated across distinct ports and processes.
- **Safety**: Live trading is disabled (`ALPACA_LIVE_TRADING_ENABLED=false`), order submission requires explicit cryptographic approval phrases, and all destructive actions are guarded against unauthorized execution.
