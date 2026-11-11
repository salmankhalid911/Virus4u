"""Turn a strategy signal into a fully priced, risk-checked trade card (the exact signal format).

A card is only produced when every number can be computed from real candles and the trade
passes the risk gate and the exchange order rules. Otherwise the result is NO TRADE.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .config import Settings
from .data.models import SymbolRules
from .risk.limits import AccountState, TradeIdea, check_trade, reward_risk
from .risk.sizing import size_position
from .strategies import Signal

STATUSES = ("WAITING", "SETUP DETECTED", "ENTRY CONFIRMED", "TRADE ACTIVE", "TAKE PROFIT HIT", "STOP LOSS HIT", "SIGNAL INVALIDATED")
NO_TRADE = "NO TRADE — WAIT FOR A BETTER SETUP."
STRATEGY_NAMES = {"A_trend": "Trend Pullback", "B_breakout": "Breakout and Retest", "C_liquidity": "Liquidity Sweep + CHOCH", "D_range": "Range Reversion"}


@dataclass
class TradeCard:
    pair: str
    direction: str
    strategy: str
    current_price: float
    entry: float
    stop: float
    tp1: float
    tp2: float
    tp3: float
    reward_risk: float
    qty: float
    position_value: float
    capital_at_risk: float
    confidence: str
    timeframe: str
    explanation: str
    invalidation: str
    data_timestamp: str
    status: str = "SETUP DETECTED"

    def text(self) -> str:
        p = lambda v: f"{v:,.6g}"
        return "\n".join([
            f"PAIR: {self.pair[:-4]}/USDT",
            f"DIRECTION: {self.direction}",
            f"STRATEGY: {self.strategy}",
            f"CURRENT PRICE: {p(self.current_price)}",
            f"ENTRY PRICE: {p(self.entry)}",
            f"STOP LOSS: {p(self.stop)}",
            f"TAKE PROFIT 1: {p(self.tp1)} (close 50%)",
            f"TAKE PROFIT 2: {p(self.tp2)} (close 30%)",
            f"TAKE PROFIT 3: {p(self.tp3)} (close 20%)",
            f"RISK/REWARD: 1:{self.reward_risk:.2f} to TP1",
            f"POSITION SIZE: {self.qty:g} {self.pair[:-4]} (${self.position_value:,.2f})",
            f"CAPITAL AT RISK: ${self.capital_at_risk:.2f} including fees and slippage",
            f"CONFIDENCE SCORE: {self.confidence}",
            f"TIMEFRAME: {self.timeframe}",
            f"SETUP EXPLANATION: {self.explanation}",
            f"INVALIDATION CONDITION: {self.invalidation}",
            f"DATA TIMESTAMP: {self.data_timestamp}",
        ])


def _round_tick(x: float, tick: float) -> float:
    return round(round(x / tick) * tick, 10)


def build_card(sig: Signal, entry: float, current: float, bar_close_ms: int, tf: str, acct: AccountState,
               rules: SymbolRules, settings: Settings, confidence: str) -> tuple[TradeCard | None, str]:
    """Return (card, "") or (None, reason it is NO TRADE)."""
    side = 1 if sig.side == "LONG" else -1
    entry = _round_tick(entry, rules.tick_size)
    stop = _round_tick(sig.stop, rules.tick_size)
    risk = (entry - stop) * side
    if risk <= 0:
        return None, "price is already beyond the stop"
    tps = [_round_tick(entry + side * k * risk, rules.tick_size) for k in (2, 3, 4)]
    if sig.target_cap is not None and (tps[0] - sig.target_cap) * side > 0:
        return None, "first target does not fit inside the range"
    lim = settings.risk
    gate = check_trade(TradeIdea(sig.side, entry, stop, tps[0], lim.default_risk_pct), acct, lim)
    if not gate.allowed:
        return None, "; ".join(gate.reasons)
    size = size_position(acct.equity, lim.default_risk_pct, lim.max_risk_pct, entry, stop, sig.side, rules, settings.costs,
                         acct.equity, lim.max_leverage)
    if size.skipped:
        return None, size.reason
    ts = datetime.fromtimestamp((bar_close_ms + 1) / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M UTC (closed %s candle)" % tf)
    inval = (f"Close {'below' if side == 1 else 'above'} {stop:,.6g}, or no entry fill within one candle.")
    card = TradeCard(sig.symbol, sig.side, STRATEGY_NAMES.get(sig.strategy, sig.strategy), current, entry, stop, *tps,
                     reward_risk(sig.side, entry, stop, tps[0]), size.qty, size.notional, size.loss_at_stop, confidence, tf,
                     sig.reason, inval, ts)
    return card, ""
