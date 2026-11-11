from cryptoai.config import RiskLimits
from cryptoai.risk.limits import AccountState, TradeIdea, check_trade, reward_risk

L = RiskLimits()
def acct(**kw):
    a = dict(equity=100, start_of_day_equity=100, start_of_week_peak_equity=100, trades_opened_today=0)
    a.update(kw); return AccountState(**a)
GOOD = TradeIdea("LONG", 100, 99, 102, 0.005)

def test_good_trade_passes():
    assert check_trade(GOOD, acct(), L).allowed

def test_requires_stop_and_target():
    r = check_trade(TradeIdea("LONG", 100, None, 102, 0.005), acct(), L)
    assert not r.allowed and "no stop loss" in r.reasons

def test_min_reward_risk():
    assert reward_risk("SHORT", 100, 101, 98) == 2.0
    r = check_trade(TradeIdea("LONG", 100, 99, 101.5, 0.005), acct(), L)
    assert not r.allowed and any("reward/risk" in x for x in r.reasons)

def test_risk_cap_daily_weekly_and_trade_count():
    assert not check_trade(TradeIdea("LONG", 100, 99, 102, 0.02), acct(), L).allowed
    assert not check_trade(GOOD, acct(equity=98), L).allowed            # -2% today
    assert not check_trade(GOOD, acct(equity=95, start_of_day_equity=95), L).allowed  # -5% week
    assert not check_trade(GOOD, acct(trades_opened_today=3), L).allowed
    assert check_trade(GOOD, acct(equity=98.1), L).allowed               # -1.9% still ok
