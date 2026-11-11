"""Phase 5: every strategy x timeframe x side on its own, BTC/ETH/SOL, train/validation/test.
Protocol: docs/STRATEGY_RULES.md (committed before this script was first run)."""
import calendar, json, sys, time, pathlib
from dataclasses import replace
sys.path.insert(0, pathlib.Path(__file__).resolve().parent.parent.as_posix())
import numpy as np
from cryptoai.config import SETTINGS, VAR_DIR, CostModel
from cryptoai.backtest.history import load, rules
from cryptoai.backtest.engine import build_paths, run_account
from cryptoai.backtest.metrics import summarize, gate_report
from cryptoai.strategies import MTF, STRATEGIES, Context

PAIRS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
TFS = tuple(sys.argv[1].split(",")) if len(sys.argv) > 1 else ("5m", "15m", "1h", "4h")
ms = lambda d: calendar.timegm(time.strptime(d, "%Y-%m-%d")) * 1000
PERIODS = {"train": (ms("2024-11-01"), ms("2025-09-01")), "validation": (ms("2025-09-01"), ms("2026-03-01")), "test": (ms("2026-03-01"), ms("2026-11-12"))}
COSTS = {"low": CostModel(taker_fee=0.0004, maker_fee=0.0004, slippage=0.0002), "base": SETTINGS.costs, "high": CostModel(taker_fee=0.001, maker_fee=0.001, slippage=0.0015)}
R = rules(VAR_DIR, PAIRS)
L = SETTINGS.risk
t0 = time.time()

# ---- baselines: equal-weight buy and hold of BTC/ETH/SOL (4h closes), and no trading ----
def buy_hold(a, b):
    curves = []
    for p in PAIRS:
        d = load(VAR_DIR, p, "4h"); m = (d["open_time"] >= a) & (d["open_time"] < b)
        c = d["close"][m]; curves.append(c / c[0])
    eq = np.mean(curves, axis=0) * (1 - 0.0015) * (1 - 0.0015)
    dd = float(np.max(1 - eq / np.maximum.accumulate(eq)))
    per = {p: float(cv[-1] - 1) * 100 for p, cv in zip(PAIRS, curves)}
    return {"net_return_pct": float(eq[-1] - 1) * 100, "max_drawdown_pct": dd * 100, "per_coin_pct": per}
baselines = {per: {"buy_and_hold": buy_hold(a, b), "no_trade": {"net_return_pct": 0.0, "max_drawdown_pct": 0.0}} for per, (a, b) in PERIODS.items()}

# ---- signals and trade paths ----
paths = {}  # (strategy, tf, side, cost) -> [Path]
counts = {}
for tf in TFS:
    trend_tf, struct_tf = MTF[tf]
    for sym in PAIRS:
        x = Context(sym, tf, load(VAR_DIR, sym, tf), load(VAR_DIR, sym, struct_tf), load(VAR_DIR, sym, trend_tf))
        for name, fn in STRATEGIES.items():
            sigs = fn(x)
            for cname, cm in COSTS.items():
                for p in build_paths(x, sigs, cm):
                    paths.setdefault((name, tf, p.sig.side, cname), []).append(p)
            counts[(name, tf, sym)] = len(sigs)
    print(f"{tf}: signals built ({time.time() - t0:.0f}s)", flush=True)

rows = []
for name in STRATEGIES:
    for tf in TFS:
        for side in ("LONG", "SHORT"):
            row = {"strategy": name, "tf": tf, "side": side}
            for per, (a, b) in PERIODS.items():
                for cname in COSTS:
                    sub = [p for p in paths.get((name, tf, side, cname), []) if a <= p.entry_time < b]
                    row[f"{per}_{cname}"] = summarize(run_account(sub, R, L, COSTS[cname]), L.starting_equity)
            tr, va, te = row["train_base"], row["validation_base"], row["test_base"]
            row["qualified"] = tr["expectancy"] > 0 and va["expectancy"] > 0 and tr["trades"] >= 30 and va["trades"] >= 30
            row["test_negative"] = te["expectancy"] <= 0 or te["trades"] == 0
            row["gates"] = gate_report(te)
            rows.append(row)
rows.sort(key=lambda r: (r["test_base"]["expectancy_r"] if r["test_base"]["trades"] else -9), reverse=True)
out = {"generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "periods": {k: [time.strftime("%Y-%m-%d", time.gmtime(a / 1000)), time.strftime("%Y-%m-%d", time.gmtime(b / 1000 - 1))] for k, (a, b) in PERIODS.items()},
       "baselines": baselines, "rows": rows, "signal_counts": {"|".join(k): v for k, v in counts.items()}}
(VAR_DIR / "phase5_results.json").write_text(json.dumps(out, indent=1, default=str))

f = lambda v: "inf" if v == float("inf") else f"{v:.2f}"
print(f"\nBaselines (net % / max DD %): " + "  ".join(f"{p}: B&H {b['buy_and_hold']['net_return_pct']:+.1f}/{b['buy_and_hold']['max_drawdown_pct']:.1f}" for p, b in baselines.items()))
print(f"\n{'rank':<5}{'strategy':<12}{'tf':<5}{'side':<6}| {'TRAIN n':>7}{'expR':>7} | {'VALID n':>7}{'expR':>7} | {'TEST n':>6}{'win%':>6}{'PF':>6}{'expR':>7}{'net%':>8}{'DD%':>6} | {'test expR low/high cost':>22} | qual  gates")
for i, r in enumerate(rows, 1):
    tr, va, te, lo, hi = r["train_base"], r["validation_base"], r["test_base"], r["test_low"], r["test_high"]
    print(f"{i:<5}{r['strategy']:<12}{r['tf']:<5}{r['side']:<6}| {tr['trades']:>7}{tr['expectancy_r']:>7.2f} | {va['trades']:>7}{va['expectancy_r']:>7.2f} | {te['trades']:>6}{te['win_rate']:>6.1f}{f(te['profit_factor']):>6}{te['expectancy_r']:>7.2f}{te['net_return_pct']:>8.2f}{te['max_drawdown_pct']:>6.2f} | {lo['expectancy_r']:>10.2f} / {hi['expectancy_r']:<9.2f} | {'YES' if r['qualified'] else 'no ':<5} {sum(r['gates'].values())}/5")
print(f"\ndone in {time.time() - t0:.0f}s; saved {VAR_DIR / 'phase5_results.json'}")
