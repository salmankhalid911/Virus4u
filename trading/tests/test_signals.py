from cryptoai.config import Settings
from cryptoai.data.models import SymbolRules
from cryptoai.risk.limits import AccountState
from cryptoai.signals import build_card
from cryptoai.strategies import Signal

R = SymbolRules("SOLUSDT", 0.001, 0.001, 0.01, 5.0, "TRADING")
ACCT = AccountState(100, 100, 100, 0)

def test_card_prices_risk_and_format():
    card, why = build_card(Signal("SOLUSDT", "A_trend", "SHORT", 0, 85.137, "rally to EMA20"), 83.0, 83.0, 0, "15m", ACCT, R, Settings(), "UNVALIDATED")
    assert why == "" and card.direction == "SHORT"
    for v in (card.entry, card.stop, card.tp1, card.tp2, card.tp3):
        assert abs(v * 100 - round(v * 100)) < 1e-6   # on the 0.01 tick
    assert card.tp1 < card.entry < card.stop and card.reward_risk >= 2 - 1e-9
    assert card.capital_at_risk <= 0.5 + 1e-9 and card.position_value <= 100
    txt = card.text()
    for field in ("PAIR:", "DIRECTION:", "STRATEGY:", "CURRENT PRICE:", "ENTRY PRICE:", "STOP LOSS:", "TAKE PROFIT 1:", "TAKE PROFIT 2:",
                  "TAKE PROFIT 3:", "RISK/REWARD:", "POSITION SIZE:", "CAPITAL AT RISK:", "CONFIDENCE SCORE:", "TIMEFRAME:",
                  "SETUP EXPLANATION:", "INVALIDATION CONDITION:", "DATA TIMESTAMP:"):
        assert field in txt

def test_no_trade_when_blocked():
    assert build_card(Signal("SOLUSDT", "A_trend", "LONG", 0, 84.0, ""), 83.0, 83.0, 0, "15m", ACCT, R, Settings(), "")[0] is None
    blocked = AccountState(97.9, 100, 100, 1)  # -2.1% today
    card, why = build_card(Signal("SOLUSDT", "A_trend", "LONG", 0, 82.0, ""), 83.0, 83.0, 0, "15m", blocked, R, Settings(), "")
    assert card is None and "daily loss" in why
