"""One scan cycle, plus a loop that runs it after every closed candle.

Order of work per pair:
1. fetch and validate 15m / 1h / 4h candles (rejects stale or broken data: no scan that cycle)
2. feed newly closed 15m candles to open paper positions (stops and take profits)
3. refresh the watchlist entry (market direction, RSI, volatility)
4. run the enabled strategies on the LAST CLOSED candle only
5. for each new signal: price it, risk-check it, size it -> trade card, or record why not
6. paper-fill accepted cards at the current price (a market order now, not the earlier open)
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import numpy as np

from . import analyst
from .config import SETTINGS, TIMEFRAME_SECONDS, VAR_DIR, Settings
from .data.models import Candle
from .data.service import MarketDataService
from .data.sources import BinancePublicSource
from .execution.paper import Bar, PaperBroker
from .risk.limits import AccountState
from .signals import NO_TRADE, build_card
from .strategies import STRATEGIES, Context

log = logging.getLogger("scanner")
SIGNAL_TF = "15m"
MAX_HOLD_MS = 96 * 15 * 60 * 1000  # 1 day on 15m, same as the backtest


def _arrays(cs: list[Candle]) -> dict:
    return {k: np.array([getattr(c, k) for c in cs]) for k in ("open_time", "close_time", "open", "high", "low", "close", "volume")}


def _confidence_records() -> dict:
    p = VAR_DIR / "backtest_report.json"
    if not p.exists():
        return {}
    out = {}
    for r in json.loads(p.read_text()):
        if r["sides"] == "long+short" and r["qualified"] and all(r["gates"].values()):
            out[(r["strategy"], r["tf"])] = r["test"]
    return out


def account_state(broker: PaperBroker, now_ms: int) -> AccountState:
    con = broker.con
    now = datetime.fromtimestamp(now_ms / 1000, timezone.utc)
    day = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    week = int((now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    eq = broker.equity
    today = con.execute("SELECT COALESCE(SUM(realized-fees),0) FROM positions WHERE closed_ms>=?", (day,)).fetchone()[0]
    opened_today = con.execute("SELECT COUNT(*) FROM positions WHERE opened_ms>=?", (day,)).fetchone()[0]
    week_pnls = [r[0] for r in con.execute("SELECT realized-fees FROM positions WHERE closed_ms>=? ORDER BY closed_ms", (week,))]
    e = eq - sum(week_pnls)
    peak = e
    for p in week_pnls:
        e += p
        peak = max(peak, e)
    n_open = len(broker.open_positions())
    return AccountState(eq, eq - today, peak, opened_today, n_open)


def scan_once(svc: MarketDataService, broker: PaperBroker, settings: Settings = SETTINGS, enabled=tuple(STRATEGIES)) -> dict:
    src = BinancePublicSource()
    rules = {p: src.symbol_rules(p) for p in settings.pairs}
    conf = _confidence_records()
    summary = {"time": svc.now_ms(), "pairs": {}, "cards": [], "rejected": []}
    watch = []
    for pair in settings.pairs:
        got = {tf: svc.fetch(pair, tf, 500 if tf == SIGNAL_TF else 300) for tf in (SIGNAL_TF, "1h", "4h")}
        bad = [f"{tf}: {r.error or 'invalid'}" for tf, r in got.items() if not r.ok]
        if bad:
            summary["pairs"][pair] = "skipped, data rejected: " + "; ".join(bad)
            broker.log("data", f"{pair} skipped: {'; '.join(bad)}")
            continue
        d = _arrays(got[SIGNAL_TF].candles)
        # 2. manage open positions with every newly closed 15m candle
        for i in range(len(d["open_time"])):
            broker.on_bar(pair, Bar(int(d["open_time"][i]), int(d["close_time"][i]), d["open"][i], d["high"][i], d["low"][i], d["close"][i]), MAX_HOLD_MS)
        x = Context(pair, SIGNAL_TF, d, _arrays(got["1h"].candles), _arrays(got["4h"].candles))
        view = analyst.market_view(x)
        view.update(symbol=pair, data_ms=int(d["close_time"][-1]) + 1)
        watch.append(view)
        # 4. strategies on the last closed candle only
        last = x.n - 1
        sigs = [s for name in enabled for s in STRATEGIES[name](x) if s.bar == last]
        live = src.fetch_candles(pair, SIGNAL_TF, 2)
        forming = [c for c in live if c.open_time == int(d["close_time"][-1]) + 1]
        summary["pairs"][pair] = f"ok, {len(sigs)} setup(s) on the {SIGNAL_TF} candle closed {datetime.fromtimestamp((d['close_time'][-1] + 1) / 1000, timezone.utc):%H:%M} UTC"
        for s in sigs:
            sig_id = f"{pair}|{s.strategy}|{SIGNAL_TF}|{int(d['close_time'][last])}|{s.side}"
            if not forming:
                broker.record_signal(sig_id, summary["time"], pair, s.strategy, s.side, SIGNAL_TF, "SIGNAL INVALIDATED", "no current price available")
                continue
            price = forming[-1].close  # market order now
            acct = account_state(broker, summary["time"])
            rec = conf.get((s.strategy, SIGNAL_TF))
            card, why = build_card(s, price, price, int(d["close_time"][last]), SIGNAL_TF, acct, rules[pair], settings, analyst.confidence_line(rec))
            if card is None:
                if broker.record_signal(sig_id, summary["time"], pair, s.strategy, s.side, SIGNAL_TF, "SIGNAL INVALIDATED", why):
                    summary["rejected"].append(f"{pair} {s.side} {s.strategy}: {why}")
                continue
            card.explanation = card.explanation + ". " + analyst.explain(card, view).split("\n", 1)[0].replace("Why: ", "")
            if not broker.record_signal(sig_id, summary["time"], pair, s.strategy, s.side, SIGNAL_TF, "ENTRY CONFIRMED", card=card):
                continue  # already handled on a previous run
            fill = Bar(forming[-1].open_time, forming[-1].close_time, price, price, price, price)
            if broker.open_from_card(sig_id, card, fill):
                summary["cards"].append(card.text())
    (VAR_DIR / "watchlist.json").write_text(json.dumps(watch, indent=1))
    if not summary["cards"]:
        summary["verdict"] = NO_TRADE
    return summary


def run_forever(interval_s: int | None = None):
    """Wake a few seconds after every 15m close (or every interval_s), scan, sleep. Survives errors."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(VAR_DIR / "scanner.log"), logging.StreamHandler()])
    svc = MarketDataService(SETTINGS)
    broker = PaperBroker(svc.con, SETTINGS.costs, SETTINGS.risk.starting_equity)
    assert SETTINGS.mode == "paper" or SETTINGS.live_trading_allowed(), "live mode needs explicit authorization"
    step = TIMEFRAME_SECONDS[SIGNAL_TF]
    backoff = 5
    while True:
        try:
            s = scan_once(svc, broker)
            log.info("scan ok: %s | new trades: %d | rejected: %d", s["pairs"], len(s["cards"]), len(s["rejected"]))
            backoff = 5
        except Exception as e:  # keep running; never crash the loop on one bad cycle
            log.exception("scan failed: %s", e)
            time.sleep(min(backoff, 300))
            backoff *= 2
            continue
        wait = interval_s or (step - time.time() % step + 5)
        time.sleep(wait)
