import sqlite3
import numpy as np
import pytest
from cryptoai.backtest.engine import simulate_path
from cryptoai.config import CostModel
from cryptoai.execution.paper import Bar, PaperBroker
from cryptoai.signals import TradeCard
from cryptoai.strategies import Signal

STEP = 900_000

class X:
    def __init__(self, o, h, l, c):
        self.o, self.h, self.l, self.c = map(np.array, (o, h, l, c)); self.n = len(self.o); self.tf = "15m"
        self.t_open = np.arange(self.n) * STEP; self.t_close = self.t_open + STEP - 1; self.trend4h = np.zeros(self.n)

def card(side, stop, entry_guess=100.0):
    k = 1 if side == "LONG" else -1
    r = abs(entry_guess - stop)
    return TradeCard("BTCUSDT", side, "t", entry_guess, entry_guess, stop, *(entry_guess + k * m * r for m in (2, 3, 4)),
                     2, 1.0, entry_guess, 0, "n/a", "15m", "", "", "")

@pytest.mark.parametrize("seed", range(40))
@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_paper_broker_matches_backtest(seed, side):
    rng = np.random.default_rng(seed)
    n = 30
    c = 100 + np.cumsum(rng.normal(0, 0.6, n)); c[0] = c[1] = 100.0
    o = np.concatenate(([100.0, 100.0], c[1:-1])); h = np.maximum(o, c) + rng.uniform(0, .5, n); l = np.minimum(o, c) - rng.uniform(0, .5, n)
    x = X(o, h, l, c)
    stop = 99.0 if side == "LONG" else 101.0
    costs = CostModel()
    p = simulate_path(x, Signal("BTCUSDT", "t", side, 0, stop, ""), costs, 20, np.full(n, .5))
    con = sqlite3.connect(":memory:"); b = PaperBroker(con, costs, 100.0)
    b.record_signal("sig", 0, "BTCUSDT", "t", side, "15m", "SETUP DETECTED", card=card(side, stop, o[1]))
    bar = lambda j: Bar(int(x.t_open[j]), int(x.t_close[j]), o[j], h[j], l[j], c[j])
    assert b.open_from_card("sig", card(side, stop, o[1]), bar(1))
    for j in range(1, n):
        b.on_bar("BTCUSDT", bar(j), max_hold_ms=21 * STEP - 1)
    assert not b.open_positions()
    assert abs((b.equity - 100.0) - p.pnl_per_unit) < 1e-9

def test_same_signal_never_opens_twice():
    con = sqlite3.connect(":memory:"); b = PaperBroker(con, CostModel(), 100.0)
    assert b.record_signal("s1", 0, "BTCUSDT", "t", "LONG", "15m", "SETUP DETECTED")
    assert not b.record_signal("s1", 0, "BTCUSDT", "t", "LONG", "15m", "SETUP DETECTED")
    cd = card("LONG", 99.0)
    assert b.open_from_card("s1", cd, Bar(0, STEP - 1, 100, 100, 100, 100))
    assert not b.open_from_card("s1", cd, Bar(0, STEP - 1, 100, 100, 100, 100))

def test_bars_before_entry_are_ignored_and_replays_are_idempotent():
    con = sqlite3.connect(":memory:"); b = PaperBroker(con, CostModel(), 100.0)
    b.record_signal("s", 0, "BTCUSDT", "t", "LONG", "15m", "SETUP DETECTED")
    assert b.open_from_card("s", card("LONG", 99.0), Bar(5 * STEP, 6 * STEP - 1, 100, 100, 100, 100))
    crash = Bar(2 * STEP, 3 * STEP - 1, 100, 100, 90, 95)   # before entry: must not stop us out
    b.on_bar("BTCUSDT", crash, 10**12)
    assert b.open_positions()
    tp = Bar(6 * STEP, 7 * STEP - 1, 100, 102.5, 100, 102)
    for _ in range(3):                                      # replaying the same candle changes nothing
        b.on_bar("BTCUSDT", tp, 10**12)
    row = con.execute("SELECT remaining FROM positions").fetchone()
    assert abs(row[0] - 0.5) < 1e-9
