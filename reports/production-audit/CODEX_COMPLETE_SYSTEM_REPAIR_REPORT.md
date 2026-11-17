# Day Trader AI Complete System Repair Report

**Initial audit:** 2026-11-15  
**Latest verification:** 2026-11-16  
**Repository audited:** `/Users/shabil/Downloads/day-trader-skill_Shabil`  
**Overall verdict:** **CONDITIONALLY READY for supervised PAPER testing through the two local servers.** The paper account and read-only broker calls were verified, but no order was submitted, so end-to-end order submission is not certified.

The initial audit below recorded the state on November 15. The November 16 retest supersedes earlier status statements where they differ. No order was approved or submitted, no account-changing endpoint was called, and no credentials or account balances were disclosed.

## Current retest — 2026-11-16

| Check | Latest result |
|---|---|
| Analysis server | Running on `127.0.0.1:18740/mcp`; discovered 20 tools; status shows PAPER enabled, PAPER submission enabled, LIVE disabled. |
| Execution server | Running on `127.0.0.1:18741/mcp`; discovered 11 tools; status shows PAPER enabled, PAPER submission enabled, LIVE disabled. |
| Alpaca PAPER account | Read-only `/account` returned `ACTIVE` and `trading_blocked=false`; `/clock` reported the market closed; `/positions` returned 0 positions. The same getters succeeded through both MCP servers. |
| Guardrails | Both servers rejected LIVE-mode proposals. PAPER buy market orders were rejected; buys require a limit entry with a protective stop and target, and the entry is capped at `$100` notional. |
| Bracket preflight | A valid protected limit-buy preflight reached the risk gate and was blocked only because the US market was closed. It did not persist a proposal. A risk test with a simulated open session passed. |
| Test suite | **419 passed, 0 failed, 0 skipped** (`18.25s`) in an isolated copy. |
| Orders | No Alpaca order endpoint was called; no proposal was stored; the account remains at 0 positions. |

Both host server processes were left running for the user. This verifies the local PAPER configuration, broker read access, tool discovery, and order preflight behavior. It does **not** prove an actual Alpaca order can be accepted or filled: placing a test order would change the account and was not requested. Docker image/container health, tunnels, and the external ChatGPT connector also remain unverified because Docker Engine was unavailable. Optional analysis providers still have their documented prerequisites, including a real SEC contact identity.

The latest order-path repair makes PAPER buy proposals require a limit entry plus both stop-loss and take-profit prices. It sends an Alpaca bracket payload, includes those protection prices in the exact approval phrase, rejects market buys, and keeps the `$100` notional cap. The risk gate receives the entry, stop, and target together. The current weekend preflight was intentionally not persisted because the risk gate correctly rejected entry while the market was closed.

The two servers are suitable for a **supervised first paper-order validation** once the US market is open, using a protected limit buy and the normal explicit approval flow. This is not a claim that every provider-backed analysis tool or the external deployment path is fully working, and it is not a live-trading readiness claim.

## Verdicts

| Area | Verdict | Evidence and limit |
|---|---|---|
| Analysis MCP | **PAPER-READY LOCALLY** | Current loopback Streamable HTTP listener passed tool discovery and read-only PAPER account/clock/positions calls with 20 tools. Scanner was exercised separately. Other provider-backed tools and container health were not verified. |
| Execution MCP | **PAPER-READY LOCALLY, SUBMISSION UNVERIFIED** | Current loopback listener passed discovery, PAPER status and read-only account calls with 11 tools. Bracket preflight and mocked order lifecycle are covered; no order was sent to Alpaca. |
| Market data | **VERIFIED** | Read-only Yahoo daily and 5-minute history plus Nasdaq Trader symbol-directory downloads succeeded. Yahoo is unofficial and not asserted to be real-time; the latest bars were from the prior session. |
| Scanner | **VERIFIED** | Live 10-symbol daily run returned complete diagnostics and a correct zero-candidate status; weekend ORB correctly returned `market_closed`. Offline scanner and parser tests passed. |
| Approval/rejection | **MOCK VERIFIED** | Exact phrase, notional recheck, expiry, rejection, duplicate/concurrent submission protection, mock submission, and reconciliation tests passed. |
| ChatGPT connector | **NOT VERIFIED** | Local host MCP sessions work. The Docker endpoints, tunnels, and connected ChatGPT client could not be reached. |
| Overall | **CONDITIONALLY READY FOR SUPERVISED PAPER VALIDATION** | Local PAPER account access and preflight are verified. End-to-end order submission and external deployment are not. |

The following detailed sections preserve the November 15 baseline and repair notes; statements there that the broker was never contacted, PAPER flags were disabled, or tests numbered 417 describe that earlier state and are superseded by the current retest above.

## Initial condition and root causes

- Paper broker URLs could be overridden by `APCA_API_BASE_URL`; a paper credential could therefore be paired with a live base URL.
- The `$100` ceiling was checked at proposal time but was not recomputed from persisted order data immediately before broker submission.
- State changes made before an exception, including expiry and submission state, could be lost because the state context committed only on normal exit.
- A broker response without an order ID could be treated as a successful submission. A process crash in `submitting` had no reconciliation path.
- Live-mode proposals/submission were not consistently denied, and status could echo the configured live flag as if it were effective policy.
- Proposal retrieval exposed the approval hash and broker payload; execution status also returned a fabricated fixed timestamp.
- Compose did not persist MCP state, and the active image dependency setup could install requirements from the inactive `chatgpt-mcp-new` experiment.
- SEC contact documentation/configuration used placeholder identities, and the active Analysis container did not receive `SEC_USER_AGENT`.
- Position sizing used the caller's current directory for plan files and forwarded stop/target values in a format the exit CLI does not parse.
- Scanner responses did not reliably distinguish zero hits from provider/data failures or explain per-symbol retrieval, freshness, liquidity, and strategy outcomes.
- Test imports relied on a different absolute checkout path, and previous session probes depended on opening a local socket unavailable in this environment.

## Repairs made

- Fixed the PAPER API base URL in code; disabled LIVE proposal/submission paths regardless of environment flag; status reports effective live trading as disabled.
- Recompute and validate persisted order notional, approval integrity, account buying power, and risk immediately before paper submission. Preserve the existing risk/position checks and `$100.00` ceiling.
- Persist state in a `finally` path with atomic replacement and restrictive permissions; retain locking. Reject broker submissions without an ID and allow reconciliation of `submitting`/unknown outcomes.
- Exclude internal approval and payload fields from public proposal responses; report a real `observed_at` timestamp.
- Mount shared MCP state in Compose; pin the active MCP SDK dependency and exclude the inactive experiment, secrets, state, and audit output from the Docker build context.
- Pass `SEC_USER_AGENT` only to the Analysis service. Reject missing or placeholder SEC identities without fabricating contact details.
- Resolve plan paths against the repository root. Validate complete explicit plan inputs and format stop/target arguments correctly; size explicit inputs in a temporary directory without leaving a plan or order file in the project.
- Normalize Yahoo bars and timestamps, reject duplicate timestamps and invalid/inconsistent OHLCV, label source/timing and non-real-time status, and return per-symbol diagnostics. Preserve the `$5` price and 1-million-share daily volume floors.
- Give scanner outcomes separate statuses for candidates, zero candidates, partial data, provider failure, insufficient data, market closed, invalid universe, and invalid input. MCP preserves the scanner JSON in its result envelope and treats a valid zero-hit scan as successful analysis.
- Add structured type/input guards on the affected Analysis and Execution tool handlers. Correct tests to use the supplied checkout dynamically and isolated state.

## Market-data and scanner evidence

The live run used the repository's existing first 10 universe symbols and did not write the universe or watchlist. It ran on Sunday, November 15, 2026, so Yahoo's latest completed daily session was Friday, November 13. All daily results are explicitly marked `real_time: false`.

| Symbol | Price | Volume | Liquidity | Strategy/result |
|---|---:|---:|---|---|
| A | $173.96 | 1,347,542 | Pass | Evaluated; no existing strategy signal |
| AA | $39.74 | 2,779,350 | Pass | Evaluated; no existing strategy signal |
| AAC | $9.95 | 276 | Reject | Volume below 1,000,000 |
| AACG | $0.7767 | 2,154 | Reject | Price below $5.00; volume also below floor |
| AACI | $10.115 | 53,352 | Reject | Volume below 1,000,000 |
| AACO | $10.045 | 118 | Reject | Volume below 1,000,000 |
| AACP | $10.11 | 6 | Reject | Volume below 1,000,000 |
| AADX | $8.38 | 1,757,685 | Pass | Evaluated; no existing strategy signal |
| AAL | $13.17 | 55,538,581 | Pass | Evaluated; no existing strategy signal |
| AAME | $1.26 | 31,959 | Reject | Price below $5.00; volume also below floor |

The result was **10 fetched, 6 illiquid, 4 evaluated, 0 hits**, `scan_status: success_zero_candidates`, `ok: true`, and CLI `exit_code: 1` (the scanner's documented no-hit exit code). Each daily diagnostic carried Yahoo source, a bar timestamp, session date, freshness, price/volume, liquidity result, strategy status, and reason. The shared Yahoo daily bar timestamp was `2026-11-13T14:30:00Z`; the scan identifies its completed-session date as November 13. Thresholds were unchanged.

Additional read-only provider checks:

- Yahoo SPY 5-minute history: **390 bars**, November 9 through November 13; last bar `2026-11-13T21:00:00Z`, close `$754.37`. It was not current-session data.
- Nasdaq Trader `nasdaqlisted.txt` and `otherlisted.txt`: **13,286 rows parsed**, **5,932 symbols retained**. Ran with `--no-write`; `trader/universe.txt` was not regenerated.
- ORB on Sunday returned `market_closed` with no attempt to present stale bars as a current-session signal.
- Existing offline daily/ORB fixtures, strategy logic, duplicate-timestamp validation, and malformed OHLCV handling passed in the test suite.

Yahoo's free endpoints are unofficial and may lag; provider delay is unknown. Intraday current-session behavior could not be observed while the market was closed. No rate-limit event occurred during these small provider checks; retry behavior is covered by code/tests, not by a live rate-limit event.

## MCP tool-by-tool results

All 31 tools were discovered through the MCP SDK. The table distinguishes local/mock evidence from external calls deliberately not made.

### Analysis MCP — 20 tools

| Tool | Result |
|---|---|
| `server_status` | Local handler returned running; paper credential presence is true, live credential presence false, and effective LIVE trading false. No credential value was emitted. In the local non-Compose process, paper submission flags are disabled. |
| `get_account` | Schema and mode validation reviewed. No broker endpoint was contacted. |
| `get_market_clock` | Schema and mode validation reviewed. No broker endpoint was contacted. |
| `get_positions` | Schema, response shape, and mode validation reviewed. No broker endpoint was contacted. |
| `propose_order` | Mocked PAPER proposal tests pass; LIVE proposal is rejected. |
| `approve_and_submit_order` | Mocked submission tests pass, including exact phrase verification and the immediate cap/risk recheck. |
| `reject_order` | Mocked rejection lifecycle tests pass; rejected proposal cannot submit. |
| `reconcile_order` | Mocked found/not-found reconciliation tests pass; no real order was queried. |
| `list_order_proposals` | Handler/state behavior covered by isolated lifecycle tests; no repository state was modified. |
| `scan_market` | Live 10-symbol daily result above; wrapper returned nested scanner payload, `success_zero_candidates`, `ok: true`, `exit_code: 1`. |
| `get_market_news` | Registered and handler reviewed; not called against its external news source in this verification. |
| `check_entry` | Registered; underlying entry strategy/regression fixtures passed. No live entry check was made while the market was closed. |
| `plan_exit` | Registered; existing exit fixtures passed. Explicit plan forwarding was corrected; no project plan was created. |
| `backtest_strategy` | Registered; MCP schema exposes optional `symbol`; historical Time Machine tests passed. No live/provider backtest was run. |
| `check_risk` | Risk engine tests passed. The project has no `trader/orders.json`, so current project risk state was not synthesized. |
| `calculate_position_size` | Explicit-input sizing and missing-plan behavior tested with temporary files; no persistent plan/order was written. Current `trader/plan.json` is absent. |
| `show_order_tickets` | Registered; current order tickets were not displayed because `trader/orders.json` is absent. No ticket was created. |
| `check_price_alerts` | Registered; no alert configuration file is present, so no current alert result was claimed. |
| `get_company_fundamentals` | Blocked by placeholder SEC contact configuration; handler rejects it before network access. Genuine user-supplied identity is required. |
| `check_congress_trades` | Registered and input validation reviewed; external congressional disclosure source was not queried. |

### Execution MCP — 11 tools

| Tool | Result |
|---|---|
| `get_execution_server_status` | Local handler returned running; paper credential presence true, live false, and effective LIVE trading false. No credential value was emitted. |
| `get_execution_status` | In-process tool call succeeded and returned an actual `observed_at`; session stability test passed. Isolated state was used for the test. |
| `get_order_proposal` | Public response omits approval hash and broker payload. No real proposal was exposed or changed. |
| `get_account` | Schema/mode validation reviewed; broker endpoint not contacted. |
| `get_market_clock` | Schema/mode validation reviewed; broker endpoint not contacted. |
| `get_positions` | Schema/mode validation reviewed; broker endpoint not contacted. |
| `propose_order` | Mocked PAPER lifecycle tests pass; LIVE is denied. |
| `approve_and_submit_order` | Mock PAPER submission, exact approval, cap recheck, and concurrent duplicate prevention tests pass. |
| `reject_order` | Mock rejection tests pass; rejected proposals cannot submit. |
| `reconcile_order` | Mock reconciliation tests pass for found and not-found cases; real broker reconciliation was not attempted. |
| `list_order_proposals` | Isolated lifecycle/state tests pass; no real broker state was accessed. |

## MCP session and connectivity

`chatgpt-mcp/tests/test_mcp_sessions.py` uses the installed SDK's Streamable HTTP client against each server's ASGI app. It discovered **20 Analysis** and **11 Execution** tools, checked key schemas, invoked an expected broker-disabled error, then made a later status call on the same initialized session. Both sessions remained usable.

Both host processes were also started directly on loopback using the configured Python entry points: Analysis at `127.0.0.1:18740` and Execution at `127.0.0.1:18741`. A real MCP SDK Streamable HTTP client initialized each listener, listed all tools (20/11), called each server's status tool, sent an invalid-mode `get_account` call, then made another status call on that same session. All calls returned HTTP 200; both sessions stayed usable. Execution status reported zero active/pending proposals. No broker endpoint was contacted.

Docker Compose syntax validation passed. Docker CLI version was 29.9.1, but its server response ended in `EOF`; `docker compose build analysis-mcp execution-mcp` could not proceed. Therefore no image was rebuilt, no container was recreated, and container health, tunnel forwarding, and external ChatGPT connector behavior remain unverified. The prior `Session terminated` symptom was not reproduced on these host listeners, but cannot be declared fixed for the actual connector without that runtime test.

## Order safety evidence

Order-lifecycle tests used temporary state and a mocked broker. The suite includes:

- `$100.00` accepted and `$100.01` rejected, plus a persisted-order tamper test proving the cap is checked again immediately before submission.
- Fixed PAPER endpoint despite a live URL override; LIVE proposal/submission rejected even if the live flag is set.
- Correct and incorrect approval phrases; rejected and expired proposals cannot submit.
- Concurrent approval submits once; duplicate requests are blocked by state locking.
- Mock submission without an order ID is treated as uncertain/failure; mock reconciliation covers found and not-found outcomes.
- A crash-state regression verifies reconciliation from `submitting`; expired-state persistence and concurrent locking are tested. State writes use atomic replacement and restrictive permissions.

No order endpoint on Alpaca was called. The local process reported paper trading and order submission disabled; Compose declares those PAPER flags enabled and LIVE disabled, but the services could not be started to verify that runtime environment.

## Full test suite

The complete suite ran from an isolated temporary copy, excluding `.env`, `.env.save`, virtual environments, and repository state. Result: **417 collected, 417 passed, 0 failed, 0 skipped** (`18.24s`). The run included scanner fixtures and parser validation, risk/budget/position sizing, order lifecycle and reconciliation, MCP schemas/sessions, and regression coverage. Docker integration could not be performed because Docker Engine returned `EOF`.

## Files changed in this repair

- `.dockerignore`
- `Dockerfile.mcp`
- `docker-compose.yml`
- `chatgpt-mcp/order_gateway.py`
- `chatgpt-mcp/server.py`
- `chatgpt-mcp/execution_server.py`
- `trader-scanner/scan.py`
- `chatgpt-mcp/tests/test_order_gateway.py`
- `chatgpt-mcp/tests/test_execution_server_status.py`
- `chatgpt-mcp/tests/test_mcp_sessions.py` (new)
- `tests/test_calculate_position_size.py`
- `tests/test_order_audit.py`
- `tests/test_order_proposal_audit.py`
- `tests/test_scanner.py`
- `tests/test_scanner_fixes.py`
- `tests/test_regression.py`
- `tests/test_repo.py`
- `tests/test_risk.py`
- `reports/production-audit/CODEX_COMPLETE_SYSTEM_REPAIR_REPORT.md` (this report)

The following pre-existing project files were preserved: `.env`, `.env.save`, `trader/config.json`, `trader/entry.json`, `trader/universe.txt`, and MCP order state. Tests used separate temporary state.

## Remaining blockers and untested behavior

1. Docker Engine/Buildx is unavailable to this session (`EOF`), preventing image rebuild, container health, tunnel, and actual MCP endpoint verification.
2. The configured `SEC_USER_AGENT` is a placeholder. Supply a genuine contact identity before calling SEC fundamentals; none was fabricated.
3. `trader/plan.json`, `trader/orders.json`, and an alert configuration are absent. Plan/risk/ticket/alert tools must report prerequisites until the user supplies valid state; no fake trading data was generated.
4. Real paper broker account, clock, positions, and order paths were not called. Only the presence of paper credentials was checked; broker connectivity is unverified.
5. News and congressional disclosure providers were not queried. Yahoo daily/intraday history was verified, but data is unofficial and no current-session intraday bars were available on the weekend.
6. Actual ChatGPT connector and tunnel health remain unverified. In-process session success does not establish external connectivity.

No live readiness is claimed.
