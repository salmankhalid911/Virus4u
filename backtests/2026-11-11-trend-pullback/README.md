# Trend-pullback backtest (2026-11-11)

Mechanical version of the SOL "short the bounce" setup, tested on Binance 4h spot candles
for BTC, ETH, SOL, XRP, BNB, DOGE, ADA, LINK (2024-07-30 to 2026-11-10). Rules were fixed
before the run, not tuned.

- Trend: close vs EMA50 and EMA50 slope (6 bars); alts only trade with BTC's trend.
- Entry: candle touches EMA20 and closes back in the trend direction; enter next open.
- Stop: 6-bar extreme + 0.2%. Skip if stop < 0.5% or > 8% away.
- Exit: 2R target, stop, or 30 bars (5 days). Same-candle stop and target counts as a stop.
- Costs: 0.3% round trip. Risk 1% of equity per trade, compounded.

Result: no edge after costs. Last 100 trades: 40% wins, -0.04R per trade, -4.7%, PF 0.94.
All 1,330 trades: -0.09R per trade, -73%, max drawdown 79.5%. Before fees it is slightly
positive (+0.06R), so fees take the whole edge.

Rerun: `python3 fetch.py data && python3 backtest.py data`
