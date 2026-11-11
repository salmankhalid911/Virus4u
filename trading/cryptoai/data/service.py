"""Fetch -> validate -> store, with the primary/secondary source fallback."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from ..config import Settings
from . import store
from .models import Candle, DataSourceUnavailable, DataValidationError
from .sources import BinancePublicSource, CandleSource, TradingViewSource
from .validation import ValidationReport, validate_candles

log = logging.getLogger(__name__)


@dataclass
class FetchResult:
    symbol: str
    timeframe: str
    source: str | None
    candles: list[Candle]
    report: ValidationReport | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.report is not None and self.report.ok


class MarketDataService:
    def __init__(self, settings: Settings, sources: list[CandleSource] | None = None, clock_source: CandleSource | None = None):
        self.settings = settings
        self.sources = sources or [TradingViewSource(), BinancePublicSource()]
        # Freshness is judged against an exchange server clock, not this machine's clock.
        self.clock = clock_source or next((s for s in self.sources if isinstance(s, BinancePublicSource)), self.sources[-1])
        self.con = store.connect(settings.db_path)

    def now_ms(self) -> int:
        return self.clock.server_time_ms()

    def fetch(self, symbol: str, timeframe: str, limit: int = 500) -> FetchResult:
        errors = []
        now = self.now_ms()
        for src in self.sources:
            try:
                raw = src.fetch_candles(symbol, timeframe, limit)
                clean, rep = validate_candles(raw, timeframe, now, self.settings.max_staleness_bars)
            except DataSourceUnavailable as e:
                errors.append(f"{src.name}: unavailable ({e})")
                continue
            except DataValidationError as e:
                errors.append(f"{src.name}: rejected ({e})")
                log.warning("rejected %s %s from %s: %s", symbol, timeframe, src.name, e)
                continue
            store.upsert_candles(self.con, clean)
            return FetchResult(symbol, timeframe, src.name, clean, rep)
        return FetchResult(symbol, timeframe, None, [], None, error=" | ".join(errors))
