# Market Data & Analysis Audit Report

## Market Data Sources
- **Yahoo Finance**: Powers daily/intraday charts, scanner, and entry checks. Fallback endpoints (`query1`, `query2`) with rate-limit retry logic.
- **SEC EDGAR**: Powers fundamental analysis (`trader-analyst/facts.py`) via XBRL company facts API.

## Audit Findings & Fixes
1. **SEC User-Agent Compliance**: SEC API calls require a valid `SEC_USER_AGENT` environment variable. `server.py` now propagates environment variables correctly to subprocess execution, and `get_company_fundamentals` provides clear error guidance if the variable is missing or set to a placeholder.
2. **Pre-Market Entry Status**: `trader-entry/entry.py` was audited for pre-market handling. Status `waiting` correctly yields exit code `0` to prevent unnecessary pipeline termination during pre-market observation periods.
3. **Position Sizing Prerequisite**: `calculate_position_size` now validates the presence of `trader/plan.json` (created by `trader-exit`) and returns an informative structured error if missing.
