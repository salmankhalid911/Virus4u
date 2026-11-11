"""FastAPI backend for the dashboard. Read-only: no endpoint can place, change or close a trade."""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from .config import SETTINGS, VAR_DIR

app = FastAPI(title="Crypto paper trading", docs_url=None, redoc_url=None)
HERE = Path(__file__).resolve().parent


def _con() -> sqlite3.Connection:
    con = sqlite3.connect(SETTINGS.db_path)
    con.row_factory = sqlite3.Row
    return con


def _since(rows, ms):
    return sum(r["pnl"] for r in rows if r["closed_ms"] and r["closed_ms"] >= ms)


@app.get("/")
def index():
    return FileResponse(HERE / "dashboard.html")


@app.get("/api/state")
def state():
    con = _con()
    try:
        acct = {r["key"]: r["value"] for r in con.execute("SELECT key,value FROM account")}
    except sqlite3.OperationalError:
        return {"ready": False, "message": "No paper account yet. Run the scanner once to create it."}
    eq, start = acct.get("equity", 0.0), acct.get("starting_equity", SETTINGS.risk.starting_equity)
    closed = [dict(r) for r in con.execute(
        "SELECT p.symbol,p.side,p.qty,p.entry,p.stop,p.opened_ms,p.closed_ms,p.outcome,p.realized-p.fees AS pnl,s.strategy "
        "FROM positions p JOIN signals s ON s.id=p.signal_id WHERE p.status!='TRADE ACTIVE' ORDER BY p.closed_ms DESC")]
    active = [dict(r) for r in con.execute(
        "SELECT p.symbol,p.side,p.qty,p.entry,p.stop,p.tps,p.done,p.remaining,p.opened_ms,s.strategy FROM positions p "
        "JOIN signals s ON s.id=p.signal_id WHERE p.status='TRADE ACTIVE'")]
    signals = [dict(r) for r in con.execute("SELECT id,created_ms,symbol,strategy,side,timeframe,status,reason,card FROM signals ORDER BY created_ms DESC LIMIT 60")]
    for s in signals:
        s["card"] = json.loads(s["card"]) if s["card"] else None
    events = [dict(r) for r in con.execute("SELECT ts_ms,kind,detail FROM events ORDER BY ts_ms DESC LIMIT 40")]
    now = datetime.now(timezone.utc)
    day = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    week = int((now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    month = int(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    wins = [t["pnl"] for t in closed if t["pnl"] > 0]
    losses = [t["pnl"] for t in closed if t["pnl"] <= 0]
    curve, e, peak, mdd = [], start, start, 0.0
    for t in reversed(closed):
        e += t["pnl"]
        peak = max(peak, e)
        mdd = max(mdd, (peak - e) / peak)
        curve.append([t["closed_ms"], round(e, 4)])
    committed = sum(a["qty"] * a["remaining"] * a["entry"] for a in active)
    risk = sum(a["qty"] * a["remaining"] * abs(a["entry"] - a["stop"]) for a in active)
    by_strat = {}
    for t in closed:
        b = by_strat.setdefault(t["strategy"], {"trades": 0, "pnl": 0.0, "wins": 0})
        b["trades"] += 1
        b["pnl"] += t["pnl"]
        b["wins"] += t["pnl"] > 0
    report = VAR_DIR / "backtest_report.json"
    watch = VAR_DIR / "watchlist.json"
    return {
        "ready": True,
        "mode": SETTINGS.mode, "live_allowed": SETTINGS.live_trading_allowed(),
        "server_time_ms": int(time.time() * 1000),
        "balance": eq, "starting": start, "available": eq - committed, "total_pnl": eq - start,
        "daily_pnl": _since(closed, day), "weekly_pnl": _since(closed, week), "monthly_pnl": _since(closed, month),
        "trades": len(closed), "win_rate": 100 * len(wins) / len(closed) if closed else None,
        "profit_factor": (sum(wins) / abs(sum(losses))) if losses and sum(losses) else None,
        "max_drawdown_pct": 100 * mdd, "open_risk": risk, "open_risk_pct": 100 * risk / eq if eq else 0,
        "active": active, "history": closed[:100], "signals": signals, "events": events, "equity_curve": curve,
        "strategy_performance": by_strat,
        "limits": {k: getattr(SETTINGS.risk, k) for k in ("default_risk_pct", "max_risk_pct", "max_daily_loss_pct", "max_weekly_drawdown_pct", "max_trades_per_day", "min_reward_risk")},
        "watchlist": json.loads(watch.read_text()) if watch.exists() else [],
        "backtest": json.loads(report.read_text()) if report.exists() else None,
    }
