"""Write docs/PHASE5_REPORT.md from var/phase5_results.json. Every row is included."""
import json, sys, pathlib
sys.path.insert(0, pathlib.Path(__file__).resolve().parent.parent.as_posix())
from cryptoai.config import VAR_DIR

D = json.loads((VAR_DIR / "phase5_results.json").read_text())
rows, base, per = D["rows"], D["baselines"], D["periods"]
NAMES = {"A_trend": "A Trend pullback", "B_breakout": "B Breakout-retest", "C_liquidity": "C Liquidity/CHOCH", "D_range": "D Range"}
pf = lambda v: "inf" if v in ("inf", float("inf")) or (isinstance(v, (int, float)) and v > 1e9) else f"{float(v):.2f}"
out = []
w = out.append

qual = [r for r in rows if r["qualified"]]
pos_test = [r for r in rows if r["test_base"]["trades"] > 0 and r["test_base"]["expectancy"] > 0]
survivors = [r for r in qual if not r["test_negative"]]
passing = [r for r in survivors if all(r["gates"].values())]

w("# Phase 5 strategy comparison")
w("")
w(f"Generated {D['generated']}. Rules and protocol: `docs/STRATEGY_RULES.md`, committed before this run.")
w(f"BTC, ETH, SOL; 5m / 15m / 1h / 4h; each strategy x timeframe x side tested on its own with the $100 account and all risk limits.")
w(f"Train {per['train'][0]} to {per['train'][1]}, validation {per['validation'][0]} to {per['validation'][1]}, test {per['test'][0]} to {per['test'][1]}.")
w("")
w("## Verdict")
w("")
if passing:
    w(f"{len(passing)} combination(s) passed every gate. See the ranking. Paper-trade them before anything else.")
elif survivors:
    w(f"{len(survivors)} combination(s) qualified on train + validation AND stayed positive out of sample, but none passed every live-trading gate.")
else:
    w("**No strategy is profitable after fees in a way that survives the protocol.** "
      f"{len(qual)} of {len(rows)} combinations qualified on train + validation"
      + (f", and {'none' if not survivors else len(survivors)} of those stayed positive in the test period." if qual else ".")
      + f" {len(pos_test)} combinations were positive in the test period alone, but a test-only result after failing train and validation is not evidence of an edge.")
w("")
w("## Baselines (same periods)")
w("")
w("| Period | Buy and hold BTC/ETH/SOL (equal weight) | Max drawdown | BTC | ETH | SOL | No trading |")
w("|---|---|---|---|---|---|---|")
for p, b in base.items():
    bh = b["buy_and_hold"]
    w(f"| {p} | {bh['net_return_pct']:+.1f}% | {bh['max_drawdown_pct']:.1f}% | {bh['per_coin_pct']['BTCUSDT']:+.1f}% | {bh['per_coin_pct']['ETHUSDT']:+.1f}% | {bh['per_coin_pct']['SOLUSDT']:+.1f}% | 0.0% |")
w("")
w("## Ranking by out-of-sample (test) expectancy, base costs")
w("")
w("Expectancy is in R (multiples of the planned risk) after fees, slippage and funding. Net % and drawdown are for the $100 account at 0.5% risk per trade.")
w("")
w("| # | Strategy | TF | Side | Train trades / expR | Valid trades / expR | Test trades | Win % | PF | Exp R | Avg win R / loss R | Net % | Max DD % | Qualified | Status |")
w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for i, r in enumerate(rows, 1):
    tr, va, te = r["train_base"], r["validation_base"], r["test_base"]
    status = "PASS all gates" if all(r["gates"].values()) else ("rejected: negative OOS" if r["test_negative"] else ("positive OOS, failed train/valid" if not r["qualified"] else "positive OOS, fails gates"))
    w(f"| {i} | {NAMES[r['strategy']]} | {r['tf']} | {r['side']} | {tr['trades']} / {tr['expectancy_r']:+.2f} | {va['trades']} / {va['expectancy_r']:+.2f} | {te['trades']} | {te['win_rate']:.1f} | {pf(te['profit_factor'])} | {te['expectancy_r']:+.2f} | {te['avg_win_r']:+.2f} / {te['avg_loss_r']:+.2f} | {te['net_return_pct']:+.2f} | {te['max_drawdown_pct']:.2f} | {'yes' if r['qualified'] else 'no'} | {status} |")
w("")
w("## Long versus short (test period, base costs, all strategies and timeframes)")
w("")
for side in ("LONG", "SHORT"):
    s = [r["test_base"] for r in rows if r["side"] == side]
    n = sum(x["trades"] for x in s)
    er = sum(x["expectancy_r"] * x["trades"] for x in s) / n if n else 0
    w(f"- {side}: {n} trades, average {er:+.3f}R per trade, {sum(x['net_return_pct'] for x in s):+.1f}% summed across combinations")
w("")
w("## By strategy (test period, base costs, all timeframes and both sides)")
w("")
for k, v in NAMES.items():
    s = [r["test_base"] for r in rows if r["strategy"] == k]
    n = sum(x["trades"] for x in s)
    er = sum(x["expectancy_r"] * x["trades"] for x in s) / n if n else 0
    w(f"- {v}: {n} trades, {er:+.3f}R per trade")
w("")
w("## By timeframe (test period, base costs)")
w("")
for tf in ("5m", "15m", "1h", "4h"):
    s = [r["test_base"] for r in rows if r["tf"] == tf]
    n = sum(x["trades"] for x in s)
    er = sum(x["expectancy_r"] * x["trades"] for x in s) / n if n else 0
    w(f"- {tf}: {n} trades, {er:+.3f}R per trade")
w("")
w("## Market regime (test period P/L in $, base costs) for the top 8")
w("")
w("Regime = 4h (or daily) direction at entry; volatility = ATR percentile at entry.")
w("")
w("| Strategy | TF | Side | Bull | Bear | Sideways | High vol | Low vol |")
w("|---|---|---|---|---|---|---|---|")
for r in rows[:8]:
    b = r["test_base"]["pnl_by"]
    g = lambda k: f"{b.get(k, 0):+.2f}"
    w(f"| {NAMES[r['strategy']]} | {r['tf']} | {r['side']} | {g('bull')} | {g('bear')} | {g('sideways')} | {g('high_vol')} | {g('low_vol')} |")
w("")
w("## Sensitivity to fees and slippage (test expectancy, R)")
w("")
w("Low = 0.04% fee + 0.02% slippage per side. Base = 0.10% + 0.05%. High = 0.10% + 0.15%.")
w("")
w("| Strategy | TF | Side | Low | Base | High |")
w("|---|---|---|---|---|---|")
for r in rows[:12]:
    w(f"| {NAMES[r['strategy']]} | {r['tf']} | {r['side']} | {r['test_low']['expectancy_r']:+.2f} | {r['test_base']['expectancy_r']:+.2f} | {r['test_high']['expectancy_r']:+.2f} |")
w("")
w("## Live-trading gates")
w("")
w("100+ trades, positive expectancy after fees, profit factor > 1.3, max drawdown < 5%, profitable without its best market regime.")
w(f"Combinations passing all five: {len(passing)}. Nothing proceeds to live trading.")
(pathlib.Path(__file__).resolve().parent.parent / "docs" / "PHASE5_REPORT.md").write_text("\n".join(out) + "\n")
print("\n".join(out[:12]))
