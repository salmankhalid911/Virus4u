"""Four independent strategies. Rule values are fixed here and were set before any backtest.

Each strategy reads a Context (one symbol, one signal timeframe, with the 4h trend and 1h
structure aligned to closed bars only) and returns signals. A signal at bar i means: bar i
has CLOSED and confirmed the setup; the trade would enter at the OPEN of bar i+1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .. import indicators as ta


@dataclass(frozen=True)
class Signal:
    symbol: str
    strategy: str
    side: str  # LONG / SHORT
    bar: int  # index of the confirming (closed) bar on the signal timeframe
    stop: float
    reason: str
    target_cap: float | None = None  # e.g. the far side of a range; TP1 must fit inside it


# Multi-timeframe map: signal timeframe -> (direction timeframe, structure timeframe)
MTF = {"5m": ("4h", "1h"), "15m": ("4h", "1h"), "1h": ("4h", "1h"), "4h": ("1d", "4h")}
VOL_MIN_RANK, VOL_MAX_RANK = 0.10, 0.95   # skip the calmest 10% and the wildest 5%
MIN_STOP_ATR, MAX_STOP_ATR = 1.0, 3.0      # stop at least 1 ATR, at most 3 ATR from the signal close


class Context:
    """h1/h4 are the STRUCTURE and DIRECTION series for this signal timeframe (see MTF)."""
    def __init__(self, symbol: str, tf: str, d: dict, h1: dict, h4: dict):
        self.symbol, self.tf = symbol, tf
        self.t_open, self.t_close = d["open_time"], d["close_time"]
        self.o, self.h, self.l, self.c, self.v = d["open"], d["high"], d["low"], d["close"], d["volume"]
        c = self.c
        self.ema20, self.ema50, self.ema200 = ta.ema(c, 20), ta.ema(c, 50), ta.ema(c, 200)
        self.rsi = ta.rsi(c, 14)
        self.macd_h = ta.macd_hist(c)
        self.atr = ta.atr(self.h, self.l, c, 14)
        self.vol_avg = ta.sma(self.v, 20)
        self.swing_h, self.swing_l = ta.confirmed_swings(self.h, self.l, 3)
        self.trend4h = ta.align_closed(h4["close_time"], ta.trend_state(h4["close"]), self.t_close)
        self.struct1h = ta.align_closed(h1["close_time"], ta.trend_state(h1["close"]), self.t_close)
        self.n = len(c)
        atrp = self.atr / c
        self.vol_rank = np.full(self.n, np.nan)
        for i in range(500, self.n):
            self.vol_rank[i] = (atrp[i - 500:i] < atrp[i]).mean()

    def vol_ok(self, i: int) -> bool:
        return VOL_MIN_RANK <= self.vol_rank[i] <= VOL_MAX_RANK

    def atr_stop(self, side: int, i: int, structure_stop: float) -> float | None:
        """Structure stop, widened to at least MIN_STOP_ATR; None if it would exceed MAX_STOP_ATR."""
        a, c = self.atr[i], self.c[i]
        stop = min(structure_stop, c - MIN_STOP_ATR * a) if side == 1 else max(structure_stop, c + MIN_STOP_ATR * a)
        return None if abs(c - stop) > MAX_STOP_ATR * a else stop


WARMUP = 520  # 500 bars for the volatility rank + indicator warmup


def trend_pullback(x: Context) -> list[Signal]:
    """A: trade with a 4h trend that 1h agrees with, on a pullback to EMA20 that holds."""
    out = []
    for i in range(WARMUP, x.n - 1):
        a = x.atr[i]
        vol_ok = x.v[i] >= x.vol_avg[i] and x.vol_ok(i)
        if x.trend4h[i] == 1 and x.struct1h[i] == 1 and x.ema20[i] > x.ema50[i] > x.ema200[i]:
            if x.l[i] <= x.ema20[i] < x.c[i] and x.c[i] > x.o[i] and 40 <= x.rsi[i] <= 65 and x.macd_h[i] > x.macd_h[i - 1] and vol_ok:
                st = x.atr_stop(1, i, x.l[i - 4:i + 1].min() - 0.25 * a)
                if st is not None:
                    out.append(Signal(x.symbol, "A_trend", "LONG", i, st, "pullback to EMA20 with higher-timeframe uptrend"))
        elif x.trend4h[i] == -1 and x.struct1h[i] == -1 and x.ema20[i] < x.ema50[i] < x.ema200[i]:
            if x.h[i] >= x.ema20[i] > x.c[i] and x.c[i] < x.o[i] and 35 <= x.rsi[i] <= 60 and x.macd_h[i] < x.macd_h[i - 1] and vol_ok:
                st = x.atr_stop(-1, i, x.h[i - 4:i + 1].max() + 0.25 * a)
                if st is not None:
                    out.append(Signal(x.symbol, "A_trend", "SHORT", i, st, "rally to EMA20 with higher-timeframe downtrend"))
    return out


def breakout_retest(x: Context, look: int = 20, wait: int = 8) -> list[Signal]:
    """B: tight range, breakout close with 1.5x volume, then a retest that holds."""
    out = []
    i = WARMUP
    while i < x.n - 1:
        a = x.atr[i]
        top, bot = x.h[i - look:i].max(), x.l[i - look:i].min()
        tight = (top - bot) <= 4 * a and x.vol_ok(i)
        side = 0
        if tight and x.c[i] > top and x.v[i] >= 1.5 * x.vol_avg[i] and x.trend4h[i] != -1:
            side = 1
        elif tight and x.c[i] < bot and x.v[i] >= 1.5 * x.vol_avg[i] and x.trend4h[i] != 1:
            side = -1
        if not side:
            i += 1
            continue
        level = top if side == 1 else bot
        for j in range(i + 1, min(i + 1 + wait, x.n - 1)):
            aj = x.atr[j]
            if side == 1:
                if x.c[j] < level - 0.5 * aj:  # fell back into the range: false breakout
                    break
                if x.l[j] <= level + 0.2 * aj and x.c[j] > level and x.c[j] > x.o[j]:
                    st = x.atr_stop(1, j, min(x.l[j], level) - 0.25 * aj)
                    if st is not None:
                        out.append(Signal(x.symbol, "B_breakout", "LONG", j, st, "breakout on 1.5x volume, retest held"))
                    break
            else:
                if x.c[j] > level + 0.5 * aj:
                    break
                if x.h[j] >= level - 0.2 * aj and x.c[j] < level and x.c[j] < x.o[j]:
                    st = x.atr_stop(-1, j, max(x.h[j], level) + 0.25 * aj)
                    if st is not None:
                        out.append(Signal(x.symbol, "B_breakout", "SHORT", j, st, "breakdown on 1.5x volume, retest held"))
                    break
        i += look // 2  # one setup per range
    return out


def liquidity_structure(x: Context, wait: int = 10) -> list[Signal]:
    """C: sweep of a confirmed swing that is reclaimed, then a displacement close through the
    opposite swing (change of character)."""
    out = []
    i = WARMUP
    while i < x.n - 1:
        sl, sh, a = x.swing_l[i - 1], x.swing_h[i - 1], x.atr[i]
        side = 0
        if not np.isnan(sl) and x.l[i] < sl < x.c[i] and x.trend4h[i] != -1:
            side, sweep_px, target_lvl = 1, x.l[i], sh
        elif not np.isnan(sh) and x.h[i] > sh > x.c[i] and x.trend4h[i] != 1:
            side, sweep_px, target_lvl = -1, x.h[i], sl
        if not side or np.isnan(target_lvl):
            i += 1
            continue
        hit = None
        for j in range(i + 1, min(i + 1 + wait, x.n - 1)):
            body = abs(x.c[j] - x.o[j])
            if side == 1 and x.l[j] < sweep_px:
                break
            if side == -1 and x.h[j] > sweep_px:
                break
            vol_ok = x.v[j] >= 1.2 * x.vol_avg[j] and x.vol_ok(j)
            if side == 1 and x.c[j] > target_lvl and body >= 1.2 * x.atr[j] and x.c[j] > x.o[j] and vol_ok:
                hit = j
                break
            if side == -1 and x.c[j] < target_lvl and body >= 1.2 * x.atr[j] and x.c[j] < x.o[j] and vol_ok:
                hit = j
                break
        if hit is not None:
            st = x.atr_stop(side, hit, sweep_px - side * 0.1 * a)
            if st is not None:
                out.append(Signal(x.symbol, "C_liquidity", "LONG" if side == 1 else "SHORT", hit, st,
                                  "swept swing low, CHOCH up with displacement" if side == 1 else "swept swing high, CHOCH down with displacement"))
            i = hit + 1
        else:
            i += 1
    return out


def range_reversion(x: Context, look: int = 48) -> list[Signal]:
    """D: only when the 4h trend is flat. Fade the edge of a 3-10 ATR range with RSI and volume."""
    out = []
    for i in range(WARMUP, x.n - 1):
        if x.trend4h[i] != 0:
            continue
        a = x.atr[i]
        top, bot = x.h[i - look:i].max(), x.l[i - look:i].min()
        width = top - bot
        if not (3 * a <= width <= 10 * a):
            continue
        pos = (x.c[i] - bot) / width
        vol_ok = x.v[i] >= x.vol_avg[i] and x.vol_ok(i)
        if pos <= 0.15 and x.rsi[i] < 35 and x.c[i] > x.o[i] and vol_ok and x.l[i] >= bot - 0.5 * a:
            st = x.atr_stop(1, i, bot - 0.5 * a)
            if st is not None:
                out.append(Signal(x.symbol, "D_range", "LONG", i, st, "bottom of range, RSI < 35", target_cap=top))
        elif pos >= 0.85 and x.rsi[i] > 65 and x.c[i] < x.o[i] and vol_ok and x.h[i] <= top + 0.5 * a:
            st = x.atr_stop(-1, i, top + 0.5 * a)
            if st is not None:
                out.append(Signal(x.symbol, "D_range", "SHORT", i, st, "top of range, RSI > 65", target_cap=bot))
    return out


STRATEGIES = {
    "A_trend": trend_pullback,
    "B_breakout": breakout_retest,
    "C_liquidity": liquidity_structure,
    "D_range": range_reversion,
}
