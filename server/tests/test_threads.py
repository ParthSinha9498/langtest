from fastapi.testclient import TestClient

from langtest_server.app import app


def test_lists_every_thread(populated_db):
    _, thread_ids = populated_db
    client = TestClient(app)

    response = client.get("/threads")

    assert response.status_code == 200
    body = response.json()
    assert {t["thread_id"] for t in body} == set(thread_ids)
    for thread in body:
        assert thread["checkpoint_count"] > 0
        assert thread["latest_checkpoint_id"]
        assert thread["updated_at"]


def test_empty_db_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGTEST_DB_PATH", str(tmp_path / "empty.db"))
    client = TestClient(app)

    response = client.get("/threads")

    assert response.status_code == 200
    assert response.json() == []
