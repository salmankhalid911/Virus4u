"""Paper broker: simulated fills, fees and slippage, stop and take-profit management.

Never sends an order anywhere. State lives in SQLite so a restart picks up where it left off.
A signal id is unique (symbol|strategy|timeframe|bar close|side), so one signal can never
open two trades, even if the scanner runs twice on the same candle.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass

from ..config import CostModel
from ..signals import TradeCard

TP_FRACTION = (0.5, 0.3, 0.2)
SHORT_FUNDING_PER_8H = 0.0001
SCHEMA = """
CREATE TABLE IF NOT EXISTS account (key TEXT PRIMARY KEY, value REAL);
CREATE TABLE IF NOT EXISTS signals (
  id TEXT PRIMARY KEY, created_ms INTEGER, symbol TEXT, strategy TEXT, side TEXT, timeframe TEXT,
  status TEXT, reason TEXT, card TEXT);
CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, signal_id TEXT UNIQUE, symbol TEXT, side TEXT, qty REAL,
  entry REAL, fill_in REAL, stop REAL, tps TEXT, done TEXT, remaining REAL, be_pending INTEGER,
  opened_ms INTEGER, last_bar_ms INTEGER, status TEXT, realized REAL DEFAULT 0, fees REAL DEFAULT 0,
  closed_ms INTEGER, outcome TEXT);
CREATE TABLE IF NOT EXISTS events (ts_ms INTEGER, kind TEXT, detail TEXT);
"""


@dataclass
class Bar:
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float


class PaperBroker:
    def __init__(self, con: sqlite3.Connection, costs: CostModel, starting_equity: float = 100.0):
        self.con, self.costs = con, costs
        con.executescript(SCHEMA)
        if self._get("equity") is None:
            self._set("equity", starting_equity)
            self._set("starting_equity", starting_equity)
            self.log("init", f"paper account opened with ${starting_equity:.2f}")

    # --- account -------------------------------------------------------------
    def _get(self, k):
        r = self.con.execute("SELECT value FROM account WHERE key=?", (k,)).fetchone()
        return r[0] if r else None

    def _set(self, k, v):
        self.con.execute("INSERT OR REPLACE INTO account VALUES (?,?)", (k, v))
        self.con.commit()

    @property
    def equity(self) -> float:
        return self._get("equity")

    def log(self, kind: str, detail: str, ts_ms: int | None = None):
        self.con.execute("INSERT INTO events VALUES (?,?,?)", (ts_ms or int(time.time() * 1000), kind, detail))
        self.con.commit()

    def open_positions(self):
        return self.con.execute("SELECT * FROM positions WHERE status='TRADE ACTIVE'").fetchall()

    def committed_cash(self) -> float:
        return sum(r[0] * r[1] for r in self.con.execute("SELECT qty*remaining, entry FROM positions WHERE status='TRADE ACTIVE'"))

    # --- signals -------------------------------------------------------------
    def record_signal(self, sig_id: str, created_ms: int, symbol: str, strategy: str, side: str, tf: str,
                      status: str, reason: str = "", card: TradeCard | None = None) -> bool:
        """Insert a signal once. Returns False if this exact signal was already recorded."""
        cur = self.con.execute(
            "INSERT OR IGNORE INTO signals VALUES (?,?,?,?,?,?,?,?,?)",
            (sig_id, created_ms, symbol, strategy, side, tf, status, reason, json.dumps(card.__dict__) if card else None))
        self.con.commit()
        return cur.rowcount == 1

    def set_signal_status(self, sig_id: str, status: str, reason: str = ""):
        self.con.execute("UPDATE signals SET status=?, reason=COALESCE(NULLIF(?,''),reason) WHERE id=?", (status, reason, sig_id))
        self.con.commit()

    # --- orders --------------------------------------------------------------
    def open_from_card(self, sig_id: str, card: TradeCard, fill_bar: Bar) -> bool:
        """Simulated market entry at the open of the bar after the signal."""
        if self.con.execute("SELECT 1 FROM positions WHERE signal_id=?", (sig_id,)).fetchone():
            return False
        if self.con.execute("SELECT 1 FROM positions WHERE symbol=? AND status='TRADE ACTIVE'", (card.pair,)).fetchone():
            self.set_signal_status(sig_id, "SIGNAL INVALIDATED", "already in a position on this pair")
            return False
        side = 1 if card.direction == "LONG" else -1
        entry = fill_bar.open
        if (entry - card.stop) * side <= 0:
            self.set_signal_status(sig_id, "SIGNAL INVALIDATED", "opened beyond the stop")
            return False
        fill_in = entry * (1 + side * self.costs.slippage)
        fee = fill_in * card.qty * self.costs.taker_fee
        self.con.execute(
            "INSERT INTO positions (signal_id,symbol,side,qty,entry,fill_in,stop,tps,done,remaining,be_pending,opened_ms,last_bar_ms,status,fees) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (sig_id, card.pair, card.direction, card.qty, entry, fill_in, card.stop, json.dumps([card.tp1, card.tp2, card.tp3]),
             json.dumps([False] * 3), 1.0, 0, fill_bar.open_time, fill_bar.open_time - 1, "TRADE ACTIVE", fee))
        self._set("equity", self.equity - fee)
        self.set_signal_status(sig_id, "TRADE ACTIVE")
        self.log("entry", f"{card.direction} {card.qty:g} {card.pair} @ {entry:g} stop {card.stop:g}", fill_bar.open_time)
        self.con.commit()
        return True

    def on_bar(self, symbol: str, bar: Bar, max_hold_ms: int):
        """Feed one CLOSED candle. Same rules as the backtest: stop first, gap fills at open,
        breakeven after TP1 applies from the next bar, TPs are limit fills."""
        for row in self.con.execute("SELECT id,side,qty,entry,fill_in,stop,tps,done,remaining,be_pending,opened_ms,last_bar_ms,signal_id "
                                    "FROM positions WHERE symbol=? AND status='TRADE ACTIVE'", (symbol,)).fetchall():
            pid, side_s, qty, entry, fill_in, stop, tps, done, rem, be, opened, last_ms, sig_id = row
            if bar.open_time <= last_ms or bar.open_time < opened:
                continue  # already processed (restart safety) or from before the entry
            side = 1 if side_s == "LONG" else -1
            tps, done = json.loads(tps), json.loads(done)
            if be:
                stop, be = entry, 0
            realized = fees = 0.0
            status, outcome = "TRADE ACTIVE", None
            if (bar.low <= stop) if side == 1 else (bar.high >= stop):
                px = stop if bar.open_time == opened else (min(stop, bar.open) if side == 1 else max(stop, bar.open))
                px *= (1 - side * self.costs.slippage)
                realized += rem * qty * side * (px - fill_in)
                fees += rem * qty * px * self.costs.taker_fee
                rem = 0.0
                status = "STOP LOSS HIT" if not done[0] else "TAKE PROFIT HIT"
                outcome = "stop" if not done[0] else ("breakeven" if not done[1] else "tp2+stop")
            else:
                for k in range(3):
                    if not done[k] and ((bar.high >= tps[k]) if side == 1 else (bar.low <= tps[k])):
                        done[k] = True
                        realized += TP_FRACTION[k] * qty * side * (tps[k] - fill_in)
                        fees += TP_FRACTION[k] * qty * tps[k] * self.costs.taker_fee
                        rem -= TP_FRACTION[k]
                        if k == 0:
                            be = 1
                        self.log("take_profit", f"{symbol} TP{k + 1} @ {tps[k]:g}", bar.close_time)
                if rem <= 1e-9:
                    rem, status, outcome = 0.0, "TAKE PROFIT HIT", "tp3"
                elif bar.close_time - opened >= max_hold_ms:
                    px = bar.close * (1 - side * self.costs.slippage)
                    realized += rem * qty * side * (px - fill_in)
                    fees += rem * qty * px * self.costs.taker_fee
                    rem, status = 0.0, ("TAKE PROFIT HIT" if done[0] else "SIGNAL INVALIDATED")
                    outcome = "tp1+time" if done[0] else "time"
            if status != "TRADE ACTIVE" and side == -1:  # shorts are 1x futures: pay funding
                fees += fill_in * qty * SHORT_FUNDING_PER_8H * (bar.close_time - opened) / 3_600_000 / 8
            self.con.execute(
                "UPDATE positions SET stop=?, done=?, remaining=?, be_pending=?, last_bar_ms=?, status=?, realized=realized+?, fees=fees+?, "
                "closed_ms=?, outcome=? WHERE id=?",
                (stop, json.dumps(done), rem, be, bar.open_time, status, realized, fees,
                 bar.close_time if status != "TRADE ACTIVE" else None, outcome, pid))
            self._set("equity", self.equity + realized - fees)
            if status != "TRADE ACTIVE":
                self.set_signal_status(sig_id, status)
                self.log("exit", f"{symbol} {outcome} pnl {realized - fees:+.4f}", bar.close_time)
        self.con.commit()

    def closed_trades(self):
        q = "SELECT p.symbol,p.side,p.qty,p.entry,p.opened_ms,p.closed_ms,p.outcome,p.realized-p.fees,s.strategy FROM positions p JOIN signals s ON s.id=p.signal_id WHERE p.status!='TRADE ACTIVE' ORDER BY p.closed_ms"
        return self.con.execute(q).fetchall()
