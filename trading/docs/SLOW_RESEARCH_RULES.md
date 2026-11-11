# Slower-timeframe research: rules and protocol (fixed before any result)

Committed before the first run of any strategy in this file. Settings are standard textbook
values chosen without results. No rule changes after results exist. The previous research
(Phase 5 intraday strategies, and the earlier Donchian/momentum test) is closed and is not
reused or tuned here.

Disclosure: I have seen 2026 prices and an earlier, different daily trend test touched part of
2026. None of the four strategies below has ever been run on any period.

## Markets and data
- BTCUSDT, ETHUSDT, Binance spot candles, validated (closed candles only, no gaps).
- Timeframes: 1D and 4H. Weekly candles are built from daily candles (Monday 00:00 UTC to
  Sunday close); a week is used only after it has closed.
- Data before 2024 is used only to warm up indicators, never to evaluate a strategy.

## Periods
- Train: 2024-01-01 to 2024-12-31. Validation: 2025-01-01 to 2025-12-31.
- Final test: 2026-01-01 to 2026-11-10, never run before the rules below were committed.
- Forward paper trading: from 2026-11-11.
- A trade belongs to the period in which it was entered. A trade still open when the data ends
  is closed at the last available close and labelled as such.

## Execution (all strategies)
- Long only. Spot, no leverage, no shorts (shorting needs borrowing). Cash otherwise.
- Every decision uses closed candles only. Orders are market orders at the next candle's open.
- Stops are checked before targets inside a candle. A gap through the stop fills at the open.
- Take profit 1 at 2R closes 50% (keeps the 1:2 minimum reward/risk); the stop then moves to
  the entry price from the next candle; the other 50% leaves on the strategy's exit rule
  (market order at the next open).
- Indicators: EMA, ATR(14) Wilder, ADX(14) Wilder, RSI(14) Wilder, volume SMA(20).

## Strategy A: Trend following (EMA 50/200 + ADX). Run on 1D and on 4H.
- Entry signal on a closed candle when ALL are true and were NOT all true on the previous
  candle: close > EMA200; EMA50 > EMA200; ADX(14) >= 25; +DI > -DI.
- Stop: signal close - 2.5 x ATR(14).
- Exit (rest): candle closes below EMA50.

## Strategy B: Higher-timeframe trend + pullback. Run on 1D (weekly direction) and on 4H
(daily direction).
- Direction (last CLOSED higher-timeframe candle): close > EMA20 and EMA20 above its value one
  candle earlier.
- Structure: close > EMA50 on the signal timeframe.
- Pullback: within the last 3 candles (including the signal candle) a low touched or went
  below EMA20.
- Momentum confirmation: the signal candle closes above the previous candle's high and RSI(14)
  is between 45 and 70.
- Stop: the lower of (lowest low of the last 5 candles - 0.5 x ATR) and (close - 1.5 x ATR).
- Exit (rest): close below EMA50, or the higher-timeframe direction turns false.

## Strategy C: Consolidation breakout. Run on 1D and on 4H.
- Box: the 10 candles before the breakout candle; box high/low = their highest high / lowest
  low. Consolidation if box height <= 2.5 x ATR(14) measured on the last box candle.
- Breakout: candle closes above box high with volume >= 1.5 x volume SMA(20).
- Confirmation (no chasing): the NEXT candle must also close above box high. If it closes
  back inside the box, the setup is cancelled. Entry at the open after the confirming candle.
- Stop: box low - 0.25 x ATR(14).
- Exit (rest): close below EMA20.

## Strategy D: BTC/ETH momentum rotation. Daily data, decided weekly.
- Every Monday, using closed daily candles up to Sunday: score = 28-day return of each coin.
- Eligible: score > 0 and close > SMA(100) of that coin.
- If holding nothing: buy the eligible coin with the higher score.
- If holding a coin: keep it while it is eligible, unless the other coin is eligible and its
  score is at least 5 percentage points higher (anti-switching filter); then switch. If the
  held coin is no longer eligible, sell it (and buy the other if eligible).
- Protective stop: entry - 3.0 x ATR(14, daily). Take profit 1 and breakeven as above; the rest
  leaves on the weekly decision.

## Account (same for every strategy)
$100 start. 0.5% risk per trade (maximum 1%, never used to rescue a result). No leverage. Max
one open position at a time (across BTC and ETH). Daily loss stop 2%, weekly drawdown stop 5%,
max 3 trades a day. Binance order rules (minimum $5 order, size steps). A trade that cannot fit
these rules is skipped and counted.

## Costs and robustness scenarios
- Base: 0.10% fee + 0.05% slippage per side (Binance spot taker fee).
- Low fees: 0.075% (BNB discount) + 0.02% slippage.
- High costs: 0.10% fee + 0.15% slippage.
- Entry delay: enter one candle later (at the open after the next candle), base costs.
- Bad stop fills: every stop fills 0.5% worse than the stop price, base costs.
- Regimes: each trade is labelled by BTC daily regime at entry: bull (close > SMA200 and
  SMA200 higher than 20 days ago), bear (close < SMA200 and SMA200 lower), otherwise sideways.

## Classification (fixed now)
- FAIL if any of: train expectancy <= 0 (5+ trades); validation expectancy <= 0 (5+ trades);
  test expectancy <= 0 (5+ trades); test max drawdown >= 5% on the $100 account; test
  expectancy <= 0 under ANY robustness scenario.
- INSUFFICIENT EVIDENCE if not FAIL and any of train, validation or test has fewer than 10
  trades.
- PASS otherwise. Expectancy is after costs, measured in R per trade. A bootstrap estimate of
  the chance that the true test expectancy is <= 0 is reported for information.
- Compared with buy-and-hold BTC, buy-and-hold ETH, and cash / no trading (0%).
- Nothing goes to live trading. A PASS goes to forward paper trading for 60-90 days.
