# Strategy rules and test protocol (fixed before the Phase 5 run)

Committed before any Phase 5 result was produced. Nothing below may change in response to
results. Disclosure: an earlier, different backtest (trend pullback, 8 coins) and a smoke test
of the runner (old rules, 5 coins, 15m/1h) printed results that included the 2026 test
period. Those results were weak. The rule changes below come only from the Phase 4 spec
(volatility filters, ATR stops, 5m/4h, sides separate), not from those numbers.

## Universe and data
- BTCUSDT, ETHUSDT, SOLUSDT, Binance spot candles, validated (closed bars only, no gaps).
- Signal timeframes: 5m, 15m, 1h, 4h.
- Multi-timeframe map (direction, structure): 5m and 15m use (4h, 1h); 1h uses (4h, 1h);
  4h uses (1d, 4h). Higher-timeframe values come from the last bar CLOSED by the time the
  signal bar closed.

## Shared filters
- Direction = EMA20/EMA50 trend state with a rising/falling EMA50 (6 bars).
- Volatility: ATR% percentile vs the previous 500 bars must be between 0.10 and 0.95.
- Stops: structure level plus an ATR buffer, widened to at least 1.0 ATR from the signal
  close; skipped if wider than 3.0 ATR.
- Entry: market order at the open of the bar after the confirming bar closes.
- Exits: TP1 2R (50%), TP2 3R (30%), TP3 4R (20%); stop moves to entry after TP1 (from the
  next bar); time exit after 1 day (5m, 15m), 2 days (1h), 7 days (4h).
- Intrabar: stop is assumed hit before any target; a gap through the stop fills at the open.

## Strategies
A Trend pullback: direction and structure agree; EMA20 > EMA50 > EMA200 (mirror for
shorts); candle touches EMA20 and closes back in trend direction; RSI 40-65 long / 35-60
short; MACD histogram turning in trend direction; volume >= 20-bar average.

B Breakout-retest: 20-bar range no wider than 4 ATR; close beyond it on >= 1.5x average
volume, not against the direction trend; within 8 bars a retest of the level (within 0.2
ATR) closes back beyond it; a close 0.5 ATR back inside cancels the setup.

C Liquidity / structure: a candle sweeps the last confirmed swing low (swing needs 3 bars
each side, so it is known 3 bars late) and closes back above it, direction not down; within
10 bars a displacement candle (body >= 1.2 ATR, volume >= 1.2x average) closes above the
last confirmed swing high (change of character). Mirror for shorts.

D Range: only when direction is flat; 48-bar range 3-10 ATR wide; long in the bottom 15%
with RSI < 35, bullish candle and volume >= average; TP1 must fit inside the range.

## Costs
- Base: 0.10% fee + 0.05% slippage per side (taker both ways). Shorts pay 0.01% per 8h
  funding (they need a futures account).
- Sensitivity: low = 0.04% fee + 0.02% slippage; high = 0.10% fee + 0.15% slippage.

## Account
$100, 0.5% risk per trade, max 1%, -2% daily stop, -5% weekly stop, 3 trades a day, one
position per coin, spot-style sizing (position value <= cash), exchange minimum order rules.

## Periods
- Train: 2024-11-01 to 2025-08-31. Validation: 2025-09-01 to 2026-02-28.
- Test: 2026-03-01 to 2026-11-11.

## Decision rules
- Each strategy x timeframe x side is evaluated on its own (no combining first).
- Qualifies only with positive expectancy after base costs in BOTH train and validation,
  with at least 30 trades in each.
- Rejected if test expectancy is negative. Ranked by test expectancy after base costs.
- Compared with buy-and-hold (equal-weight BTC/ETH/SOL) and no trading (0%).
- Live-trading gates (100+ trades, PF > 1.3, max DD < 5%, positive OOS, not one regime)
  are reported but nothing proceeds to live trading.
