"""Download and cache validated historical candles plus exchange order rules."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from ..config import TIMEFRAME_SECONDS
from ..data.models import SymbolRules
from ..data.sources import BinancePublicSource
from ..data.validation import validate_candles

HIST_PAIRS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT")


def cache_path(var: Path, symbol: str, tf: str) -> Path:
    return var / "history" / f"{symbol}_{tf}.npz"


def download(var: Path, symbol: str, tf: str, days: int, src: BinancePublicSource | None = None) -> dict:
    src = src or BinancePublicSource()
    bars = int(days * 86400 / TIMEFRAME_SECONDS[tf])
    raw = src.fetch_history(symbol, tf, bars)
    now = src.server_time_ms()
    # Historical series: freshness not required, but every other check still applies.
    clean, rep = validate_candles(raw, tf, now, require_fresh=False, max_gap_fraction=0.002)
    arr = {k: np.array([getattr(c, k) for c in clean]) for k in ("open_time", "close_time", "open", "high", "low", "close", "volume")}
    p = cache_path(var, symbol, tf)
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, **arr)
    return dict(symbol=symbol, tf=tf, bars=len(clean), gaps=len(rep.gaps), dropped_unclosed=rep.dropped_unclosed)


def load(var: Path, symbol: str, tf: str) -> dict[str, np.ndarray]:
    with np.load(cache_path(var, symbol, tf)) as z:
        return {k: z[k] for k in z.files}


def rules(var: Path, symbols, src: BinancePublicSource | None = None) -> dict[str, SymbolRules]:
    p = var / "history" / "rules.json"
    if p.exists():
        return {k: SymbolRules(**v) for k, v in json.loads(p.read_text()).items()}
    src = src or BinancePublicSource()
    r = {s: src.symbol_rules(s) for s in symbols}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({k: asdict(v) for k, v in r.items()}, indent=1))
    return r
