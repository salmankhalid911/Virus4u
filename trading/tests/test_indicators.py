import numpy as np
import pandas as pd
from cryptoai import indicators as ta

rng = np.random.default_rng(1)
close = 100 + np.cumsum(rng.normal(0, 1, 400))
high, low = close + rng.uniform(0, 1, 400), close - rng.uniform(0, 1, 400)

def test_ema_matches_pandas():
    assert np.allclose(ta.ema(close, 20), pd.Series(close).ewm(span=20, adjust=False).mean().values)

def test_rsi_bounds_and_extremes():
    r = ta.rsi(close)
    assert np.nanmin(r) >= 0 and np.nanmax(r) <= 100
    assert ta.rsi(np.arange(1, 40, dtype=float))[-1] == 100.0

def test_no_lookahead_in_any_indicator():
    """Changing future bars must not change any past value."""
    cut = 300
    fut_c = close.copy(); fut_c[cut:] *= 3
    fut_h, fut_l = high.copy(), low.copy(); fut_h[cut:] *= 3; fut_l[cut:] *= 3
    for f in (lambda c, h, l: ta.ema(c, 50), lambda c, h, l: ta.rsi(c), lambda c, h, l: ta.macd_hist(c),
              lambda c, h, l: ta.atr(h, l, c), lambda c, h, l: ta.rolling_max(h, 20), lambda c, h, l: ta.trend_state(c),
              lambda c, h, l: ta.confirmed_swings(h, l, 3)[0], lambda c, h, l: ta.confirmed_swings(h, l, 3)[1]):
        a, b = f(close, high, low), f(fut_c, fut_h, fut_l)
        assert np.allclose(a[:cut], b[:cut], equal_nan=True)

def test_swing_is_only_known_k_bars_later():
    h = np.array([1, 2, 3, 9, 3, 2, 1, 1, 1, 1], float); l = h - 0.5
    sh, _ = ta.confirmed_swings(h, l, 3)
    assert np.isnan(sh[5]) and sh[6] == 9  # peak at bar 3 is confirmed at bar 6

def test_align_closed_uses_only_closed_higher_timeframe_bars():
    h4_close = np.array([14_399_999, 28_799_999])  # 4h bars closing at 04:00 and 08:00
    vals = np.array([1.0, -1.0])
    ltf_close = np.array([14_399_999 - 900_000, 14_399_999, 28_799_999 - 1])
    out = ta.align_closed(h4_close, vals, ltf_close)
    assert np.isnan(out[0]) and out[1] == 1.0 and out[2] == 1.0

def test_adx_bounds_no_lookahead_and_trend_response():
    a, p, m = ta.adx(high, low, close)
    assert np.nanmin(a) >= 0 and np.nanmax(a) <= 100
    fut = close.copy(); fut[300:] *= 2; fh, fl = high.copy(), low.copy(); fh[300:] *= 2; fl[300:] *= 2
    assert np.allclose(a[:300], ta.adx(fh, fl, fut)[0][:300], equal_nan=True)
    up = np.arange(1, 200, dtype=float); a2, p2, m2 = ta.adx(up + 0.5, up - 0.5, up)
    assert a2[-1] > 50 and p2[-1] > m2[-1]

def test_weekly_candles_only_complete_weeks():
    day = 86_400_000
    t0 = 1704067200000  # 2024-01-01, a Monday
    t = t0 + np.arange(17) * day   # 2 full weeks + 3 days
    d = dict(open_time=t, close_time=t + day - 1, open=np.arange(17.), high=np.arange(17.) + 1, low=np.arange(17.) - 1, close=np.arange(17.) + .5, volume=np.ones(17))
    w = ta.weekly_from_daily(d)
    assert len(w["open_time"]) == 2 and w["open_time"][0] == t0 and w["close"][0] == 6.5 and w["high"][1] == 14 and w["volume"][0] == 7
