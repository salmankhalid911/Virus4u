import sys, pathlib
sys.path.insert(0, pathlib.Path(__file__).resolve().parent.parent.as_posix())
from cryptoai.config import VAR_DIR
from cryptoai.backtest.history import HIST_PAIRS, download, rules
for s in HIST_PAIRS:
    for tf, days in (("15m", 740), ("1h", 760), ("4h", 800)):
        print(download(VAR_DIR, s, tf, days), flush=True)
print(rules(VAR_DIR, HIST_PAIRS))
