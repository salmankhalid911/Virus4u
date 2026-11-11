import numpy as np
from cryptoai import indicators as ta
from cryptoai.config import CostModel
from cryptoai.research.slow import Scenario, strat_A, strat_B, strat_C, strat_D

DAY = 86_400_000
def series(seed, n=900, t0=1704067200000 - 400 * DAY):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, n)))
    o = np.concatenate(([c[0]], c[:-1])); h = np.maximum(o, c) * (1 + rng.uniform(0, .02, n)); l = np.minimum(o, c) * (1 - rng.uniform(0, .02, n))
    t = t0 + np.arange(n) * DAY
    return dict(open_time=t, close_time=t + DAY - 1, open=o, high=h, low=l, close=c, volume=rng.uniform(1, 3, n))

def cut(d, k):
    return {key: v[:k] for key, v in d.items()}

def test_no_strategy_uses_future_prices():
    d = series(1); k = 700
    for name, f in (("A", lambda x: strat_A(x)), ("B", lambda x: strat_B(x, ta.weekly_from_daily(x))), ("C", lambda x: strat_C(x))):
        full, _ = f(d); part, _ = f(cut(d, k))
        a = [(i, round(s, 9)) for i, s in full if i < k - 1]
        b = [(i, round(s, 9)) for i, s in part if i < k - 1]
        assert a == b, name
        assert all(i >= 1 for i, _ in full)

def test_rotation_decisions_ignore_future_prices():
    b, e = series(2), series(3)
    reg = {"BTCUSDT": np.zeros(900), "ETHUSDT": np.zeros(900)}
    sc = Scenario("base", CostModel())
    full = strat_D(b, e, sc, reg)
    part = strat_D(cut(b, 700), cut(e, 700), sc, {k: v[:700] for k, v in reg.items()})
    done = lambda ps: [(p.sig.symbol, p.entry_time, p.exit_time, round(p.pnl_per_unit, 9)) for p in ps if p.exit_time < b["open_time"][690]]
    assert done(full) and done(full) == done(part)
    # never holds two coins at once
    ps = sorted(full, key=lambda p: p.entry_time)
    assert all(ps[i + 1].entry_time > ps[i].exit_time - DAY for i in range(len(ps) - 1))
