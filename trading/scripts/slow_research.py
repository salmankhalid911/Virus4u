"""Slower-timeframe research run. Protocol: docs/SLOW_RESEARCH_RULES.md (committed first)."""
import calendar, json, sys, time, pathlib
sys.path.insert(0, pathlib.Path(__file__).resolve().parent.parent.as_posix())
import numpy as np
from cryptoai import indicators as ta
from cryptoai.config import SETTINGS, VAR_DIR, CostModel
from cryptoai.backtest.history import rules
from cryptoai.backtest.engine import run_account
from cryptoai.backtest.metrics import summarize
from cryptoai.research.slow import Scenario, btc_regime, single_coin_paths, strat_A, strat_B, strat_C, strat_D

ms = lambda s: calendar.timegm(time.strptime(s, "%Y-%m-%d")) * 1000
PERIODS = {"train": (ms("2024-01-01"), ms("2025-01-01")), "validation": (ms("2025-01-01"), ms("2026-01-01")), "test": (ms("2026-01-01"), ms("2026-11-11"))}
MONTHS = {"train": 12.0, "validation": 12.0, "test": 10.33}
BASE = SETTINGS.costs
SCEN = [Scenario("base", BASE), Scenario("low fees", CostModel(taker_fee=0.00075, maker_fee=0.00075, slippage=0.0002)),
        Scenario("high costs", CostModel(taker_fee=0.001, maker_fee=0.001, slippage=0.0015)),
        Scenario("entry delay +1", BASE, delay=1), Scenario("stops 0.5% worse", BASE, stop_extra=0.005)]
PAIRS = ("BTCUSDT", "ETHUSDT")
R = rules(VAR_DIR, PAIRS)
L = SETTINGS.risk
load = lambda p, tf: dict(np.load(VAR_DIR / "history" / f"{p}_{tf}_long.npz"))
D1 = {p: load(p, "1d") for p in PAIRS}
H4 = {p: load(p, "4h") for p in PAIRS}
WK = {p: ta.weekly_from_daily(D1[p]) for p in PAIRS}
REG = {(p, tf): btc_regime(D1["BTCUSDT"], (D1 if tf == "1d" else H4)[p]["close_time"]) for p in PAIRS for tf in ("1d", "4h")}


def build(variant, sc):
    if variant == "D_rotation_1d":
        return strat_D(D1["BTCUSDT"], D1["ETHUSDT"], sc, {p: REG[(p, "1d")] for p in PAIRS})
    strat, tf = variant.rsplit("_", 1)
    out = []
    for p in PAIRS:
        d = D1[p] if tf == "1d" else H4[p]
        if strat == "A_trend":
            sigs, ex = strat_A(d)
        elif strat == "B_pullback":
            sigs, ex = strat_B(d, WK[p] if tf == "1d" else D1[p])
        else:
            sigs, ex = strat_C(d)
        out += single_coin_paths(strat, p, d, sigs, ex, sc, REG[(p, tf)])
    return out


def edge(ps):
    r = np.array([p.r for p in ps])
    if not len(r):
        return dict(trades=0, exp_r=0.0, win_rate=0.0, pf=0.0, avg_win_r=0.0, avg_loss_r=0.0, hold_days=0.0)
    w, lo = r[r > 0], r[r <= 0]
    return dict(trades=int(len(r)), exp_r=float(r.mean()), win_rate=float(100 * len(w) / len(r)),
                pf=float(w.sum() / abs(lo.sum())) if lo.sum() else float("inf"), avg_win_r=float(w.mean()) if len(w) else 0.0,
                avg_loss_r=float(lo.mean()) if len(lo) else 0.0,
                hold_days=float(np.mean([(p.exit_time - p.entry_time) / 86_400_000 for p in ps])))


def boot_p(ps, n=20000):
    r = np.array([p.r for p in ps])
    if len(r) < 3:
        return None
    rng = np.random.default_rng(0)
    return float(np.mean(rng.choice(r, (n, len(r))).mean(axis=1) <= 0))


def buy_hold(p, a, b):
    d = D1[p]; m = (d["open_time"] >= a) & (d["open_time"] < b)
    c = d["close"][m]; eq = c / c[0]
    return dict(net_pct=float(eq[-1] * (1 - .0015) ** 2 - 1) * 100, max_dd_pct=float(np.max(1 - eq / np.maximum.accumulate(eq))) * 100)


VARIANTS = ["A_trend_1d", "A_trend_4h", "B_pullback_1d", "B_pullback_4h", "C_breakout_1d", "C_breakout_4h", "D_rotation_1d"]
results = []
for v in VARIANTS:
    allp = {sc.name: build(v, sc) for sc in SCEN}
    row = {"variant": v, "periods": {}}
    for per, (a, b) in PERIODS.items():
        pr = {}
        for sc in SCEN:
            ps = [p for p in allp[sc.name] if a <= p.entry_time < b]
            pr[sc.name] = edge(ps)
        base = [p for p in allp["base"] if a <= p.entry_time < b]
        acct = summarize(run_account(base, R, L, BASE, max_positions=1), L.starting_equity)
        reg = {}
        for p in base:
            reg.setdefault(p.regime_trend, []).append(p.r)
        pr["account"] = {k: acct[k] for k in ("trades", "win_rate", "profit_factor", "net_return_pct", "max_drawdown_pct", "expectancy", "max_consecutive_losses", "skipped")}
        pr["trades_per_month"] = pr["base"]["trades"] / MONTHS[per]
        pr["regime_r"] = {k: dict(trades=len(x), exp_r=float(np.mean(x))) for k, x in reg.items()}
        pr["boot_p_le_0"] = boot_p(base)
        row["periods"][per] = pr
    P = row["periods"]
    tr, va, te = P["train"]["base"], P["validation"]["base"], P["test"]["base"]
    fail = []
    if tr["trades"] >= 5 and tr["exp_r"] <= 0: fail.append("train expectancy <= 0")
    if va["trades"] >= 5 and va["exp_r"] <= 0: fail.append("validation expectancy <= 0")
    if te["trades"] >= 5 and te["exp_r"] <= 0: fail.append("test expectancy <= 0")
    if P["test"]["account"]["max_drawdown_pct"] >= 5: fail.append("test drawdown >= 5%")
    for sc in SCEN[1:]:
        if te["trades"] >= 5 and P["test"][sc.name]["exp_r"] <= 0:
            fail.append(f"test expectancy <= 0 with {sc.name}")
    small = [k for k in ("train", "validation", "test") if P[k]["base"]["trades"] < 10]
    row["verdict"] = "FAIL" if fail else ("INSUFFICIENT EVIDENCE" if small else "PASS")
    row["reasons"] = fail if fail else ([f"fewer than 10 trades in {', '.join(small)}"] if small else [])
    results.append(row)
    print(f"{v}: {row['verdict']} {row['reasons']}", flush=True)

bh = {per: {p: buy_hold(p, a, b) for p in PAIRS} for per, (a, b) in PERIODS.items()}
(VAR_DIR / "slow_research.json").write_text(json.dumps({"results": results, "buy_hold": bh}, indent=1, default=float))
print("\nBuy and hold (net % / max DD %): " + "  ".join(f"{per}: BTC {v['BTCUSDT']['net_pct']:+.1f}/{v['BTCUSDT']['max_dd_pct']:.1f} ETH {v['ETHUSDT']['net_pct']:+.1f}/{v['ETHUSDT']['max_dd_pct']:.1f}" for per, v in bh.items()))
print(f"\n{'variant':<15}{'period':<11}{'n':>4}{'expR':>7}{'win%':>6}{'PF':>6}{'hold d':>7}{'/mo':>5} | $100: {'net%':>6}{'DD%':>6}{'n':>4} | test expR: low / high / delay / badstop | P(<=0)")
for r in results:
    for per in PERIODS:
        P = r["periods"][per]; b = P["base"]; a = P["account"]
        pf = "inf" if b["pf"] == float("inf") else f"{b['pf']:.2f}"
        extra = ""
        if per == "test":
            extra = " | " + " / ".join(f"{P[s]['exp_r']:+.2f}" for s in ("low fees", "high costs", "entry delay +1", "stops 0.5% worse")) + f" | {P['boot_p_le_0'] if P['boot_p_le_0'] is None else round(P['boot_p_le_0'], 2)}"
        print(f"{r['variant'] if per == 'train' else '':<15}{per:<11}{b['trades']:>4}{b['exp_r']:>+7.2f}{b['win_rate']:>6.1f}{pf:>6}{b['hold_days']:>7.1f}{P['trades_per_month']:>5.1f} | {a['net_return_pct']:>+10.2f}{a['max_drawdown_pct']:>6.2f}{a['trades']:>4}{extra}")
    print(f"{'':<15}VERDICT: {r['verdict']}  {'; '.join(r['reasons'])}")
