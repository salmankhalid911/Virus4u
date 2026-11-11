"""Candle validation. Anything that fails here never reaches a strategy.

Rules:
- the still-forming candle (close_time >= now) is dropped: signals use closed candles only
- every candle must have positive prices with low <= open, close <= high, and volume >= 0
- times must be strictly increasing, aligned to the timeframe, with no duplicates
- gaps (missing bars) are reported; too many gaps rejects the series
- the newest closed candle must be fresh (no older than max_staleness_bars bar lengths)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import TIMEFRAME_SECONDS
from .models import Candle, DataValidationError


@dataclass
class ValidationReport:
    symbol: str
    timeframe: str
    received: int
    accepted: int = 0
    dropped_unclosed: int = 0
    gaps: list[tuple[int, int]] = field(default_factory=list)  # (after_open_time, missing_bars)
    latest_close_time: int | None = None
    age_seconds: float | None = None
    fresh: bool = False
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems and self.fresh


def validate_candles(
    candles: list[Candle],
    timeframe: str,
    now_ms: int,
    max_staleness_bars: float = 2.0,
    max_gap_fraction: float = 0.01,
    require_fresh: bool = True,
) -> tuple[list[Candle], ValidationReport]:
    """Return (clean closed candles, report). Raises DataValidationError on hard failures."""
    step = TIMEFRAME_SECONDS[timeframe] * 1000
    sym = candles[0].symbol if candles else "?"
    rep = ValidationReport(sym, timeframe, len(candles))
    if not candles:
        rep.problems.append("no candles")
        raise DataValidationError(f"{sym} {timeframe}: no candles")

    closed = [c for c in candles if c.close_time < now_ms]
    rep.dropped_unclosed = len(candles) - len(closed)

    prev = None
    for c in closed:
        if c.timeframe != timeframe or c.symbol != sym:
            rep.problems.append(f"mixed series at {c.open_time}")
        if min(c.open, c.high, c.low, c.close) <= 0:
            rep.problems.append(f"non-positive price at {c.open_time}")
        if not (c.low <= min(c.open, c.close) and max(c.open, c.close) <= c.high):
            rep.problems.append(f"OHLC inconsistent at {c.open_time}")
        if c.volume < 0:
            rep.problems.append(f"negative volume at {c.open_time}")
        if c.open_time % step != 0:
            rep.problems.append(f"misaligned open time {c.open_time}")
        if c.close_time != c.open_time + step - 1:
            rep.problems.append(f"bad close time at {c.open_time}")
        if prev is not None:
            if c.open_time <= prev.open_time:
                rep.problems.append(f"out of order or duplicate at {c.open_time}")
            elif c.open_time - prev.open_time > step:
                rep.gaps.append((prev.open_time, (c.open_time - prev.open_time) // step - 1))
        prev = c

    missing = sum(m for _, m in rep.gaps)
    if closed and missing > max_gap_fraction * len(closed):
        rep.problems.append(f"{missing} missing bars ({len(rep.gaps)} gaps)")

    if closed:
        rep.latest_close_time = closed[-1].close_time
        rep.age_seconds = (now_ms - closed[-1].close_time) / 1000
        rep.fresh = rep.age_seconds <= max_staleness_bars * TIMEFRAME_SECONDS[timeframe]
        if require_fresh and not rep.fresh:
            rep.problems.append(f"stale: newest closed candle is {rep.age_seconds:.0f}s old")
    else:
        rep.problems.append("no closed candles")

    rep.accepted = len(closed)
    if rep.problems:
        raise DataValidationError(f"{sym} {timeframe}: " + "; ".join(rep.problems[:5]))
    return closed, rep
