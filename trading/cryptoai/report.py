"""Daily performance report from the paper account (markdown)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .execution.paper import PaperBroker


def daily_report(broker: PaperBroker, now_ms: int) -> str:
    con = broker.con
    day = datetime.fromtimestamp(now_ms / 1000, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = int(day.timestamp() * 1000)
    rows = con.execute("SELECT p.symbol,p.side,s.strategy,p.entry,p.outcome,p.realized-p.fees FROM positions p JOIN signals s ON s.id=p.signal_id "
                       "WHERE p.closed_ms>=? ORDER BY p.closed_ms", (start,)).fetchall()
    sigs = con.execute("SELECT status,COUNT(*) FROM signals WHERE created_ms>=? GROUP BY status", (start,)).fetchall()
    rej = con.execute("SELECT symbol,side,strategy,reason FROM signals WHERE created_ms>=? AND status='SIGNAL INVALIDATED'", (start,)).fetchall()
    all_closed = [r[0] for r in con.execute("SELECT realized-fees FROM positions WHERE status!='TRADE ACTIVE'")]
    wins = [x for x in all_closed if x > 0]
    losses = [x for x in all_closed if x <= 0]
    pf = sum(wins) / abs(sum(losses)) if losses and sum(losses) else None
    start_eq = con.execute("SELECT value FROM account WHERE key='starting_equity'").fetchone()[0]
    lines = [f"# Paper trading report, {day:%Y-%m-%d} (UTC)", "",
             f"Balance: ${broker.equity:.2f} (started ${start_eq:.2f}, {broker.equity - start_eq:+.2f})",
             f"Today: {len(rows)} closed trade(s), P/L {sum(r[5] for r in rows):+.4f}",
             f"All time: {len(all_closed)} trades, win rate {100 * len(wins) / len(all_closed):.1f}%" if all_closed else "All time: no closed trades yet",
             f"Profit factor: {pf:.2f}" if pf else "Profit factor: n/a", "", "## Closed today"]
    lines += [f"- {r[0]} {r[1]} ({r[2]}) entry {r[3]:g}: {r[4]}, {r[5]:+.4f}" for r in rows] or ["- none"]
    lines += ["", "## Signals today"] + ([f"- {s}: {n}" for s, n in sigs] or ["- none"])
    if rej:
        lines += ["", "## Rejected setups (and why)"] + [f"- {r[0]} {r[1]} {r[2]}: {r[3]}" for r in rej]
    open_ = broker.open_positions()
    lines += ["", f"## Open positions: {len(open_)}"]
    return "\n".join(lines)
