"""Backtest engine.

1. simulate_path: one signal -> one trade path, per unit, on closed candles after the signal.
   Entry at the next bar's open. Stops are checked before targets inside a bar (worst case),
   a gap through the stop fills at the open, and the breakeven stop after TP1 only applies
   from the next bar. Every fill pays fees and every market fill pays slippage.
2. run_account: the $100 account. Signals are processed in time order with the same
   sizing and risk gate as live paper trading, one open position per symbol.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from ..config import CostModel, RiskLimits, TIMEFRAME_SECONDS
from ..data.models import SymbolRules
from ..risk.limits import AccountState, TradeIdea, check_trade
from ..risk.sizing import loss_per_unit, size_position
from ..strategies import Context, Signal

TP_R = (2.0, 3.0, 4.0)
TP_FRACTION = (0.5, 0.3, 0.2)
SHORT_FUNDING_PER_8H = 0.0001  # shorts need a futures account; assume 0.01% per 8h paid


@dataclass
class Path:
    sig: Signal
    entry_time: int
    exit_time: int
    entry: float
    stop: float
    tps: tuple[float, float, float]
    pnl_per_unit: float  # after fees, slippage and funding
    risk_per_unit: float  # planned worst-case loss per unit (sizing basis)
    outcome: str
    regime_trend: str
    regime_vol: str

    @property
    def r(self) -> float:
        return self.pnl_per_unit / self.risk_per_unit


def simulate_path(x: Context, s: Signal, costs: CostModel, max_hold: int, vol_rank: np.ndarray) -> Path | None:
    i = s.bar + 1
    if i >= x.n:
        return None
    side = 1 if s.side == "LONG" else -1
    entry = x.o[i]
    risk = (entry - s.stop) * side
    if risk <= 0:
        return None  # price already beyond the stop at entry: setup void
    tps = tuple(entry + side * k * risk for k in TP_R)
    if s.target_cap is not None and (tps[0] - s.target_cap) * side > 0:
        return None  # TP1 does not fit inside the range: reward/risk too low
    slip, fee = costs.slippage, costs.taker_fee
    fill_in = entry * (1 + side * slip)
    remaining = 1.0
    done = [False, False, False]
    stop = s.stop
    be_pending = False
    exits: list[tuple[float, float]] = []  # (fraction, fill price)
    outcome = "time"
    last = min(i + max_hold, x.n - 1)
    j = i
    for j in range(i, last + 1):
        if be_pending:
            stop, be_pending = entry, False
        hit_stop = (x.l[j] <= stop) if side == 1 else (x.h[j] >= stop)
        if hit_stop:
            px = stop
            if j > i:  # a gap through the stop fills at the open
                px = min(stop, x.o[j]) if side == 1 else max(stop, x.o[j])
            exits.append((remaining, px * (1 - side * slip)))
            outcome = "stop" if not done[0] else ("breakeven" if not done[1] else "tp2+stop")
            remaining = 0
            break
        for k in range(3):
            if not done[k] and ((x.h[j] >= tps[k]) if side == 1 else (x.l[j] <= tps[k])):
                done[k] = True
                exits.append((TP_FRACTION[k], tps[k]))  # limit order: no slippage
                remaining -= TP_FRACTION[k]
                if k == 0:
                    be_pending = True
        if remaining <= 1e-9:
            outcome = "tp3"
            break
    if remaining > 1e-9:
        exits.append((remaining, x.c[j] * (1 - side * slip)))
        outcome = "time" if not done[0] else "tp1+time"
    pnl = sum(f * side * (px - fill_in) for f, px in exits)
    fees = fill_in * fee + sum(f * px * fee for f, px in exits)
    hours = (x.t_close[j] - x.t_open[i]) / 3_600_000
    funding = (fill_in * SHORT_FUNDING_PER_8H * hours / 8) if side == -1 else 0.0
    trend = {1: "bull", -1: "bear", 0: "sideways"}.get(int(np.nan_to_num(x.trend4h[s.bar])), "sideways")
    vol = "high_vol" if vol_rank[s.bar] >= 0.5 else "low_vol"
    return Path(s, int(x.t_open[i]), int(x.t_close[j]), entry, s.stop, tps, pnl - fees - funding,
                loss_per_unit(entry, s.stop, s.side, costs), outcome, trend, vol)


def volatility_rank(x: Context, window: int = 500) -> np.ndarray:
    """Percentile of today's ATR% among the previous `window` bars (past data only)."""
    atrp = x.atr / x.c
    out = np.full(x.n, 0.5)
    for i in range(window, x.n):
        past = atrp[i - window:i]
        out[i] = (past < atrp[i]).mean()
    return out


@dataclass
class Fill:
    path: Path
    qty: float
    notional: float
    pnl: float


@dataclass
class AccountResult:
    fills: list[Fill] = field(default_factory=list)
    equity_curve: list[tuple[int, float]] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)
    final_equity: float = 0.0


def _day(ms: int) -> tuple:
    d = datetime.fromtimestamp(ms / 1000, timezone.utc)
    return d.date()


def _week(ms: int) -> tuple:
    d = datetime.fromtimestamp(ms / 1000, timezone.utc)
    y, w, _ = d.isocalendar()
    return (y, w)


def run_account(paths: list[Path], rules: dict[str, SymbolRules], limits: RiskLimits, costs: CostModel,
                start_equity: float | None = None) -> AccountResult:
    eq = start_equity if start_equity is not None else limits.starting_equity
    res = AccountResult(equity_curve=[(paths[0].entry_time if paths else 0, eq)])
    open_: list[Fill] = []
    day = week = None
    day_start = week_peak = eq
    trades_today = 0

    def realize(upto: int):
        nonlocal eq, week_peak
        for f in sorted([f for f in open_ if f.path.exit_time <= upto], key=lambda f: f.path.exit_time):
            eq += f.pnl
            open_.remove(f)
            week_peak = max(week_peak, eq)
            res.equity_curve.append((f.path.exit_time, eq))

    for p in sorted(paths, key=lambda p: p.entry_time):
        realize(p.entry_time)
        d, w = _day(p.entry_time), _week(p.entry_time)
        if d != day:
            day, day_start, trades_today = d, eq, 0
        if w != week:
            week, week_peak = w, eq

        def skip(why):
            res.skipped[why] = res.skipped.get(why, 0) + 1

        if any(f.path.sig.symbol == p.sig.symbol for f in open_):
            skip("position already open on this symbol")
            continue
        acct = AccountState(eq, day_start, week_peak, trades_today, len(open_))
        gate = check_trade(TradeIdea(p.sig.side, p.entry, p.stop, p.tps[0], limits.default_risk_pct), acct, limits)
        if not gate.allowed:
            skip(gate.reasons[0].split(" (")[0])
            continue
        cash = eq - sum(f.notional for f in open_)
        size = size_position(eq, limits.default_risk_pct, limits.max_risk_pct, p.entry, p.stop, p.sig.side,
                             rules[p.sig.symbol], costs, cash, limits.max_leverage)
        if size.skipped:
            skip(size.reason.split(" $")[0].split(" 0")[0])
            continue
        trades_today += 1
        f = Fill(p, size.qty, size.notional, size.qty * p.pnl_per_unit)
        open_.append(f)
        res.fills.append(f)
    realize(2**62)
    res.final_equity = eq
    return res


def build_paths(x: Context, signals: list[Signal], costs: CostModel) -> list[Path]:
    max_hold = int(86400 / TIMEFRAME_SECONDS[x.tf]) if x.tf != "1h" else 48  # 1 day on 15m, 2 days on 1h
    vr = volatility_rank(x)
    out = []
    for s in signals:
        p = simulate_path(x, s, costs, max_hold, vr)
        if p is not None:
            out.append(p)
    return out
