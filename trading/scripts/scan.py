"""Run one scan now (default) or keep running after every 15m candle (--loop)."""
import sys, json, pathlib
sys.path.insert(0, pathlib.Path(__file__).resolve().parent.parent.as_posix())
from cryptoai.config import SETTINGS
from cryptoai.data.service import MarketDataService
from cryptoai.execution.paper import PaperBroker
from cryptoai.report import daily_report
from cryptoai.scanner import run_forever, scan_once
if "--loop" in sys.argv:
    run_forever()
svc = MarketDataService(SETTINGS)
broker = PaperBroker(svc.con, SETTINGS.costs, SETTINGS.risk.starting_equity)
s = scan_once(svc, broker)
for p, v in s["pairs"].items(): print(f"{p}: {v}")
for c in s["cards"]: print("\n" + c)
for r in s["rejected"]: print("rejected:", r)
if not s["cards"]: print("\n" + s["verdict"])
print("\n" + daily_report(broker, s["time"]))
