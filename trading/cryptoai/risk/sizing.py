"""Position sizing: size = dollar risk / distance to stop, then fit it to costs and exchange rules.

The loss if the stop is hit INCLUDES fees and slippage on both sides, so the real loss
at the stop never exceeds the dollar risk. If the exchange minimum forces a bigger
position than the risk budget allows, the trade is skipped.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..config import CostModel
from ..data.models import SymbolRules


@dataclass(frozen=True)
class SizeResult:
    qty: float
    notional: float
    dollar_risk_budget: float
    loss_at_stop: float  # including fees and slippage
    skipped: bool
    reason: str = ""


def _floor_to_step(x: float, step: float) -> float:
    return math.floor(x / step + 1e-9) * step


def loss_per_unit(entry: float, stop: float, side: str, costs: CostModel) -> float:
    """Worst-case loss per unit if the stop fills: price move + slippage + fees on both sides."""
    if side == "LONG":
        fill_in = entry * (1 + costs.slippage)
        fill_out = stop * (1 - costs.slippage)
        move = fill_in - fill_out
    else:
        fill_in = entry * (1 - costs.slippage)
        fill_out = stop * (1 + costs.slippage)
        move = fill_out - fill_in
    fees = fill_in * costs.taker_fee + fill_out * costs.taker_fee
    return move + fees


def size_position(
    equity: float,
    risk_pct: float,
    max_risk_pct: float,
    entry: float,
    stop: float,
    side: str,
    rules: SymbolRules,
    costs: CostModel,
    available_cash: float,
    max_leverage: float = 1.0,
) -> SizeResult:
    def skip(reason: str, budget: float = 0.0) -> SizeResult:
        return SizeResult(0.0, 0.0, budget, 0.0, True, reason)

    if side not in ("LONG", "SHORT"):
        return skip(f"unknown side {side}")
    if entry <= 0 or stop <= 0:
        return skip("entry and stop must be positive")
    if (side == "LONG" and stop >= entry) or (side == "SHORT" and stop <= entry):
        return skip("stop is on the wrong side of entry")
    if rules.status != "TRADING":
        return skip(f"{rules.symbol} is not trading ({rules.status})")
    risk_pct = min(risk_pct, max_risk_pct)
    budget = equity * risk_pct
    if budget <= 0:
        return skip("no risk budget", budget)

    per_unit = loss_per_unit(entry, stop, side, costs)
    qty = _floor_to_step(budget / per_unit, rules.step_size)
    # Spot: position value can never exceed cash (times leverage, which is 1.0 for spot).
    cash_cap = _floor_to_step(available_cash * max_leverage / (entry * (1 + costs.slippage + costs.taker_fee)), rules.step_size)
    qty = min(qty, cash_cap)
    notional = qty * entry
    if qty < rules.min_qty:
        return skip(f"size {qty:g} is below the exchange minimum {rules.min_qty:g}", budget)
    if notional < rules.min_notional:
        return skip(f"order value ${notional:.2f} is below the exchange minimum ${rules.min_notional:.2f}", budget)
    loss = qty * per_unit
    if loss > budget * (1 + 1e-9):
        return skip("cannot fit the exchange minimum inside the risk budget", budget)
    return SizeResult(qty, notional, budget, loss, False)
