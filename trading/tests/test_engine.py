import numpy as np
from cryptoai.backtest.engine import Path, run_account, simulate_path
from cryptoai.config import CostModel, RiskLimits
from cryptoai.data.models import SymbolRules
from cryptoai.strategies import Signal

COST0 = CostModel(taker_fee=0, maker_fee=0, slippage=0)

class X:  # minimal context
    def __init__(self, o, h, l, c, trend=0):
        self.o, self.h, self.l, self.c = map(np.array, (o, h, l, c))
        self.n = len(self.o); self.tf = "15m"
        self.t_open = np.arange(self.n) * 900_000; self.t_close = self.t_open + 899_999
        self.trend4h = np.full(self.n, trend, float)

VR = np.full(10, 0.5)

def test_stop_checked_before_target_in_same_bar():
    x = X([100]*4, [100, 100, 104, 100], [100, 100, 98, 100], [100]*4)
    p = simulate_path(x, Signal("T", "s", "LONG", 0, 99, ""), COST0, 10, VR)
    assert p.outcome == "stop" and abs(p.r + 1) < 1e-9

def test_take_profits_and_breakeven_after_tp1():
    # entry 100, risk 1: TP1 102 hit on bar 1; bar 2 dips to entry -> breakeven stop
    x = X([100, 100, 101, 101], [100, 102.5, 101, 101], [100, 100.5, 99.9, 101], [100, 101, 100.5, 101])
    p = simulate_path(x, Signal("T", "s", "LONG", 0, 99, ""), COST0, 10, VR)
    assert p.outcome == "breakeven" and abs(p.pnl_per_unit - 0.5 * 2) < 1e-9

def test_gap_through_stop_fills_at_open():
    x = X([100, 100, 95], [100, 100.5, 95], [100, 99.5, 94], [100, 100, 95])
    p = simulate_path(x, Signal("T", "s", "LONG", 0, 99, ""), COST0, 10, VR)
    assert p.outcome == "stop" and abs(p.pnl_per_unit - (95 - 100)) < 1e-9

def test_fees_reduce_pnl():
    x = X([100]*4, [100, 102.5, 103.5, 104.5], [100, 100, 101, 102], [100, 102, 103, 104])
    s = Signal("T", "s", "LONG", 0, 99, "")
    assert simulate_path(x, s, CostModel(), 10, VR).pnl_per_unit < simulate_path(x, s, COST0, 10, VR).pnl_per_unit

def _path(t, pnl_r, sym="BTCUSDT"):
    return Path(Signal(sym, "s", "LONG", 0, 99, ""), t, t + 1, 100.0, 99.0, (102, 103, 104), pnl_r * 1.0, 1.0, "x", "bull", "low_vol")

RULES = {s: SymbolRules(s, 0.001, 0.001, 0.01, 5.0, "TRADING") for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")}

def test_account_stops_after_three_trades_a_day_and_daily_loss():
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
    paths = [_path(1000 + i * 10, 2.0, syms[i]) for i in range(4)]  # 4 winners, same day
    res = run_account(paths, RULES, RiskLimits(), COST0)
    assert len(res.fills) == 3 and res.skipped
    losers = [_path(1000 + i * 10, -4.5, syms[i % 4]) for i in range(3)]  # each loses ~2.25% if sized at 0.5%? capped by qty
    res2 = run_account(losers, RULES, RiskLimits(), COST0)
    assert res2.final_equity < 100

def test_loss_never_exceeds_risk_budget_on_stop():
    res = run_account([_path(1000, -1.0)], RULES, RiskLimits(), COST0)
    assert abs(res.fills[0].pnl) <= 0.5 + 1e-9
