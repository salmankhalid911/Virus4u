from cryptoai.config import Settings

def test_live_trading_off_by_default(monkeypatch):
    monkeypatch.delenv("LIVE_TRADING_AUTHORIZED", raising=False)
    assert Settings().mode == "paper"
    assert not Settings().live_trading_allowed()
    assert not Settings(mode="live").live_trading_allowed()   # mode alone is not enough
    monkeypatch.setenv("LIVE_TRADING_AUTHORIZED", "yes")
    assert not Settings().live_trading_allowed()              # env alone is not enough
