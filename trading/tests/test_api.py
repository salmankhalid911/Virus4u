import importlib, sqlite3
from fastapi.testclient import TestClient

def test_dashboard_api_reads_paper_account(tmp_path, monkeypatch):
    monkeypatch.setenv("CRYPTOAI_VAR", str(tmp_path))
    import cryptoai.config as cfg; importlib.reload(cfg)
    import cryptoai.api as api; importlib.reload(api)
    from cryptoai.execution.paper import PaperBroker
    PaperBroker(sqlite3.connect(cfg.SETTINGS.db_path), cfg.SETTINGS.costs, 100.0)
    c = TestClient(api.app)
    s = c.get("/api/state").json()
    assert s["ready"] and s["balance"] == 100.0 and s["mode"] == "paper" and s["live_allowed"] is False
    assert c.get("/").status_code == 200
    # read-only: no write endpoints exist
    assert all(m == {"GET", "HEAD"} or m == {"GET"} for r in api.app.routes for m in [getattr(r, "methods", {"GET"})])
