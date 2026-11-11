from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candle:
    """One OHLCV bar. Times are UTC milliseconds; close_time is the last ms of the bar."""

    symbol: str
    timeframe: str
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str


@dataclass(frozen=True)
class SymbolRules:
    """Exchange order rules. A trade that cannot satisfy them is skipped, never forced."""

    symbol: str
    min_qty: float
    step_size: float
    tick_size: float
    min_notional: float
    status: str


class DataSourceUnavailable(RuntimeError):
    """The source cannot be reached or is not connected. Never filled in with made-up data."""


class DataValidationError(ValueError):
    """Candles failed validation and must not be used for signals."""
