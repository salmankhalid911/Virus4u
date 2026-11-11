import pytest
from cryptoai.data.models import Candle, DataValidationError
from cryptoai.data.validation import validate_candles

STEP = 300_000  # 5m

def bars(n, start=1_700_000_100 * 1000 // STEP * STEP, **over):
    out = []
    for i in range(n):
        t = start + i * STEP
        out.append(Candle("BTCUSDT", "5m", t, t + STEP - 1, 100, 101, 99, 100.5, 10, "test"))
    return out

def test_drops_unclosed_candle_and_accepts_fresh_series():
    b = bars(10)
    now = b[-1].open_time + 60_000  # last bar still forming
    clean, rep = validate_candles(b, "5m", now)
    assert len(clean) == 9 and rep.dropped_unclosed == 1 and rep.ok

def test_rejects_stale_series():
    b = bars(10)
    now = b[-1].close_time + 3 * STEP  # newest closed bar is 3 bars old (limit 2)
    with pytest.raises(DataValidationError, match="stale"):
        validate_candles(b, "5m", now)

def test_rejects_inconsistent_ohlc():
    b = bars(5)
    bad = b[2].__class__(**{**b[2].__dict__, "high": 98})  # high below low/open
    b[2] = bad
    with pytest.raises(DataValidationError, match="OHLC"):
        validate_candles(b, "5m", b[-1].close_time + 1)

def test_rejects_duplicates_and_gaps():
    b = bars(5)
    with pytest.raises(DataValidationError, match="duplicate"):
        validate_candles(b + [b[-1]], "5m", b[-1].close_time + 1)
    gappy = b[:2] + b[4:]
    with pytest.raises(DataValidationError, match="missing bars"):
        validate_candles(gappy, "5m", gappy[-1].close_time + 1)

def test_rejects_empty_and_non_positive():
    with pytest.raises(DataValidationError):
        validate_candles([], "5m", 0)
    b = bars(3)
    b[1] = b[1].__class__(**{**b[1].__dict__, "low": 0})
    with pytest.raises(DataValidationError, match="non-positive"):
        validate_candles(b, "5m", b[-1].close_time + 1)
