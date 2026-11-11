"""Settings for the trading system. Every risk limit lives here, in one place."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAR_DIR = Path(os.environ.get("CRYPTOAI_VAR", ROOT / "var"))

TIMEFRAME_SECONDS = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}


@dataclass(frozen=True)
class RiskLimits:
    starting_equity: float = 100.0
    default_risk_pct: float = 0.005  # 0.5% of equity per trade
    max_risk_pct: float = 0.01  # hard ceiling, 1%
    max_daily_loss_pct: float = 0.02
    max_weekly_drawdown_pct: float = 0.05
    max_trades_per_day: int = 3
    min_reward_risk: float = 2.0
    max_leverage: float = 1.0  # spot only: position value can never exceed cash


@dataclass(frozen=True)
class CostModel:
    taker_fee: float = 0.001  # 0.10% per side (Binance spot default)
    maker_fee: float = 0.001
    slippage: float = 0.0005  # 0.05% per side on market fills and stops
    funding_per_8h: float = 0.0  # spot has no funding; kept for futures later


@dataclass(frozen=True)
class Settings:
    pairs: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    timeframes: tuple[str, ...] = ("5m", "15m", "1h", "4h")
    mode: str = "paper"  # "paper" or "live"; live also needs LIVE_TRADING_AUTHORIZED=yes
    risk: RiskLimits = field(default_factory=RiskLimits)
    costs: CostModel = field(default_factory=CostModel)
    db_path: Path = VAR_DIR / "cryptoai.sqlite3"
    # A closed candle older than this many bar lengths counts as stale.
    max_staleness_bars: float = 2.0

    def live_trading_allowed(self) -> bool:
        """Live trading needs the mode set AND an explicit environment authorization.

        Nothing in the code ever sets either of these; only the account owner can.
        """
        return self.mode == "live" and os.environ.get("LIVE_TRADING_AUTHORIZED") == "yes"


SETTINGS = Settings()
