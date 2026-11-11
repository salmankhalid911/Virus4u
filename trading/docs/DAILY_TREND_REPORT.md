# Daily trend-following: results

Rules: `docs/DAILY_TREND_RULES.md` (committed before this run). BTC, ETH, SOL daily candles.
Train 2018-02 to 2021-12, validation 2022-01 to 2024-06, test 2024-07 to 2026-11.
R = profit as a multiple of the planned risk, after 0.10% fee + 0.05% slippage per side.

## Verdict
Two of four pass the protocol: **Donchian breakout LONG** and **time-series momentum LONG**
were positive after costs in train, validation and test. Both shorts failed validation and
are rejected. The edge is real-looking but **not statistically proven**: the test samples are
small and the confidence intervals include zero. Next step is forward paper trading, which is
the only data none of these rules have ever seen.

| Strategy | Side | Train R/trade (n) | Valid R/trade (n) | Test R/trade (n) | Test win % | Test PF | Qualified | Status |
|---|---|---|---|---|---|---|---|---|
| T1 Donchian 55/20 | LONG | +3.54 (20) | +1.02 (19) | **+0.27 (21)** | 42.9 | 1.58 | yes | passes protocol |
| T2 Momentum 100d/60d | LONG | +1.27 (56) | +0.26 (73) | **+0.07 (57)** | 22.8 | 1.28 | yes | passes protocol |
| T1 Donchian 55/20 | SHORT | +0.38 (14) | -0.02 (19) | +0.25 (15) | 53.3 | 1.99 | no | rejected (validation negative) |
| T2 Momentum 100d/60d | SHORT | +0.14 (56) | -0.09 (66) | +0.03 (75) | 34.7 | 1.18 | no | rejected (validation negative) |

## Confidence (test period, longs)
- T1: mean +0.27R, t = 0.88, bootstrap chance the true mean is <= 0: 18%, 95% CI -0.29 to +0.86R.
  Without its single best trade: +0.13R.
- T2: mean +0.07R, t = 0.58, chance <= 0: 29%, 95% CI -0.15 to +0.32R. Without its best trade: +0.01R.
- The edge shrinks from train to validation to test (T1: 3.54 -> 1.02 -> 0.27R).

## Costs barely matter here
Test R/trade at low / base / high costs: T1 +0.29 / +0.27 / +0.24; T2 +0.09 / +0.07 / +0.05.
Phase 5 intraday strategies lost 0.2-0.6R per trade mostly to costs; these trade ~10x less.

## $100 account with every risk limit
At 0.5% risk ($0.50) the wide daily stops make many positions smaller than Binance's $5
minimum, so trades are skipped (T1 test: 11 of 21 taken). At 1% risk (the allowed maximum):
- T1 LONG test: 21 trades, +5.35%, max drawdown 3.70%
- T2 LONG test: 48 trades, +5.59%, max drawdown 2.90%

## Against buy and hold (test period, net, max drawdown)
BTC +17.0% (53.0%), ETH -40.5% (67.6%), SOL -43.3% (76.3%); equal weight about -22%.
No trading: 0%. The trend systems beat equal-weight buy and hold with a tiny fraction of its
drawdown, but made less than holding BTC alone.

## Regimes (test R, longs)
- T1: bull +3.8, sideways +1.8 (both positive); by coin ETH +5.7, BTC +1.7, SOL -1.8.
- T2: bull +2.9, sideways +2.4, bear -1.2; by coin BTC +2.0, ETH +2.3, SOL -0.3.

## Live-trading gates (T1 long, 1% risk)
100+ trades: no (21). Positive expectancy: yes. PF > 1.3: yes (1.58). Max DD < 5%: yes (3.7%).
Not one regime: yes. Fails on sample size, so it needs forward paper trading before anything.
