from fastapi.testclient import TestClient

from langtest_server.app import app


def test_returns_ordered_full_snapshots(chat_agent_db):
    _, (thread_id, _) = chat_agent_db
    client = TestClient(app)

    response = client.get(f"/threads/{thread_id}/history")

    assert response.status_code == 200
    body = response.json()
    steps = [c["step"] for c in body]
    assert steps == sorted(steps)
    last = body[-1]
    assert len(last["values"]["messages"]) == 4


def test_enriches_with_node_attribution(chat_agent_db):
    """This is the point of rebuilding the actual chat_agent graph server-side:
    knowing which node produced each checkpoint, and what's pending next.
    """
    _, (thread_id, _) = chat_agent_db
    client = TestClient(app)

    body = client.get(f"/threads/{thread_id}/history").json()
    by_step = {c["step"]: c for c in body}

    assert by_step[-1]["produced_by_nodes"] == []  # nothing ran yet
    assert by_step[0]["produced_by_nodes"] == ["__start__"]
    assert by_step[0]["next"] == ["router"]
    assert by_step[1]["produced_by_nodes"] == ["router"]
    assert by_step[1]["next"] == ["chitchat"]
    assert by_step[2]["produced_by_nodes"] == ["chitchat"]
    assert by_step[2]["next"] == []  # turn finished


def test_unknown_thread_is_404(chat_agent_db):
    client = TestClient(app)

    response = client.get("/threads/does-not-exist/history")

    assert response.status_code == 404
