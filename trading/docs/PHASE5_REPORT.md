# Phase 5 strategy comparison

Generated 2026-11-11 02:14 UTC. Rules and protocol: `docs/STRATEGY_RULES.md`, committed before this run.
BTC, ETH, SOL; 5m / 15m / 1h / 4h; each strategy x timeframe x side tested on its own with the $100 account and all risk limits.
Train 2024-11-01 to 2025-08-31, validation 2025-09-01 to 2026-02-28, test 2026-03-01 to 2026-11-11.

## Verdict

**No strategy is profitable after fees in a way that survives the protocol.** 0 of 32 combinations qualified on train + validation. 4 combinations were positive in the test period alone, but a test-only result after failing train and validation is not evidence of an edge.

## Baselines (same periods)

| Period | Buy and hold BTC/ETH/SOL (equal weight) | Max drawdown | BTC | ETH | SOL | No trading |
|---|---|---|---|---|---|---|
| train | +50.1% | 50.3% | +56.0% | +75.4% | +20.0% | 0.0% |
| validation | -50.4% | 59.4% | -37.8% | -55.4% | -57.5% | 0.0% |
| test | +1.5% | 32.1% | +9.3% | +1.5% | -5.3% | 0.0% |

## Ranking by out-of-sample (test) expectancy, base costs

Expectancy is in R (multiples of the planned risk) after fees, slippage and funding. Net % and drawdown are for the $100 account at 0.5% risk per trade.

| # | Strategy | TF | Side | Train trades / expR | Valid trades / expR | Test trades | Win % | PF | Exp R | Avg win R / loss R | Net % | Max DD % | Qualified | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | C Liquidity/CHOCH | 4h | SHORT | 2 / -0.91 | 2 / -0.02 | 1 | 100.0 | inf | +1.60 | +1.60 / +0.00 | +0.79 | 0.00 | no | positive OOS, failed train/valid |
| 2 | C Liquidity/CHOCH | 1h | LONG | 11 / +0.01 | 2 / +0.26 | 9 | 44.4 | 1.55 | +0.30 | +1.82 / -0.92 | +1.28 | 1.49 | no | positive OOS, failed train/valid |
| 3 | D Range | 4h | SHORT | 7 / -1.01 | 8 / +0.16 | 12 | 50.0 | 1.34 | +0.17 | +1.36 / -1.02 | +1.02 | 1.28 | no | positive OOS, failed train/valid |
| 4 | B Breakout-retest | 1h | LONG | 69 / -0.14 | 31 / -0.45 | 57 | 45.6 | 1.19 | +0.10 | +1.37 / -0.96 | +2.78 | 4.04 | no | positive OOS, failed train/valid |
| 5 | A Trend pullback | 4h | SHORT | 20 / +0.15 | 27 / -0.02 | 21 | 38.1 | 0.87 | -0.08 | +1.43 / -1.01 | -0.86 | 3.61 | no | rejected: negative OOS |
| 6 | C Liquidity/CHOCH | 1h | SHORT | 14 / -0.02 | 4 / +0.06 | 12 | 50.0 | 0.78 | -0.09 | +0.67 / -0.84 | -0.54 | 1.00 | no | rejected: negative OOS |
| 7 | C Liquidity/CHOCH | 15m | LONG | 40 / -0.23 | 15 / +0.08 | 39 | 38.5 | 0.80 | -0.10 | +1.29 / -0.97 | -2.33 | 4.44 | no | rejected: negative OOS |
| 8 | B Breakout-retest | 4h | SHORT | 6 / +0.09 | 16 / -0.07 | 10 | 30.0 | 0.76 | -0.14 | +1.65 / -0.91 | -0.76 | 2.16 | no | rejected: negative OOS |
| 9 | A Trend pullback | 1h | LONG | 99 / -0.14 | 32 / +0.13 | 77 | 32.5 | 0.70 | -0.20 | +1.38 / -0.95 | -7.17 | 9.65 | no | rejected: negative OOS |
| 10 | C Liquidity/CHOCH | 5m | SHORT | 67 / -0.23 | 74 / -0.27 | 76 | 39.5 | 0.63 | -0.20 | +1.00 / -0.98 | -7.74 | 7.98 | no | rejected: negative OOS |
| 11 | A Trend pullback | 1h | SHORT | 91 / -0.22 | 72 / +0.07 | 73 | 31.5 | 0.66 | -0.23 | +1.36 / -0.96 | -7.64 | 8.52 | no | rejected: negative OOS |
| 12 | A Trend pullback | 15m | SHORT | 158 / -0.19 | 161 / -0.13 | 159 | 35.8 | 0.61 | -0.26 | +1.02 / -0.97 | -16.38 | 20.59 | no | rejected: negative OOS |
| 13 | D Range | 1h | LONG | 27 / -0.43 | 5 / -1.00 | 28 | 35.7 | 0.54 | -0.28 | +1.01 / -1.00 | -4.01 | 4.18 | no | rejected: negative OOS |
| 14 | C Liquidity/CHOCH | 5m | LONG | 82 / -0.40 | 36 / -0.56 | 78 | 35.9 | 0.52 | -0.31 | +0.89 / -0.98 | -10.79 | 11.59 | no | rejected: negative OOS |
| 15 | A Trend pullback | 15m | LONG | 233 / -0.22 | 94 / -0.29 | 182 | 34.1 | 0.49 | -0.31 | +0.96 / -0.97 | -24.47 | 24.47 | no | rejected: negative OOS |
| 16 | B Breakout-retest | 15m | LONG | 238 / -0.30 | 114 / -0.42 | 180 | 31.1 | 0.44 | -0.37 | +0.90 / -0.94 | -25.36 | 26.15 | no | rejected: negative OOS |
| 17 | D Range | 4h | LONG | 3 / -0.43 | 0 / +0.00 | 6 | 33.3 | 0.38 | -0.41 | +0.77 / -1.00 | -1.23 | 1.33 | no | rejected: negative OOS |
| 18 | C Liquidity/CHOCH | 15m | SHORT | 38 / +0.01 | 33 / -0.27 | 35 | 28.6 | 0.37 | -0.41 | +0.83 / -0.91 | -6.76 | 6.76 | no | rejected: negative OOS |
| 19 | B Breakout-retest | 1h | SHORT | 73 / -0.20 | 49 / -0.30 | 59 | 27.1 | 0.39 | -0.44 | +1.04 / -0.99 | -11.95 | 12.05 | no | rejected: negative OOS |
| 20 | D Range | 15m | LONG | 65 / -0.35 | 43 / -0.65 | 33 | 30.3 | 0.36 | -0.46 | +0.80 / -1.00 | -7.10 | 7.37 | no | rejected: negative OOS |
| 21 | B Breakout-retest | 5m | LONG | 436 / -0.47 | 189 / -0.58 | 306 | 27.8 | 0.24 | -0.47 | +0.55 / -0.87 | -47.98 | 47.98 | no | rejected: negative OOS |
| 22 | D Range | 15m | SHORT | 55 / -0.33 | 39 / -0.21 | 45 | 28.9 | 0.34 | -0.48 | +0.81 / -1.00 | -10.20 | 12.90 | no | rejected: negative OOS |
| 23 | A Trend pullback | 5m | SHORT | 271 / -0.36 | 220 / -0.42 | 246 | 27.2 | 0.32 | -0.48 | +0.78 / -0.96 | -40.49 | 40.51 | no | rejected: negative OOS |
| 24 | D Range | 1h | SHORT | 28 / -0.27 | 16 / -0.05 | 13 | 23.1 | 0.37 | -0.50 | +1.22 / -1.01 | -3.02 | 4.75 | no | rejected: negative OOS |
| 25 | D Range | 5m | SHORT | 150 / -0.46 | 57 / -0.07 | 102 | 27.5 | 0.24 | -0.52 | +0.52 / -0.91 | -21.81 | 23.67 | no | rejected: negative OOS |
| 26 | A Trend pullback | 5m | LONG | 341 / -0.38 | 116 / -0.55 | 248 | 25.8 | 0.26 | -0.53 | +0.74 / -0.98 | -44.49 | 44.49 | no | rejected: negative OOS |
| 27 | B Breakout-retest | 15m | SHORT | 202 / -0.27 | 170 / -0.34 | 161 | 22.4 | 0.24 | -0.56 | +0.81 / -0.95 | -33.86 | 33.86 | no | rejected: negative OOS |
| 28 | A Trend pullback | 4h | LONG | 27 / -0.22 | 6 / -0.35 | 20 | 30.0 | 0.20 | -0.56 | +0.46 / -1.00 | -5.44 | 5.44 | no | rejected: negative OOS |
| 29 | D Range | 5m | LONG | 138 / -0.45 | 80 / -0.65 | 111 | 25.2 | 0.21 | -0.56 | +0.56 / -0.94 | -24.68 | 24.68 | no | rejected: negative OOS |
| 30 | B Breakout-retest | 5m | SHORT | 395 / -0.45 | 306 / -0.54 | 335 | 19.7 | 0.16 | -0.62 | +0.57 / -0.91 | -58.85 | 58.85 | no | rejected: negative OOS |
| 31 | B Breakout-retest | 4h | LONG | 11 / +0.01 | 3 / -1.00 | 13 | 7.7 | 0.06 | -0.87 | +0.66 / -1.00 | -5.49 | 5.49 | no | rejected: negative OOS |
| 32 | C Liquidity/CHOCH | 4h | LONG | 2 / +0.24 | 1 / +1.89 | 2 | 0.0 | 0.00 | -1.00 | +0.00 / -1.00 | -0.99 | 0.99 | no | rejected: negative OOS |

## Long versus short (test period, base costs, all strategies and timeframes)

- LONG: 1389 trades, average -0.395R per trade, -207.5% summed across combinations
- SHORT: 1360 trades, average -0.449R per trade, -219.0% summed across combinations

## By strategy (test period, base costs, all timeframes and both sides)

- A Trend pullback: 1026 trades, -0.384R per trade
- B Breakout-retest: 1121 trades, -0.484R per trade
- C Liquidity/CHOCH: 252 trades, -0.225R per trade
- D Range: 350 trades, -0.476R per trade

## By timeframe (test period, base costs)

- 5m: 1502 trades, -0.505R per trade
- 15m: 834 trades, -0.371R per trade
- 1h: 328 trades, -0.198R per trade
- 4h: 85 trades, -0.312R per trade

## Market regime (test period P/L in $, base costs) for the top 8

Regime = 4h (or daily) direction at entry; volatility = ATR percentile at entry.

| Strategy | TF | Side | Bull | Bear | Sideways | High vol | Low vol |
|---|---|---|---|---|---|---|---|
| C Liquidity/CHOCH | 4h | SHORT | +0.00 | +0.79 | +0.00 | +0.79 | +0.00 |
| C Liquidity/CHOCH | 1h | LONG | +2.10 | +0.00 | -0.82 | +1.19 | +0.09 |
| D Range | 4h | SHORT | +0.00 | +0.00 | +1.02 | +1.05 | -0.03 |
| B Breakout-retest | 1h | LONG | +6.69 | +0.00 | -3.90 | +1.88 | +0.90 |
| A Trend pullback | 4h | SHORT | +0.00 | -0.86 | +0.00 | -3.01 | +2.15 |
| C Liquidity/CHOCH | 1h | SHORT | -0.50 | -0.08 | +0.04 | +0.79 | -1.33 |
| C Liquidity/CHOCH | 15m | LONG | -3.56 | +0.00 | +1.23 | -1.13 | -1.20 |
| B Breakout-retest | 4h | SHORT | +0.00 | -0.76 | +0.00 | -0.20 | -0.56 |

## Sensitivity to fees and slippage (test expectancy, R)

Low = 0.04% fee + 0.02% slippage per side. Base = 0.10% + 0.05%. High = 0.10% + 0.15%.

| Strategy | TF | Side | Low | Base | High |
|---|---|---|---|---|---|
| C Liquidity/CHOCH | 4h | SHORT | +1.74 | +1.60 | +1.48 |
| C Liquidity/CHOCH | 1h | LONG | +0.43 | +0.30 | +0.19 |
| D Range | 4h | SHORT | +0.27 | +0.17 | +0.09 |
| B Breakout-retest | 1h | LONG | +0.28 | +0.10 | -0.03 |
| A Trend pullback | 4h | SHORT | -0.02 | -0.08 | -0.13 |
| C Liquidity/CHOCH | 1h | SHORT | -0.01 | -0.09 | -0.16 |
| C Liquidity/CHOCH | 15m | LONG | +0.05 | -0.10 | -0.21 |
| B Breakout-retest | 4h | SHORT | -0.07 | -0.14 | -0.21 |
| A Trend pullback | 1h | LONG | -0.12 | -0.20 | -0.26 |
| C Liquidity/CHOCH | 5m | SHORT | +0.03 | -0.20 | -0.33 |
| A Trend pullback | 1h | SHORT | -0.11 | -0.23 | -0.28 |
| A Trend pullback | 15m | SHORT | -0.10 | -0.26 | -0.34 |

## Live-trading gates

100+ trades, positive expectancy after fees, profit factor > 1.3, max drawdown < 5%, profitable without its best market regime.
Combinations passing all five: 0. Nothing proceeds to live trading.
