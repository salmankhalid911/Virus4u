"""Account-level risk gate. Every new trade must pass all checks; any failure blocks it.

These rules cannot be overridden by a strategy, the AI analyst, or a confidence score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..config import RiskLimits


@dataclass
class ClosedTrade:
    closed_at: datetime
    pnl: float  # after fees


@dataclass
class AccountState:
    equity: float
    start_of_day_equity: float
    start_of_week_peak_equity: float
    trades_opened_today: int
    open_positions: int = 0
    closed: list[ClosedTrade] = field(default_factory=list)


@dataclass(frozen=True)
class TradeIdea:
    side: str
    entry: float
    stop: float | None
    target: float | None
    risk_pct: float


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reasons: tuple[str, ...]


def reward_risk(side: str, entry: float, stop: float, target: float) -> float:
    risk = abs(entry - stop)
    reward = (target - entry) if side == "LONG" else (entry - target)
    return reward / risk if risk > 0 else 0.0


def check_trade(idea: TradeIdea, acct: AccountState, limits: RiskLimits) -> GateResult:
    reasons = []
    if idea.stop is None:
        reasons.append("no stop loss")
    elif (idea.side == "LONG" and idea.stop >= idea.entry) or (idea.side == "SHORT" and idea.stop <= idea.entry):
        reasons.append("stop is on the wrong side of entry")
    if idea.target is None:
        reasons.append("no target")
    if idea.stop is not None and idea.target is not None and not reasons:
        rr = reward_risk(idea.side, idea.entry, idea.stop, idea.target)
        if rr < limits.min_reward_risk - 1e-9:
            reasons.append(f"reward/risk {rr:.2f} is below {limits.min_reward_risk:.1f}")
    if idea.risk_pct > limits.max_risk_pct + 1e-12:
        reasons.append(f"risk {idea.risk_pct:.2%} is above the {limits.max_risk_pct:.0%} maximum")
    day_loss = (acct.start_of_day_equity - acct.equity) / acct.start_of_day_equity
    if day_loss >= limits.max_daily_loss_pct - 1e-12:
        reasons.append(f"daily loss limit reached ({day_loss:.2%})")
    week_dd = (acct.start_of_week_peak_equity - acct.equity) / acct.start_of_week_peak_equity
    if week_dd >= limits.max_weekly_drawdown_pct - 1e-12:
        reasons.append(f"weekly drawdown limit reached ({week_dd:.2%})")
    if acct.trades_opened_today >= limits.max_trades_per_day:
        reasons.append(f"already {acct.trades_opened_today} trades today (max {limits.max_trades_per_day})")
    return GateResult(not reasons, tuple(reasons))


def week_start(t: datetime) -> datetime:
    t = t.astimezone(timezone.utc)
    return (t - timedelta(days=t.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
