"""Fetch, validate and store live candles for every pair and timeframe. Prints freshness."""
import logging, sys
from datetime import datetime, timezone
sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.parent.as_posix())
from cryptoai.config import SETTINGS
from cryptoai.data.service import MarketDataService

logging.basicConfig(level=logging.WARNING)
svc = MarketDataService(SETTINGS)
now = svc.now_ms()
print("exchange server time:", datetime.fromtimestamp(now / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
bad = 0
for p in SETTINGS.pairs:
    for tf in SETTINGS.timeframes:
        r = svc.fetch(p, tf, 300)
        if r.ok:
            last = r.candles[-1]
            t = datetime.fromtimestamp(last.open_time / 1000, timezone.utc).strftime("%m-%d %H:%M")
            print(f"{p:<8} {tf:<4} OK   source={r.source:<8} bars={r.report.accepted:<4} last closed bar {t} UTC  close={last.close:<10g} age={r.report.age_seconds:>5.0f}s  forming bars dropped={r.report.dropped_unclosed} gaps={len(r.report.gaps)}")
        else:
            bad += 1
            print(f"{p:<8} {tf:<4} FAIL {r.error}")
print("stored in", SETTINGS.db_path)
sys.exit(1 if bad else 0)
