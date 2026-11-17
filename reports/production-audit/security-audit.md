# Security Audit Report

## Security Posture
- **Secret Management**: `.env` and `.env.save` contain credentials and are excluded from Git version control. (Recommendation: rotate keys found in `.env.save`).
- **Network Binding**: Docker Compose port mappings for MCP servers are bound strictly to `127.0.0.1` (`127.0.0.1:8000:8000`, `127.0.0.1:8001:8001`), preventing unintended public exposure on host network interfaces while maintaining internal Docker bridge connectivity for tunnels.
- **Trading Safety**: Live trading flags are permanently disabled (`ALPACA_LIVE_TRADING_ENABLED=false`). Order submission requires cryptographic verification.
- **Data Privacy**: No API secrets or tokens are exposed in logs or MCP tool responses.
