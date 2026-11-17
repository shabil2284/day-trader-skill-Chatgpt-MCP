# Dependency Map

- order_gateway.py:
  - .env
  - state/ (json storage)
  - trader-risk/check.py (risk validation)
  - trader/config.json (config)

- execution_server.py:
  - order_gateway.py
  - mcp.server.fastmcp
  - Alpaca API (via order_gateway)

- server.py (Analysis):
  - order_gateway.py
  - mcp.server.fastmcp
  - trader-scanner/scan.py
  - trader-news/news.py
  - trader-entry/entry.py
  - trader-exit/plan.py
  - trader-timemachine/run.py
  - trader-budget/size.py
  - trader-broker/ticket.py
  - trader-alerts/check.py
  - trader-analyst/facts.py
  - trader-pelosi/ptr.py

- Tunnels (Docker Compose):
  - analysis-mcp:8000 -> analysis-tunnel
  - execution-mcp:8001 -> execution-tunnel
