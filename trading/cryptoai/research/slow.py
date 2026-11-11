"""Slower-timeframe research strategies. Rules: docs/SLOW_RESEARCH_RULES.md.

All conditions are evaluated on closed candles; orders fill at a later candle's open.
Each strategy returns trade paths for one coin (A-C) or for the BTC/ETH pair (D).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .. import indicators as ta
from ..backtest.engine import Path
from ..config import CostModel
from ..risk.sizing import loss_per_unit
from ..strategies import Signal

WARMUP = 250


@dataclass(frozen=True)
class Scenario:
    name: str
    costs: CostModel
    delay: int = 0  # extra candles before entering
    stop_extra: float = 0.0  # stops fill this much worse than the stop price


def _b(x):
    return np.nan_to_num(x, nan=0).astype(bool)


def btc_regime(btc_daily: dict, t_close: np.ndarray) -> np.ndarray:
    """BTC daily regime (1 bull, -1 bear, 0 sideways) from the last CLOSED daily candle."""
    c = btc_daily["close"]
    s200 = ta.sma(c, 200)
    lag = np.full(len(c), np.nan)
    lag[20:] = s200[:-20]
    st = np.where((c > s200) & (s200 > lag), 1, np.where((c < s200) & (s200 < lag), -1, 0)).astype(float)
    st[np.isnan(lag)] = 0
    return ta.align_closed(btc_daily["close_time"], st, t_close)


def sim_trade(d: dict, symbol: str, strategy: str, sig_bar: int, stop: float, exit_flags: np.ndarray,
              sc: Scenario, regime: np.ndarray, entry_bar: int | None = None) -> Path | None:
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    n = len(c)
    e = (sig_bar + 1 if entry_bar is None else entry_bar) + sc.delay
    if e >= n:
        return None
    entry = o[e]
    risk = entry - stop
    if risk <= 0:
        return None
    tp1 = entry + 2 * risk
    slip, fee = sc.costs.slippage, sc.costs.taker_fee
    fill_in = entry * (1 + slip)
    rem, cur_stop, be_pending, tp_done = 1.0, stop, False, False
    exits, outcome, exit_bar = [], None, None
    for j in range(e, n):
        if be_pending:
            cur_stop, be_pending = entry, False
        if l[j] <= cur_stop:
            px = cur_stop if j == e else min(cur_stop, o[j])
            exits.append((rem, px * (1 - sc.stop_extra) * (1 - slip)))
            outcome, rem, exit_bar = ("tp1+breakeven" if tp_done else "stop"), 0.0, j
            break
        if not tp_done and h[j] >= tp1:
            tp_done, be_pending = True, True
            exits.append((0.5, tp1))
            rem -= 0.5
        if exit_flags[j] and j + 1 < n:
            exits.append((rem, o[j + 1] * (1 - slip)))
            outcome, rem, exit_bar = ("tp1+exit rule" if tp_done else "exit rule"), 0.0, j + 1
            break
    if exit_bar is None:
        exits.append((rem, c[n - 1] * (1 - slip)))
        outcome, exit_bar = "open at end (marked)", n - 1
    pnl = sum(f * (px - fill_in) for f, px in exits)
    fees = fill_in * fee + sum(f * px * fee for f, px in exits)
    reg = {1: "bull", -1: "bear"}.get(int(np.nan_to_num(regime[sig_bar])), "sideways")
    return Path(Signal(symbol, strategy, "LONG", sig_bar, stop, ""), int(d["open_time"][e]), int(d["close_time"][exit_bar]),
                entry, stop, (tp1, np.nan, np.nan), pnl - fees, loss_per_unit(entry, stop, "LONG", sc.costs), outcome, reg, "n/a")


# ---------------- A: EMA 50/200 + ADX trend ----------------
def strat_A(d: dict):
    h, l, c = d["high"], d["low"], d["close"]
    e50, e200 = ta.ema(c, 50), ta.ema(c, 200)
    a, p, m = ta.adx(h, l, c, 14)
    atr = ta.atr(h, l, c, 14)
    cond = _b((c > e200) & (e50 > e200) & (a >= 25) & (p > m))
    fresh = cond & ~np.concatenate(([True], cond[:-1]))
    sigs = [(i, c[i] - 2.5 * atr[i]) for i in np.flatnonzero(fresh) if i >= WARMUP]
    return sigs, c < e50


# ---------------- B: higher-timeframe trend + pullback ----------------
def strat_B(d: dict, htf: dict):
    h, l, c = d["high"], d["low"], d["close"]
    e20, e50 = ta.ema(c, 20), ta.ema(c, 50)
    rsi = ta.rsi(c, 14)
    atr = ta.atr(h, l, c, 14)
    he20 = ta.ema(htf["close"], 20)
    hdir = np.concatenate(([0.0], ((htf["close"][1:] > he20[1:]) & (he20[1:] > he20[:-1])).astype(float)))
    direction = _b(ta.align_closed(htf["close_time"], hdir, d["close_time"]))
    sigs = []
    for i in range(WARMUP, len(c)):
        if not direction[i] or c[i] <= e50[i]:
            continue
        if not np.any(l[i - 2:i + 1] <= e20[i - 2:i + 1]):
            continue
        if c[i] > h[i - 1] and 45 <= rsi[i] <= 70:
            sigs.append((i, min(l[i - 4:i + 1].min() - 0.5 * atr[i], c[i] - 1.5 * atr[i])))
    return sigs, (c < e50) | ~direction


# ---------------- C: confirmed consolidation breakout ----------------
def strat_C(d: dict):
    h, l, c, v = d["high"], d["low"], d["close"], d["volume"]
    atr = ta.atr(h, l, c, 14)
    e20 = ta.ema(c, 20)
    vs = ta.sma(v, 20)
    bh, bl = ta.rolling_max(h, 10), ta.rolling_min(l, 10)  # the 10 candles BEFORE i
    sigs = []
    for i in range(WARMUP, len(c) - 1):
        if not (bh[i] - bl[i] <= 2.5 * atr[i - 1]):
            continue
        if c[i] > bh[i] and v[i] >= 1.5 * vs[i] and c[i + 1] > bh[i]:  # breakout, then the next candle confirms
            sigs.append((i + 1, bl[i] - 0.25 * atr[i + 1]))
    return sigs, c < e20


def single_coin_paths(strategy: str, sym: str, d: dict, sigs, exit_flags, sc: Scenario, regime) -> list[Path]:
    out = []
    for i, stop in sigs:
        p = sim_trade(d, sym, strategy, i, stop, exit_flags, sc, regime)
        if p is not None:
            out.append(p)
    return out


# ---------------- D: BTC/ETH weekly momentum rotation ----------------
def strat_D(btc: dict, eth: dict, sc: Scenario, regime) -> list[Path]:
    assert np.array_equal(btc["open_time"], eth["open_time"])
    coins = {"BTCUSDT": btc, "ETHUSDT": eth}
    stat = {}
    for s, d in coins.items():
        c = d["close"]
        sc28 = np.full(len(c), np.nan)
        sc28[28:] = c[28:] / c[:-28] - 1
        stat[s] = (sc28, ta.sma(c, 100), ta.atr(d["high"], d["low"], c, 14))
    t = btc["open_time"]
    mondays = [k for k in range(WARMUP, len(t)) if ((t[k] // 86_400_000) + 3) % 7 == 0]
    none = np.zeros(len(t), bool)
    paths, pos = [], None  # pos = (symbol, entry_monday_index, open-ended Path)

    def eligible(s, k):
        sc28, s100, _ = stat[s]
        return sc28[k - 1] > 0 and coins[s]["close"][k - 1] > s100[k - 1]

    def open_pos(s, k):
        _, _, atr = stat[s]
        stop = coins[s]["close"][k - 1] - 3.0 * atr[k - 1]
        p = sim_trade(coins[s], s, "D_rotation", k - 1, stop, none, sc, regime[s], entry_bar=k)
        return (s, k, p) if p is not None else None

    for k in mondays:
        if pos is not None and pos[2].exit_time < t[k]:
            paths.append(pos[2])  # closed by its stop (or breakeven stop) before this Monday
            pos = None
        held = pos[0] if pos else None
        el = {s: eligible(s, k) for s in coins}
        score = {s: stat[s][0][k - 1] for s in coins}
        target = held
        if held is None:
            cands = [s for s in coins if el[s]]
            target = max(cands, key=lambda s: score[s]) if cands else None
        else:
            other = "ETHUSDT" if held == "BTCUSDT" else "BTCUSDT"
            if not el[held]:
                target = other if el[other] else None
            elif el[other] and score[other] >= score[held] + 0.05:
                target = other
        if pos is not None and target != held:
            s, k0, _ = pos
            flags = np.zeros(len(t), bool)
            flags[k - 1] = True  # sell at this Monday's open
            p = sim_trade(coins[s], s, "D_rotation", k0 - 1, pos[2].stop, flags, sc, regime[s], entry_bar=k0)
            if p is not None:
                paths.append(p)
            pos = None
        if pos is None and target is not None:
            pos = open_pos(target, k)
    if pos is not None:
        paths.append(pos[2])
    return paths
