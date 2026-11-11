import sys, pathlib
sys.path.insert(0, pathlib.Path(__file__).resolve().parent.parent.as_posix())
from cryptoai.config import VAR_DIR
from cryptoai.backtest.history import download
sym = sys.argv[1]
print(download(VAR_DIR, sym, "1d", 900), flush=True)
print(download(VAR_DIR, sym, "5m", 745), flush=True)
