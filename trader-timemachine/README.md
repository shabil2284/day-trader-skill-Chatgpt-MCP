# ⏳ **trader-timemachine**

*Replays every possible outcome of a trade across 10,000 simulated sessions and past setups before you risk a single dollar.*

![Python](https://img.shields.io/badge/python-3.x-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## ⏳ What It Does

`trader-timemachine` sits directly between trade planning and capital commitment, stress-testing the entry, stop, and target levels established by `trader-exit`. It reconstructs the remainder of the trading day 10,000 times by randomly sampling the stock's own 5-minute price action across the prior 60 trading days, while simultaneously backtesting the rule against every real historical session. Rather than offering speculative price predictions, it delivers an honest statistical verdict on whether your setup represents a genuine edge or merely a coin flip before handing off to `/trader-budget`.

## 🚀 Quick Start

```bash
# Run 10,000 replays using the active plan in trader/plan.json (default seed: 19)
python3 timemachine.py run

# Run replays and save full distributions to trader/timemachine.json
python3 timemachine.py run --write

# Replay with an early exit cutoff (e.g. flat-by 15:55 ET)
python3 timemachine.py run --until 15:55

# Output machine-readable JSON for downstream pipelines
python3 timemachine.py run --json

# Replay a specific setup directly via CLI arguments
python3 timemachine.py run --symbol TSLA --date 2026-10-19 \
    --entry 364.18 --stop 358.32 --target 370.04 --entry-time "10:15 AM"

# Render an ASCII fan chart visualization from saved simulation results
python3 timemachine.py chart --from

# Run an offline simulation using a cached Yahoo chart JSON fixture
python3 timemachine.py run --offline TSLA-60d5m.json.gz --now "2026-10-19 10:15"
```

## 📂 What It Reads & Writes

| File | Purpose |
| --- | --- |
| `trader/plan.json` | Active trade plan from `trader-exit` (symbol, date, entry, entry time/bar, stop, stop rule, target, target R, opening range) |
| Yahoo Finance Chart API | Fetches 60 days of 5-minute bars (`range=60d&interval=5m`) to build historical ratio pools (free, unofficial) |
| `trader/timemachine.json` | Generated with `--write`: includes plan details, Monte Carlo odds (`mc`), percentiles, fan chart bands, 160 sample paths, a 24-bin closing histogram, and historical backtest records |

## ⚙️ How It Works

1. **Historical Ratio Pool**: Retains only complete trading sessions (78 five-minute bars from 9:30 AM to 4:00 PM ET) from the previous 60 days. Gaps, half-days, and today's incomplete session are excluded. Each bar is converted into four ratios relative to the previous bar's close (open, high, low, close).
2. **Path Synthesis**: Starting from the plan's entry price, the remaining bars of the session are reconstructed bar by bar. For each bar, a historical ratio is sampled at random from the identical time of day (±2 bars window) and scaled to current price levels.
3. **Stop & Target Evaluation**: For every bar in a replay, stops are evaluated before targets. If a bar touches both the stop and the target, it counts as a stopped-out trade.
4. **10,000 Monte Carlo Replays**: Calculates four key outcome probabilities:
   - **Target first**: Target hit before stop or close.
   - **Stop first**: Stop hit before target or close.
   - **Neither**: Trade remains open at the close or `--until` cutoff.
   - **Green**: Target hit first, or trade price ends above entry at the cutoff.
   - **Average R**: Evaluates expected payoff (+1R at target, -1R at stop, or fractional distance from entry divided by risk if closed at `--until`).
5. **Real Historical Backtest**: Evaluates the plan's exact setup rules (opening range, stop placement, target R) across every real historical session in the pool to contrast simulation against actual outcomes.
6. **Deterministic Reproducibility**: Random draws use Python's `random.Random(seed)` (default seed `19`). Identical plan, data, and seed always produce the exact same numbers across machines.

## ⚖️ The Verdict Engine

The verdict calculates whether the trade possesses an edge by examining only the replays that resolved (hit target or stop). Because larger targets require lower win rates to break even (1 in 1 + R), the engine benchmarks performance against the required mathematical threshold:

- **1R Target**: Requires 50.0% target-first rate to break even.
- **2R Target**: Requires 33.3% target-first rate to break even.
- **3R Target**: Requires 25.0% target-first rate to break even.

| Distance from Break-Even | 1R Verdict | Multi-R Verdict |
| --- | --- | --- |
| < 5 percentage points | **Close to a coin flip** | **Close to break-even** |
| 5 to 15 percentage points | **Leans toward target / stop** | **Leans toward target / stop** |
| ≥ 15 percentage points | **Strongly toward target / stop** | **Strongly toward target / stop** |

> *Note: If over 40% of replays end in "neither", or if the average R diverges in sign from the lean, an explanatory qualification is explicitly appended.*

## 📊 Sample Output & Fan Chart

```
TSLA buy, Monday 2026-10-19: entry 364.18 at 10:15 AM (bar 8), stop 358.32, target 370.04 (1R, risk 5.86 a share).
10,000 replays of the rest of the session, 10:15 AM to 4:00 PM (69 five-minute bars), seed 19.

  target first   29.4 %
  stop first     25.5 %
  neither        45.1 %   still open at 4:00 PM
  green          51.7 %   target first, or above the entry at 4:00 PM

  Price at 4:00 PM: median 364.36, 90 % of replays between 355.54 and 373.54.
  Average R: +0.034 (R = the 5.86 risk: +1R at the target, -1R at the stop).

History: the same rule on each of those 59 real sessions fired 33 times: 13 target, 15 stop, 5 neither. Average R -0.062.

Close to a coin flip: target first 29.4 % vs stop first 25.5 %.
45.1 % of the replays hit neither by 4:00 PM; the price at 4:00 PM decides those.
```

### ASCII Fan Chart (`timemachine.py chart --from`)

```
TSLA 2026-10-19, 2,000 replay paths from the 10:15 AM entry (seed 19)
   374.38 |                                                                      
          |                                               . ... .................
          |                      ................................................
          |           ...........................................................
   370.04 |-------...............................................................  target
          |    ....................................................::::::::::::::
          |  .......:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
          | .::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
   364.18 |**********************************************************************  entry
          | :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
          | .......::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
          |   ....................................:.:::::::::::::::::::::::::::::
          |        ..............................................................
   358.32 |-------------.........................................................  stop
          |                              ........................................
          |                                               .......................
   354.69 |                                                                      
          +----------------------------------------------------------------------
           10:15                              1:10                           4:00
* median   : middle half of the paths   . 90 % of the paths   - stop and target
```

## 🔄 Workflow Steps

1. **Verify Plan**: Ensure `trader/plan.json` exists from `/trader-exit`, or supply plan parameters via CLI flags.
2. **Run Simulation**: Execute `python3 timemachine.py run --write` (add `--until 15:55` if trading with a flat-by rule).
3. **Review Output**: Note the four probabilities, median and 90% range of the close, average R, historical backtest record, and exact printed verdict line. Always cite the random seed used.
4. **Acknowledge Odds Honestly**: If the verdict indicates a coin flip or break-even setup, do not dress it up or force a trade.
5. **Contextualize Catalysts**: Remember simulations reflect past volatility, not predictions; check `/trader-news` for upcoming earnings, filings, or halts.
6. **Handoff to Budget**: If the trade passes all criteria, proceed to `/trader-budget` for capital allocation and position sizing.

## 🚫 What It Never Does

- **Never places orders**: Runs purely informational simulations and never transmits broker orders.
- **Never sizes positions**: Position sizing is handled downstream by `/trader-budget`.
- **Never modifies plans**: Entry, stop, and target levels remain fixed as defined by `/trader-exit`.
- **Never promises profits**: Never prints expected dollar profits or promises winning outcomes.
- **Never uses unclosed bars**: Excludes live, in-progress bars and never pollutes the historical ratio pool with today's action.
- **Never runs on insufficient data**: Refuses execution if fewer than 20 full historical sessions exist or if the plan violates sanity checks (e.g., stop above buy entry).

## 🛡️ Safety & Guardrails

- **Tooling, not financial advice**: Simulated probabilities and backtests are educational tools, not investment recommendations.
- **Paper trading default**: The suite operates under `"paper": true` by default.
- **Strict execution boundary**: Live orders can only ever be placed by `/trader-broker` after passing `/trader-risk` limits and receiving explicit user approval.
- **No unapproved leverage or shorting**: Options, margin, and short selling remain disabled unless explicitly permitted in config.

---

[← Back to Day Trader Skill](../README.md)