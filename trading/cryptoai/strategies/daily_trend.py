"""Daily trend-following (rules in docs/DAILY_TREND_RULES.md).

Entry and exit conditions are evaluated on CLOSED daily candles; orders fill at the next
day's open. Uses past bars only (prior-N highs/lows exclude the current bar).
"""
from __future__ import annotations

import numpy as np

from .. import indicators as ta
from ..backtest.engine import Path
from ..config import CostModel
from . import Signal

SHORT_FUNDING_PER_8H = 0.0001


def _conditions(name: str, d: dict, side: int):
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    n = len(c)
    atr = ta.atr(h, l, c, 20)
    enter = np.zeros(n, bool)
    leave = np.zeros(n, bool)
    if name == "T1_donchian":
        hi55, lo55 = ta.rolling_max(h, 55), ta.rolling_min(l, 55)
        hi20, lo20 = ta.rolling_max(h, 20), ta.rolling_min(l, 20)
        enter = (c > hi55) if side == 1 else (c < lo55)
        leave = (c < lo20) if side == 1 else (c > hi20)
        stop_mult = 2.5
    elif name == "T2_momentum":
        sma100 = ta.sma(c, 100)
        ret60 = np.full(n, np.nan)
        ret60[60:] = c[60:] / c[:-60] - 1
        cond = (c > sma100) & (ret60 > 0) if side == 1 else (c < sma100) & (ret60 < 0)
        cond = np.nan_to_num(cond).astype(bool)
        prev = np.concatenate(([False], cond[:-1]))
        enter = cond & ~prev
        leave = ~cond
        stop_mult = 3.0
    else:
        raise ValueError(name)
    enter = np.nan_to_num(enter).astype(bool)
    leave = np.nan_to_num(leave).astype(bool)
    stop = c - side * stop_mult * atr
    return enter, leave, stop, atr


def simulate(name: str, symbol: str, d: dict, side: int, costs: CostModel, warmup: int = 120) -> list[Path]:
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    t_open, t_close = d["open_time"], d["close_time"]
    enter, leave, stop_arr, atr = _conditions(name, d, side)
    trend = ta.trend_state(c)
    atrp = atr / c
    out: list[Path] = []
    slip, fee = costs.slippage, costs.taker_fee
    sname = "LONG" if side == 1 else "SHORT"
    i = warmup
    n = len(c)
    while i < n - 1:
        if not enter[i] or np.isnan(stop_arr[i]):
            i += 1
            continue
        e = i + 1
        entry, stop0 = o[e], stop_arr[i]
        risk = (entry - stop0) * side
        if risk <= 0:
            i += 1
            continue
        tp1 = entry + side * 2 * risk
        fill_in = entry * (1 + side * slip)
        rem, stop, be_pending, tp_done = 1.0, stop0, False, False
        exits = []
        outcome, j, exit_bar = None, e, None
        for j in range(e, n):
            if be_pending:
                stop, be_pending = entry, False
            if (l[j] <= stop) if side == 1 else (h[j] >= stop):
                px = stop if j == e else (min(stop, o[j]) if side == 1 else max(stop, o[j]))
                exits.append((rem, px * (1 - side * slip)))
                outcome = "stop" if not tp_done else "tp1+breakeven"
                rem, exit_bar = 0.0, j
                break
            if not tp_done and ((h[j] >= tp1) if side == 1 else (l[j] <= tp1)):
                tp_done, be_pending = True, True
                exits.append((0.5, tp1))
                rem -= 0.5
            if leave[j] and j + 1 < n:  # trend exit at the next open
                px = o[j + 1] * (1 - side * slip)
                exits.append((rem, px))
                outcome = "tp1+trend exit" if tp_done else "trend exit"
                rem, exit_bar = 0.0, j + 1
                break
        if exit_bar is None:
            break  # still open at the end of the data: not counted
        pnl = sum(f * side * (px - fill_in) for f, px in exits)
        fees = fill_in * fee + sum(f * px * fee for f, px in exits)
        hours = (t_close[exit_bar] - t_open[e]) / 3_600_000
        funding = fill_in * SHORT_FUNDING_PER_8H * hours / 8 if side == -1 else 0.0
        past = atrp[max(0, i - 250):i]
        vr = float((past < atrp[i]).mean()) if len(past) else 0.5
        per_unit_risk = (entry * (1 + side * slip) - stop0 * (1 - side * slip)) * side + (entry + stop0) * fee
        sig = Signal(symbol, name, sname, i, stop0, "")
        out.append(Path(sig, int(t_open[e]), int(t_close[exit_bar]), entry, stop0, (tp1, np.nan, np.nan),
                        pnl - fees - funding, per_unit_risk, outcome,
                        {1: "bull", -1: "bear"}.get(int(trend[i]), "sideways"), "high_vol" if vr >= 0.5 else "low_vol"))
        i = exit_bar  # no overlapping trades for the same strategy and coin
    return out
