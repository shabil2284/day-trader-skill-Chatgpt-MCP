# Broker Portfolio Audit

## Findings
- **API Status**: Failing with **401 Unauthorized**.
- **Root Cause**: Missing `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`.
- **Requirement**: Load valid credentials into the environment (`.env.save`) to authenticate against `https://paper-api.alpaca.markets`.
