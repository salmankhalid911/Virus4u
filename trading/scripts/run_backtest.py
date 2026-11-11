"""Run every strategy, alone and combined, on train / validation / test periods.

Selection rule (fixed in advance): a strategy+timeframe only counts if it is profitable after
fees on BOTH train and validation. Only then is its test-period result meaningful. Test
results are printed for everything so nothing is hidden.
"""
import calendar, json, sys, time, pathlib
sys.path.insert(0, pathlib.Path(__file__).resolve().parent.parent.as_posix())
from cryptoai.config import SETTINGS, VAR_DIR
from cryptoai.backtest.history import HIST_PAIRS, load, rules
from cryptoai.backtest.engine import build_paths, run_account
from cryptoai.backtest.metrics import summarize, gate_report
from cryptoai.strategies import STRATEGIES, Context

ms = lambda d: calendar.timegm(time.strptime(d, "%Y-%m-%d")) * 1000
PERIODS = {"train": (ms("2024-11-01"), ms("2025-09-01")), "validation": (ms("2025-09-01"), ms("2026-03-01")), "test": (ms("2026-03-01"), ms("2026-11-12"))}
R = rules(VAR_DIR, HIST_PAIRS)
L, C = SETTINGS.risk, SETTINGS.costs

paths = {}  # (strategy, tf) -> [Path]
for tf in ("15m", "1h"):
    for sym in HIST_PAIRS:
        x = Context(sym, tf, load(VAR_DIR, sym, tf), load(VAR_DIR, sym, "1h"), load(VAR_DIR, sym, "4h"))
        for name, fn in STRATEGIES.items():
            paths.setdefault((name, tf), []).extend(build_paths(x, fn(x), C))
    print("built", tf, {k[0]: len(v) for k, v in paths.items() if k[1] == tf}, flush=True)

variants = {}
for (name, tf), ps in paths.items():
    variants[(name, tf, "long+short")] = ps
    variants[(name, tf, "long only")] = [p for p in ps if p.sig.side == "LONG"]
for tf in ("15m", "1h"):
    allp = [p for (n, t), ps in paths.items() if t == tf for p in ps]
    variants[("ALL four", tf, "long+short")] = allp
    variants[("ALL four", tf, "long only")] = [p for p in allp if p.sig.side == "LONG"]

report = []
for key, ps in variants.items():
    row = {"strategy": key[0], "tf": key[1], "sides": key[2]}
    for per, (a, b) in PERIODS.items():
        sub = [p for p in ps if a <= p.entry_time < b]
        res = run_account(sub, R, L, C)
        row[per] = summarize(res, L.starting_equity)
    row["qualified"] = row["train"]["expectancy"] > 0 and row["validation"]["expectancy"] > 0 and row["train"]["trades"] >= 30 and row["validation"]["trades"] >= 30
    row["gates"] = gate_report(row["test"])
    report.append(row)

hdr = f"{'strategy':<12}{'tf':<5}{'sides':<11}| {'period':<10}{'trades':>6}{'win%':>6}{'PF':>6}{'exp $':>8}{'exp R':>7}{'net %':>8}{'maxDD%':>7}{'streak':>7}"
print(hdr); print("-" * len(hdr))
for r in sorted(report, key=lambda r: (r["tf"], r["strategy"], r["sides"])):
    for per in PERIODS:
        s = r[per]
        tag = f"{r['strategy']:<12}{r['tf']:<5}{r['sides']:<11}" if per == "train" else " " * 28
        pf = "inf" if s["profit_factor"] == float("inf") else f"{s['profit_factor']:.2f}"
        print(f"{tag}| {per:<10}{s['trades']:>6}{s['win_rate']:>6.1f}{pf:>6}{s['expectancy']:>8.3f}{s['expectancy_r']:>7.2f}{s['net_return_pct']:>8.2f}{s['max_drawdown_pct']:>7.2f}{s['max_consecutive_losses']:>7}")
    print(" " * 28 + f"| qualified on train+validation: {'YES' if r['qualified'] else 'no'}" + ("" if not r["qualified"] else f"   test gates passed: {sum(r['gates'].values())}/5 {r['gates']}"))
out = VAR_DIR / "backtest_report.json"
out.write_text(json.dumps(report, indent=1, default=str))
print("saved", out)
