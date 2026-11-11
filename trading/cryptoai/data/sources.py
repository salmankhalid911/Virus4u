"""Market data sources.

TradingViewSource is the intended primary source, but its MCP tools are only reachable
from inside a Claude session, not from this Python process. Until a supported bridge
exists it reports itself unavailable instead of pretending to work.

BinancePublicSource reads Binance's public market-data mirror (no API key, read-only).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Protocol

from ..config import TIMEFRAME_SECONDS
from .models import Candle, DataSourceUnavailable, SymbolRules


class CandleSource(Protocol):
    name: str

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]: ...

    def server_time_ms(self) -> int: ...


class TradingViewSource:
    name = "tradingview"

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
        raise DataSourceUnavailable(
            "TradingView MCP is not connected to this environment. Connect it at "
            "claude.ai/customize/connectors and start a new session."
        )

    def server_time_ms(self) -> int:
        raise DataSourceUnavailable("TradingView MCP is not connected.")


class BinancePublicSource:
    name = "binance"
    BASE = "https://data-api.binance.vision/api/v3"

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def _get(self, path: str, params: dict) -> object:
        url = f"{self.BASE}/{path}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            raise DataSourceUnavailable(f"Binance request failed: {path}: {e}") from e

    def server_time_ms(self) -> int:
        return int(self._get("time", {})["serverTime"])

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500, end_time: int | None = None) -> list[Candle]:
        if timeframe not in TIMEFRAME_SECONDS:
            raise ValueError(f"unsupported timeframe {timeframe}")
        params = {"symbol": symbol, "interval": timeframe, "limit": min(limit, 1000)}
        if end_time is not None:
            params["endTime"] = end_time
        rows = self._get("klines", params)
        return [
            Candle(symbol, timeframe, int(r[0]), int(r[6]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), self.name)
            for r in rows
        ]

    def fetch_history(self, symbol: str, timeframe: str, bars: int) -> list[Candle]:
        """Page backwards to collect up to `bars` candles, oldest first."""
        out: list[Candle] = []
        end = None
        while len(out) < bars:
            page = self.fetch_candles(symbol, timeframe, min(1000, bars - len(out)), end_time=end)
            if not page:
                break
            out = page + out
            end = page[0].open_time - 1
            if len(page) < 2:
                break
        dedup = {c.open_time: c for c in out}
        return [dedup[k] for k in sorted(dedup)]

    def symbol_rules(self, symbol: str) -> SymbolRules:
        info = self._get("exchangeInfo", {"symbol": symbol})
        s = info["symbols"][0]
        f = {x["filterType"]: x for x in s["filters"]}
        return SymbolRules(
            symbol=symbol,
            min_qty=float(f["LOT_SIZE"]["minQty"]),
            step_size=float(f["LOT_SIZE"]["stepSize"]),
            tick_size=float(f["PRICE_FILTER"]["tickSize"]),
            min_notional=float(f.get("NOTIONAL", f.get("MIN_NOTIONAL", {})).get("minNotional", 0.0)),
            status=s["status"],
        )
