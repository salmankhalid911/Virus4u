# Crypto trading research and paper-trading system

Paper trading only. Starting balance $100. Live trading is off and stays off unless the
owner sets `mode="live"` in settings AND exports `LIVE_TRADING_AUTHORIZED=yes`. No code
path sets either.

## Architecture

```
cryptoai/
  config.py          every limit in one place: risk, costs, pairs, timeframes, mode
  data/              market data          [built]
    sources.py         TradingViewSource (primary, waits for the MCP connection)
                       BinancePublicSource (secondary: public, read-only, no key)
    validation.py      rejects stale, gappy, out-of-order or impossible candles;
                       drops the still-forming candle so signals use closed bars only
    store.py           SQLite candle store
    service.py         fetch -> validate -> store, falling back source by source
  risk/              risk manager         [built]
    sizing.py          size = dollar risk / stop distance, net of fees and slippage,
                       fitted to exchange min size, step and min order value; spot cap
    limits.py          account gate: stop and target required, reward/risk >= 2,
                       risk <= 1%, -2% day stop, -5% week stop, 3 trades a day
  indicators/        EMA, RSI, MACD, ATR, volume, swings      [next]
  strategies/        A trend pullback, B breakout-retest,
                     C liquidity/structure, D range           [next]
  backtest/          event-driven, closed bars only, train/validation/test split
  execution/         paper broker (default); live broker locked
  analyst/           plain-language explanation of each setup; cannot change risk
  api/ + dashboard/  FastAPI backend, dark dashboard with signal centre
  scheduler/         polling loop, restart recovery, no duplicate trades per signal
```

## Run

```
python3 -m venv .venv && .venv/bin/pip install pandas numpy fastapi "uvicorn[standard]" pytest httpx
cd trading
../.venv/bin/python -m pytest -q          # unit tests
../.venv/bin/python scripts/check_data.py # live fetch + validation for every pair/timeframe
```
