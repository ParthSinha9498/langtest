from fastapi.testclient import TestClient

from langtest_server.app import app


def _history(client, thread_id):
    return client.get(f"/threads/{thread_id}/history").json()


def _with_edited_last_message_content(fork_point, new_content):
    messages = fork_point["values"]["messages"]
    return messages[:-1] + [{**messages[-1], "content": new_content}]


def test_fork_creates_a_new_thread_with_edited_state(chat_agent_db):
    _, (thread_id, _) = chat_agent_db
    client = TestClient(app)
    source_history = _history(client, thread_id)
    fork_point = source_history[-1]

    response = client.post(
        "/fork",
        json={
            "thread_id": thread_id,
            "checkpoint_id": fork_point["checkpoint_id"],
            "edited_state": {
                "messages": _with_edited_last_message_content(fork_point, "edited reply")
            },
        },
    )

    assert response.status_code == 201
    new_thread_id = response.json()["thread_id"]
    assert new_thread_id != thread_id

    forked_history = _history(client, new_thread_id)
    assert len(forked_history) == 1
    assert forked_history[0]["values"]["messages"][-1]["content"] == "edited reply"


def test_original_thread_is_untouched_after_fork(chat_agent_db):
    _, (thread_id, _) = chat_agent_db
    client = TestClient(app)
    before = _history(client, thread_id)

    fork_point = before[-1]
    client.post(
        "/fork",
        json={
            "thread_id": thread_id,
            "checkpoint_id": fork_point["checkpoint_id"],
            "edited_state": {
                "messages": _with_edited_last_message_content(fork_point, "edited reply")
            },
        },
    )

    after = _history(client, thread_id)
    assert before == after


def test_forking_an_unknown_checkpoint_is_404(chat_agent_db):
    _, (thread_id, _) = chat_agent_db
    client = TestClient(app)

    response = client.post(
        "/fork",
        json={"thread_id": thread_id, "checkpoint_id": "does-not-exist", "edited_state": {}},
    )

    assert response.status_code == 404
