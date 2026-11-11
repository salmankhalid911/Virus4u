"""Run the daily trend-following test (protocol: docs/DAILY_TREND_RULES.md)."""
import calendar, json, sys, time, pathlib
sys.path.insert(0, pathlib.Path(__file__).resolve().parent.parent.as_posix())
import numpy as np
from dataclasses import replace
from cryptoai.config import SETTINGS, VAR_DIR, CostModel
from cryptoai.backtest.history import rules
from cryptoai.backtest.engine import run_account
from cryptoai.backtest.metrics import summarize
from cryptoai.strategies.daily_trend import simulate

PAIRS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
ms = lambda s: calendar.timegm(time.strptime(s, "%Y-%m-%d")) * 1000
PERIODS = {"train": (ms("2018-02-09"), ms("2022-01-01")), "validation": (ms("2022-01-01"), ms("2024-07-01")), "test": (ms("2024-07-01"), ms("2026-11-11"))}
COSTS = {"low": CostModel(taker_fee=0.0004, maker_fee=0.0004, slippage=0.0002), "base": SETTINGS.costs, "high": CostModel(taker_fee=0.001, maker_fee=0.001, slippage=0.0015)}
R = rules(VAR_DIR, PAIRS)
data = {p: dict(np.load(VAR_DIR / "history" / f"{p}_1d_long.npz")) for p in PAIRS}


def edge(paths):
    r = [p.r for p in paths]
    if not r:
        return dict(trades=0, win_rate=0, pf=0, exp_r=0, avg_win_r=0, avg_loss_r=0, total_r=0)
    w, l = [x for x in r if x > 0], [x for x in r if x <= 0]
    return dict(trades=len(r), win_rate=100 * len(w) / len(r), pf=(sum(w) / abs(sum(l))) if l and sum(l) else float("inf"),
                exp_r=sum(r) / len(r), avg_win_r=sum(w) / len(w) if w else 0, avg_loss_r=sum(l) / len(l) if l else 0, total_r=sum(r))


def buy_hold(p, a, b):
    d = data[p]; m = (d["open_time"] >= a) & (d["open_time"] < b)
    c = d["close"][m]
    if len(c) < 2:
        return None
    eq = c / c[0]
    return dict(ret=float(eq[-1] * (1 - .0015) ** 2 - 1) * 100, dd=float(np.max(1 - eq / np.maximum.accumulate(eq))) * 100)


rows = []
for name in ("T1_donchian", "T2_momentum"):
    for side in (1, -1):
        paths = {cn: [p for sym in PAIRS for p in simulate(name, sym, data[sym], side, cm)] for cn, cm in COSTS.items()}
        row = {"strategy": name, "side": "LONG" if side == 1 else "SHORT"}
        for per, (a, b) in PERIODS.items():
            for cn in COSTS:
                sub = [p for p in paths[cn] if a <= p.entry_time < b]
                row[f"{per}_edge_{cn}"] = edge(sub)
            base = [p for p in paths["base"] if a <= p.entry_time < b]
            for rk, rp in (("acct_0.5", 0.005), ("acct_1.0", 0.01)):
                lim = replace(SETTINGS.risk, default_risk_pct=rp)
                row[f"{per}_{rk}"] = summarize(run_account(base, R, lim, SETTINGS.costs), lim.starting_equity)
            by = {}
            for p in base:
                for k in (p.regime_trend, p.sig.symbol):
                    by[k] = by.get(k, 0) + p.r
            row[f"{per}_r_by"] = by
        tr, va, te = row["train_edge_base"], row["validation_edge_base"], row["test_edge_base"]
        row["qualified"] = bool(tr["exp_r"] > 0 and va["exp_r"] > 0 and tr["trades"] >= 15 and va["trades"] >= 15)
        row["test_negative"] = bool(te["exp_r"] <= 0 or te["trades"] == 0)
        rows.append(row)

bh = {per: {p: buy_hold(p, a, b) for p in PAIRS} for per, (a, b) in PERIODS.items()}
(VAR_DIR / "daily_trend_results.json").write_text(json.dumps({"rows": rows, "buy_hold": bh}, indent=1, default=float))

print("Buy and hold (net % / max drawdown %):")
for per, v in bh.items():
    print(f"  {per:<11}" + "  ".join(f"{p[:3]} {x['ret']:+7.1f}/{x['dd']:4.1f}" if x else f"{p[:3]} n/a" for p, x in v.items()))
print(f"\n{'strategy':<13}{'side':<6}| {'period':<11}{'trades':>6}{'win%':>6}{'PF':>6}{'expR':>7}{'avgW':>6}{'avgL':>6} | {'expR low/high':>14} | $100@0.5%: {'n':>3}{'net%':>7}{'DD%':>6} | $100@1%: {'n':>3}{'net%':>7}{'DD%':>6}")
for r in rows:
    for per in PERIODS:
        e, lo, hi, a5, a1 = r[f"{per}_edge_base"], r[f"{per}_edge_low"], r[f"{per}_edge_high"], r[f"{per}_acct_0.5"], r[f"{per}_acct_1.0"]
        tag = f"{r['strategy']:<13}{r['side']:<6}" if per == "train" else " " * 19
        pf = "inf" if e["pf"] == float("inf") else f"{e['pf']:.2f}"
        print(f"{tag}| {per:<11}{e['trades']:>6}{e['win_rate']:>6.1f}{pf:>6}{e['exp_r']:>+7.2f}{e['avg_win_r']:>6.2f}{e['avg_loss_r']:>6.2f} | {lo['exp_r']:>+6.2f} / {hi['exp_r']:<+6.2f} | {a5['trades']:>13}{a5['net_return_pct']:>+7.2f}{a5['max_drawdown_pct']:>6.2f} | {a1['trades']:>11}{a1['net_return_pct']:>+7.2f}{a1['max_drawdown_pct']:>6.2f}")
    print(" " * 19 + f"| qualified on train+validation: {'YES' if r['qualified'] else 'no'}; test {'NEGATIVE -> rejected' if r['test_negative'] else 'positive'}")
    print(" " * 19 + "| test R by regime/coin: " + ", ".join(f"{k} {v:+.1f}" for k, v in r["test_r_by"].items()))
