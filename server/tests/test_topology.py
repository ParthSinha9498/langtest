from fastapi.testclient import TestClient

from langtest_server.app import app


def test_returns_mermaid_topology():
    client = TestClient(app)

    response = client.get("/graph")

    assert response.status_code == 200
    mermaid = response.json()["mermaid"]
    for node in ("router", "chitchat", "calculator_agent", "tools"):
        assert node in mermaid
