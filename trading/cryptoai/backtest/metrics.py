"""Performance statistics and the live-trading evaluation gates."""
from __future__ import annotations

from .engine import AccountResult

GATES = dict(min_trades=100, min_profit_factor=1.3, max_drawdown=0.05)


def summarize(res: AccountResult, start_equity: float) -> dict:
    pnl = [f.pnl for f in res.fills]
    r = [f.path.r for f in res.fills]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x <= 0]
    peak, mdd = start_equity, 0.0
    for _, e in res.equity_curve:
        peak = max(peak, e)
        mdd = max(mdd, (peak - e) / peak)
    streak = longest = 0
    for x in pnl:
        streak = streak + 1 if x <= 0 else 0
        longest = max(longest, streak)
    by = {}
    for f in res.fills:
        for key in (f.path.regime_trend, f.path.regime_vol, f.path.sig.side):
            by[key] = by.get(key, 0.0) + f.pnl
    n = len(pnl)
    return dict(
        trades=n,
        win_rate=100 * len(wins) / n if n else 0.0,
        profit_factor=(sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else (float("inf") if wins else 0.0),
        net_return_pct=100 * (res.final_equity - start_equity) / start_equity,
        max_drawdown_pct=100 * mdd,
        avg_win=sum(wins) / len(wins) if wins else 0.0,
        avg_loss=sum(losses) / len(losses) if losses else 0.0,
        expectancy=sum(pnl) / n if n else 0.0,
        expectancy_r=sum(r) / n if n else 0.0,
        max_consecutive_losses=longest,
        final_equity=res.final_equity,
        pnl_by=by,
        skipped=res.skipped,
    )


def gate_report(s: dict) -> dict:
    trend_pnl = {k: v for k, v in s["pnl_by"].items() if k in ("bull", "bear", "sideways")}
    total = sum(trend_pnl.values())
    best = max(trend_pnl.values()) if trend_pnl else 0.0
    not_one_regime = total > 0 and (total - best) > 0
    return {
        "100+ trades": s["trades"] >= GATES["min_trades"],
        "positive expectancy after fees": s["expectancy"] > 0,
        "profit factor > 1.3": s["profit_factor"] > GATES["min_profit_factor"],
        "max drawdown < 5%": s["max_drawdown_pct"] < 100 * GATES["max_drawdown"],
        "profitable without its best market condition": not_one_regime,
    }
