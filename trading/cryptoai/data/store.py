"""SQLite storage for validated candles."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Candle

SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
  symbol TEXT NOT NULL, timeframe TEXT NOT NULL, open_time INTEGER NOT NULL,
  close_time INTEGER NOT NULL, open REAL, high REAL, low REAL, close REAL, volume REAL,
  source TEXT NOT NULL, PRIMARY KEY (symbol, timeframe, open_time)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def upsert_candles(con: sqlite3.Connection, candles: list[Candle]) -> int:
    con.executemany(
        "INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(c.symbol, c.timeframe, c.open_time, c.close_time, c.open, c.high, c.low, c.close, c.volume, c.source) for c in candles],
    )
    con.commit()
    return len(candles)


def load_candles(con: sqlite3.Connection, symbol: str, timeframe: str, limit: int | None = None) -> list[Candle]:
    q = "SELECT symbol,timeframe,open_time,close_time,open,high,low,close,volume,source FROM candles WHERE symbol=? AND timeframe=? ORDER BY open_time"
    rows = con.execute(q, (symbol, timeframe)).fetchall()
    if limit:
        rows = rows[-limit:]
    return [Candle(*r) for r in rows]
