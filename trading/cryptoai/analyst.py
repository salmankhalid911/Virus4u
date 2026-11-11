"""Market analyst: explains a setup in plain language.

It reads the same numbers the strategy and risk manager used and describes them. It cannot
change a stop, a size or a risk limit, and it never invents a probability. The confidence
line is the strategy's measured backtest record, or a plain statement that there is none.
"""
from __future__ import annotations

import numpy as np

from .signals import TradeCard
from .strategies import Context

TREND = {1: "up", -1: "down", 0: "flat"}


def market_view(x: Context, i: int | None = None) -> dict:
    i = x.n - 1 if i is None else i
    t4 = int(np.nan_to_num(x.trend4h[i]))
    t1 = int(np.nan_to_num(x.struct1h[i]))
    atrp = x.atr[i] / x.c[i] * 100
    past = (x.atr[max(0, i - 500):i] / x.c[max(0, i - 500):i])
    vol_rank = float((past < x.atr[i] / x.c[i]).mean()) if len(past) else 0.5
    stack = "bullish" if x.ema20[i] > x.ema50[i] > x.ema200[i] else "bearish" if x.ema20[i] < x.ema50[i] < x.ema200[i] else "mixed"
    return dict(trend_4h=TREND[t4], structure_1h=TREND[t1], ema_stack=stack, rsi=float(x.rsi[i]), atr_pct=float(atrp),
                volatility_rank=vol_rank, last_swing_high=float(x.swing_h[i]), last_swing_low=float(x.swing_l[i]), close=float(x.c[i]))


def confidence_line(record: dict | None) -> str:
    """record: measured out-of-sample stats for this strategy+timeframe, or None."""
    if not record or record.get("trades", 0) < 30:
        return "UNVALIDATED: this strategy has no out-of-sample record yet; treat as research only"
    return (f"Backtest (out of sample): {record['trades']} trades, {record['win_rate']:.0f}% wins, "
            f"profit factor {record['profit_factor']:.2f}, {record['expectancy_r']:+.2f}R per trade after costs")


def explain(card: TradeCard, view: dict) -> str:
    side_word = "buy" if card.direction == "LONG" else "sell short"
    with_trend = (card.direction == "LONG" and view["trend_4h"] == "up") or (card.direction == "SHORT" and view["trend_4h"] == "down")
    vol = view["volatility_rank"]
    vol_txt = ("unusually calm, so moves may be slow to reach targets" if vol < 0.2 else
               "very high, so stops are more likely to be hit by noise" if vol > 0.9 else "normal")
    lines = [
        f"Why: {card.explanation}. The 4h trend is {view['trend_4h']} and 1h structure is {view['structure_1h']}; "
        f"EMAs are {view['ema_stack']} and RSI is {view['rsi']:.0f}.",
        f"Entry: {side_word} at {card.entry:,.6g}, the open after the confirming candle closed.",
        f"Invalidation: {card.invalidation}",
        f"Trend alignment: {'with' if with_trend else 'NOT with'} the 4h trend.",
        f"Volatility: ATR is {view['atr_pct']:.2f}% of price, which is {vol_txt}.",
        f"Reward/risk: {card.reward_risk:.1f} to the first target; a stop-out costs ${card.capital_at_risk:.2f}.",
    ]
    return "\n".join(lines)
