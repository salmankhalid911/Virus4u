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


class Context:
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


WARMUP = 220


def trend_pullback(x: Context) -> list[Signal]:
    """A: trade with a 4h trend that 1h agrees with, on a pullback to EMA20 that holds."""
    out = []
    for i in range(WARMUP, x.n - 1):
        a = x.atr[i]
        vol_ok = x.v[i] >= x.vol_avg[i]
        if x.trend4h[i] == 1 and x.struct1h[i] == 1 and x.ema20[i] > x.ema50[i] > x.ema200[i]:
            if x.l[i] <= x.ema20[i] < x.c[i] and x.c[i] > x.o[i] and 40 <= x.rsi[i] <= 65 and x.macd_h[i] > x.macd_h[i - 1] and vol_ok:
                out.append(Signal(x.symbol, "A_trend", "LONG", i, x.l[i - 4:i + 1].min() - 0.25 * a, "pullback to EMA20 in 4h/1h uptrend"))
        elif x.trend4h[i] == -1 and x.struct1h[i] == -1 and x.ema20[i] < x.ema50[i] < x.ema200[i]:
            if x.h[i] >= x.ema20[i] > x.c[i] and x.c[i] < x.o[i] and 35 <= x.rsi[i] <= 60 and x.macd_h[i] < x.macd_h[i - 1] and vol_ok:
                out.append(Signal(x.symbol, "A_trend", "SHORT", i, x.h[i - 4:i + 1].max() + 0.25 * a, "rally to EMA20 in 4h/1h downtrend"))
    return out


def breakout_retest(x: Context, look: int = 20, wait: int = 8) -> list[Signal]:
    """B: tight range, breakout close with 1.5x volume, then a retest that holds."""
    out = []
    i = WARMUP
    while i < x.n - 1:
        a = x.atr[i]
        top, bot = x.h[i - look:i].max(), x.l[i - look:i].min()
        tight = (top - bot) <= 4 * a
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
                    out.append(Signal(x.symbol, "B_breakout", "LONG", j, min(x.l[j], level) - 0.25 * aj, "breakout, retest held"))
                    break
            else:
                if x.c[j] > level + 0.5 * aj:
                    break
                if x.h[j] >= level - 0.2 * aj and x.c[j] < level and x.c[j] < x.o[j]:
                    out.append(Signal(x.symbol, "B_breakout", "SHORT", j, max(x.h[j], level) + 0.25 * aj, "breakdown, retest held"))
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
            if side == 1 and x.c[j] > target_lvl and body >= 1.2 * x.atr[j] and x.c[j] > x.o[j]:
                hit = j
                break
            if side == -1 and x.c[j] < target_lvl and body >= 1.2 * x.atr[j] and x.c[j] < x.o[j]:
                hit = j
                break
        if hit is not None:
            if side == 1:
                out.append(Signal(x.symbol, "C_liquidity", "LONG", hit, sweep_px - 0.1 * a, "swept swing low, CHOCH up with displacement"))
            else:
                out.append(Signal(x.symbol, "C_liquidity", "SHORT", hit, sweep_px + 0.1 * a, "swept swing high, CHOCH down with displacement"))
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
        vol_ok = x.v[i] >= x.vol_avg[i]
        if pos <= 0.15 and x.rsi[i] < 35 and x.c[i] > x.o[i] and vol_ok and x.l[i] >= bot - 0.5 * a:
            out.append(Signal(x.symbol, "D_range", "LONG", i, bot - 0.5 * a, "bottom of range, RSI < 35", target_cap=top))
        elif pos >= 0.85 and x.rsi[i] > 65 and x.c[i] < x.o[i] and vol_ok and x.h[i] <= top + 0.5 * a:
            out.append(Signal(x.symbol, "D_range", "SHORT", i, top + 0.5 * a, "top of range, RSI > 65", target_cap=bot))
    return out


STRATEGIES = {
    "A_trend": trend_pullback,
    "B_breakout": breakout_retest,
    "C_liquidity": liquidity_structure,
    "D_range": range_reversion,
}
