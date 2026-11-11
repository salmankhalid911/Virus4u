# Slower-timeframe research: comparison report

Rules and classification were committed before any run (`docs/SLOW_RESEARCH_RULES.md`,
commit e765969). BTC/USDT and ETH/USDT, long only, spot, no leverage. Train 2024, validation
2025, final test 2026-01-01 to 2026-11-10. Costs: 0.10% fee + 0.05% slippage per side.
R = profit as a multiple of the planned risk, after costs, over every signal the rules produced.
The $100 account columns apply all risk limits (0.5% risk, one open position, $5 minimum order).

## Verdict: nothing passes

| Strategy | Verdict | Why |
|---|---|---|
| A Trend EMA50/200 + ADX, 1D | INSUFFICIENT EVIDENCE | 10 / 6 / 3 trades (train / validation / test); test -0.18R |
| A Trend EMA50/200 + ADX, 4H | FAIL | positive in train (+0.08R) and validation (+0.18R), **negative in test (-0.28R)** under every scenario |
| B Weekly trend + daily pullback, 1D | FAIL | validation -0.21R, test -0.37R |
| B Daily trend + 4H pullback, 4H | FAIL | validation -0.05R, test -0.22R |
| C Consolidation breakout, 1D | FAIL | test -0.35R (9 trades) |
| C Consolidation breakout, 4H | FAIL | train and validation about 0R; test +0.18R alone is not evidence |
| D BTC/ETH momentum rotation, 1D | INSUFFICIENT EVIDENCE | +0.18R / +0.03R / +0.28R but only 11 / 10 / 4 trades |

## Full results (base costs)

| Strategy | Period | Trades | R/trade | Win % | PF | Avg hold (days) | Trades/month | $100 net | $100 max DD |
|---|---|---|---|---|---|---|---|---|---|
| A 1D | train | 10 | +0.24 | 40.0 | 1.62 | 25.2 | 0.8 | +2.21% | 0.00% |
| | validation | 6 | +0.32 | 33.3 | 1.91 | 25.7 | 0.5 | -0.29% | 0.97% |
| | test | 3 | -0.18 | 33.3 | 0.46 | 26.3 | 0.3 | -0.50% | 0.50% |
| A 4H | train | 62 | +0.08 | 30.6 | 1.18 | 4.8 | 5.2 | +0.56% | 3.45% |
| | validation | 34 | +0.18 | 32.4 | 1.45 | 4.4 | 2.8 | +3.50% | 1.64% |
| | test | 41 | -0.28 | 19.5 | 0.48 | 3.5 | 4.0 | -2.49% | 3.03% |
| B 1D | train | 49 | +0.20 | 22.4 | 1.40 | 20.6 | 4.1 | +0.92% | 2.23% |
| | validation | 47 | -0.21 | 21.3 | 0.60 | 15.6 | 3.9 | -1.32% | 1.32% |
| | test | 11 | -0.37 | 18.2 | 0.33 | 15.4 | 1.1 | -0.38% | 0.84% |
| B 4H | train | 222 | +0.04 | 32.9 | 1.10 | 4.1 | 18.5 | +5.10% | 1.98% |
| | validation | 178 | -0.05 | 19.7 | 0.90 | 3.6 | 14.8 | -0.79% | 2.45% |
| | test | 190 | -0.22 | 25.3 | 0.56 | 2.9 | 18.4 | +2.96% | 1.24% |
| C 1D | train | 2 | -0.21 | 0.0 | 0.00 | 15.0 | 0.2 | 0.00% | 0.00% |
| | validation | 7 | +0.39 | 71.4 | 3.42 | 23.9 | 0.6 | 0.00% | 0.00% |
| | test | 9 | -0.35 | 33.3 | 0.18 | 12.6 | 0.9 | -0.35% | 0.48% |
| C 4H | train | 44 | -0.00 | 27.3 | 1.00 | 3.0 | 3.7 | +1.02% | 2.09% |
| | validation | 28 | -0.02 | 28.6 | 0.95 | 2.7 | 2.3 | +1.51% | 1.18% |
| | test | 32 | +0.18 | 12.5 | 1.58 | 2.3 | 3.1 | +0.05% | 2.64% |
| D 1D | train | 11 | +0.18 | 45.5 | 1.46 | 19.5 | 0.9 | +1.70% | 0.49% |
| | validation | 10 | +0.03 | 30.0 | 1.09 | 17.7 | 0.8 | -0.40% | 0.89% |
| | test | 4 | +0.28 | 25.0 | 1.70 | 25.5 | 0.4 | +0.88% | 0.44% |

Note on B 4H: the $100 account made +2.96% in the test period although the strategy averaged
-0.22R over all 190 signals. The account only took 42 of them (one position at a time), and
which 42 it got was luck of ordering, not an edge.

## Baselines

| Period | Buy and hold BTC | BTC max DD | Buy and hold ETH | ETH max DD | Cash / no trading |
|---|---|---|---|---|---|
| Train 2024 | +111.2% | 26.2% | +41.5% | 45.3% | 0% |
| Validation 2025 | -7.6% | 32.0% | -11.8% | 60.0% | 0% |
| Test 2026 | -17.2% | 39.5% | -31.9% | 53.3% | 0% |

In the test period every strategy lost far less than holding either coin, mostly because they
were in cash most of the time. That is capital protection, not a trading edge.

## Robustness (test R/trade: base / low fees / high costs / entry delay +1 / stops 0.5% worse)

| Strategy | Base | Low fees | High costs | Entry delay | Worse stops | Chance true mean <= 0 |
|---|---|---|---|---|---|---|
| A 1D | -0.18 | -0.17 | -0.20 | +0.33 | -0.18 | 63% |
| A 4H | -0.28 | -0.26 | -0.31 | -0.32 | -0.32 | 97% |
| B 1D | -0.37 | -0.36 | -0.39 | -0.24 | -0.40 | 95% |
| B 4H | -0.22 | -0.19 | -0.27 | -0.22 | -0.28 | 100% |
| C 1D | -0.35 | -0.35 | -0.36 | -0.39 | -0.36 | 99% |
| C 4H | +0.18 | +0.23 | +0.10 | +0.37 | +0.18 | 38% |
| D 1D | +0.28 | +0.30 | +0.26 | +0.56 | +0.27 | 33% |

Costs move results only slightly on these timeframes. The losses come from the signals, not fees.

## Regimes (test period, R per trade)
- A 4H: bull -0.35 (11), bear -0.28 (26), sideways -0.06 (4).
- B 4H: bull -0.47 (47), bear -0.04 (124), sideways -0.80 (19).
- C 4H: bear +0.30 (26), bull -0.36 (4), sideways -0.41 (2). Its only positive period is the
  2026 bear market, after flat train and validation results.
- D 1D: bear +0.58 (3), bull -0.60 (1).

## What this means
- No strategy shows positive out-of-sample expectancy after costs with enough trades. Per the
  rules, nothing is deployed and nothing is forced.
- D (rotation) is the only one positive in all three periods, but with 11, 10 and 4 trades it
  cannot be told apart from luck (33% chance the true mean is <= 0).
- 2024-2026 is a short window for daily strategies; a single slow strategy trades 0.3-1 times
  a month, so years of data or forward trading are needed to judge it.
- Account sizing: at 0.5% risk the wide daily stops push some orders under Binance's $5
  minimum, so the $100 account skipped trades (for example C 1D: 4 of 9 test signals).
