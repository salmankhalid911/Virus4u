"""Indicators on numpy arrays. Every value at index i uses only bars 0..i (no look-ahead)."""
from __future__ import annotations

import numpy as np


def ema(x: np.ndarray, n: int) -> np.ndarray:
    k = 2.0 / (n + 1)
    out = np.empty(len(x))
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i - 1] + k * (x[i] - out[i - 1])
    return out


def sma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        c = np.cumsum(np.insert(x.astype(float), 0, 0.0))
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def rsi(close: np.ndarray, n: int = 14) -> np.ndarray:
    """Wilder's RSI."""
    d = np.diff(close, prepend=close[0])
    up, dn = np.clip(d, 0, None), np.clip(-d, 0, None)
    out = np.full(len(close), np.nan)
    if len(close) <= n:
        return out
    au, ad = up[1:n + 1].mean(), dn[1:n + 1].mean()
    for i in range(n, len(close)):
        if i > n:
            au = (au * (n - 1) + up[i]) / n
            ad = (ad * (n - 1) + dn[i]) / n
        out[i] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def macd_hist(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> np.ndarray:
    line = ema(close, fast) - ema(close, slow)
    return line - ema(line, signal)


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 14) -> np.ndarray:
    prev = np.concatenate(([close[0]], close[:-1]))
    tr = np.maximum(high - low, np.maximum(abs(high - prev), abs(low - prev)))
    out = np.full(len(tr), np.nan)
    if len(tr) <= n:
        return out
    out[n] = tr[1:n + 1].mean()
    for i in range(n + 1, len(tr)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def rolling_max(x: np.ndarray, n: int) -> np.ndarray:
    """Max of the n bars BEFORE i (excludes bar i)."""
    out = np.full(len(x), np.nan)
    for i in range(n, len(x)):
        out[i] = x[i - n:i].max()
    return out


def rolling_min(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    for i in range(n, len(x)):
        out[i] = x[i - n:i].min()
    return out


def confirmed_swings(high: np.ndarray, low: np.ndarray, k: int = 3):
    """Swing highs/lows that are only KNOWN k bars after they form.

    Returns (last_swing_high, last_swing_low) arrays where the value at index i is the most
    recent swing level confirmed by bar i. A swing at bar j needs k bars on each side, so it
    becomes visible at bar j+k, never earlier.
    """
    n = len(high)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    cur_h = cur_l = np.nan
    for i in range(2 * k, n):
        j = i - k
        if high[j] == high[j - k:j + k + 1].max():
            cur_h = high[j]
        if low[j] == low[j - k:j + k + 1].min():
            cur_l = low[j]
        sh[i], sl[i] = cur_h, cur_l
    return sh, sl


def align_closed(htf_close_time: np.ndarray, htf_values: np.ndarray, ltf_close_time: np.ndarray) -> np.ndarray:
    """For each lower-timeframe bar, the higher-timeframe value from the last HTF bar that had
    CLOSED by the time the lower-timeframe bar closed. NaN before the first closed HTF bar."""
    idx = np.searchsorted(htf_close_time, ltf_close_time, side="right") - 1
    out = np.full(len(ltf_close_time), np.nan)
    ok = idx >= 0
    out[ok] = htf_values[idx[ok]]
    return out


def trend_state(close: np.ndarray, fast: int = 20, slow: int = 50, slope_bars: int = 6) -> np.ndarray:
    """+1 bullish (close > EMA50 > rising, EMA20 > EMA50), -1 bearish, 0 neither."""
    e_f, e_s = ema(close, fast), ema(close, slow)
    out = np.zeros(len(close))
    for i in range(max(slow, slope_bars), len(close)):
        rising = e_s[i] > e_s[i - slope_bars]
        if close[i] > e_s[i] and e_f[i] > e_s[i] and rising:
            out[i] = 1
        elif close[i] < e_s[i] and e_f[i] < e_s[i] and not rising:
            out[i] = -1
    return out
