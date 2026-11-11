import numpy as np
from cryptoai.config import CostModel
from cryptoai.strategies.daily_trend import simulate

DAY = 86_400_000
def series(close):
    c = np.array(close, float); o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * 1.002; l = np.minimum(o, c) * 0.998
    t = np.arange(len(c)) * DAY
    return dict(open_time=t, close_time=t + DAY - 1, open=o, high=h, low=l, close=c, volume=np.ones(len(c)))

def test_breakout_trade_enters_next_open_and_exits_on_trend_break():
    flat = [100 + (i % 2) for i in range(150)]
    up = [101 + 1.5 * i for i in range(1, 80)]
    down = [up[-1] - 3 * i for i in range(1, 40)]
    d = series(flat + up + down)
    ps = simulate("T1_donchian", "BTCUSDT", d, 1, CostModel(taker_fee=0, maker_fee=0, slippage=0))
    assert ps, "expected a long trade"
    p = ps[0]
    assert p.entry == d["open"][p.sig.bar + 1]            # filled at the next open, not the signal close
    assert p.pnl_per_unit > 0 and "tp1" in p.outcome       # took the first target in the uptrend

def test_no_lookahead_future_change_does_not_change_past_trades():
    rng = np.random.default_rng(3)
    c = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, 900)))
    a = simulate("T2_momentum", "BTCUSDT", series(c), 1, CostModel())
    c2 = c.copy(); c2[700:] *= 0.3
    b = simulate("T2_momentum", "BTCUSDT", series(c2), 1, CostModel())
    done_a = [(p.entry_time, p.exit_time, round(p.pnl_per_unit, 9)) for p in a if p.exit_time < 699 * DAY]
    done_b = [(p.entry_time, p.exit_time, round(p.pnl_per_unit, 9)) for p in b if p.exit_time < 699 * DAY]
    assert done_a and done_a == done_b
