from cryptoai.config import CostModel
from cryptoai.data.models import SymbolRules
from cryptoai.risk.sizing import loss_per_unit, size_position

BTC = SymbolRules("BTCUSDT", 0.00001, 0.00001, 0.01, 5.0, "TRADING")
COSTS = CostModel()

def size(**kw):
    args = dict(equity=100, risk_pct=0.005, max_risk_pct=0.01, entry=70000, stop=69300, side="LONG",
                rules=BTC, costs=COSTS, available_cash=100)
    args.update(kw)
    return size_position(**args)

def test_loss_at_stop_never_exceeds_budget_including_costs():
    r = size()
    assert not r.skipped
    assert r.loss_at_stop <= r.dollar_risk_budget + 1e-9
    assert abs(r.dollar_risk_budget - 0.5) < 1e-12
    # and the formula matches: qty * worst-case loss per unit
    assert abs(r.loss_at_stop - r.qty * loss_per_unit(70000, 69300, "LONG", COSTS)) < 1e-12

def test_short_side_and_wrong_side_stop():
    assert not size(side="SHORT", stop=70700).skipped
    assert size(side="SHORT", stop=69300).skipped
    assert size(side="LONG", stop=70700).skipped

def test_risk_is_capped_at_max():
    r = size(risk_pct=0.05)
    assert abs(r.dollar_risk_budget - 1.0) < 1e-12  # capped to 1%

def test_spot_never_exceeds_cash():
    r = size(stop=69930)  # 0.1% stop would need ~$300 position on $100
    assert r.notional <= 100
    assert r.loss_at_stop <= r.dollar_risk_budget

def test_skips_when_exchange_minimum_breaks_risk_or_cash():
    big_min = SymbolRules("BTCUSDT", 0.001, 0.001, 0.01, 5.0, "TRADING")  # min 0.001 BTC = $70
    r = size(rules=big_min, stop=63000)  # 10% stop: $0.50 budget buys far less than 0.001
    assert r.skipped and "minimum" in r.reason
    tiny_cash = size(available_cash=4)  # can't reach $5 minimum order
    assert tiny_cash.skipped and "$5.00" in tiny_cash.reason

def test_halted_symbol_is_skipped():
    halted = SymbolRules("BTCUSDT", 0.00001, 0.00001, 0.01, 5.0, "BREAK")
    assert size(rules=halted).skipped
