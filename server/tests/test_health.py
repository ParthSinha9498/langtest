from fastapi.testclient import TestClient

from langtest_server.app import app


def test_health_ok_with_no_db_path_configured(monkeypatch):
    monkeypatch.delenv("LANGTEST_DB_PATH", raising=False)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db_path": None}


def test_health_reports_configured_db_path(monkeypatch):
    monkeypatch.setenv("LANGTEST_DB_PATH", "/tmp/checkpoints.db")
    client = TestClient(app)

    response = client.get("/health")

    assert response.json()["db_path"] == "/tmp/checkpoints.db"
