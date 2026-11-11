# Daily trend-following: rules and protocol (fixed before any result)

Committed before the first run. Standard textbook settings, chosen without looking at results
for these strategies; nothing below changes in response to results.

## Why
Phase 5 showed fees dominate on 5m-4h. These trade a few times a month per coin, so costs
are a small fraction of each trade.

## Data
Binance daily candles, validated. BTC and ETH from 2018-02-09 (the 2018-02-08 candle is a
28-minute exchange-outage candle and is excluded, not patched); SOL from 2020-08-11.

## Strategies (each tested LONG and SHORT separately; shorts need futures and pay
0.01% funding per 8 hours)
T1 Donchian breakout ("turtle"): enter when the daily close breaks the prior 55-day high
(short: 55-day low). Exit the remainder when the daily close breaks the prior 20-day low
(short: 20-day high).
T2 Time-series momentum: enter when the close is above its 100-day average AND the 60-day
return is positive (short: below, negative), on the first day this becomes true. Exit the
remainder when either condition fails.

## Shared rules
- Signals on closed daily candles; entry at the next day's open (market order).
- Initial stop: 2.5 x ATR(20) from the signal close (T1); 3.0 x ATR(20) (T2).
- To keep the existing 1:2 minimum reward/risk rule: take profit 1 at 2R closes 50%, the
  stop then moves to entry (from the next day); the other 50% rides the trend exit above.
- Stop is checked before the target inside a day; a gap through the stop fills at the open.
- One position per coin per strategy. No pyramiding, no averaging down.

## Costs
Base 0.10% fee + 0.05% slippage per side. Sensitivity: low 0.04% + 0.02%, high 0.10% + 0.15%.

## Periods
Train 2018-02-09 to 2021-12-31 (2018 bear,
2019 recovery, 2020-21 bull). Validation 2022-01-01 to 2024-06-30 (2022 bear, 2023-24
recovery). Test 2024-07-01 to 2026-11-10. The test window overlaps the Phase 5 data, which
I have seen as prices, but these strategies have never been run on it.

## Decision rules
- Qualifies only if expectancy after base costs is positive in BOTH train and validation,
  with at least 15 trades in each (daily systems trade rarely).
- Rejected if test expectancy is negative.
- Reported per trade in R (the edge, independent of account size), and as the $100 account
  with every existing risk limit at 0.5% risk and at 1% risk (the maximum).
- Compared with buy-and-hold of the same coin and with no trading.
- The 100-trade live gate cannot be met by a daily system in this window; forward paper
  trading would be the next test either way. Nothing goes to live trading.
