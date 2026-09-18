import uuid

import httpx
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from chat_agent.graph import build_graph
from chat_agent.tools import RANDOM_NUMBER_OFFSET
from langtest import langtest


def _tool_message(result):
    return next(m for m in result["messages"] if type(m).__name__ == "ToolMessage")


def test_fork_before_add_random_number_diverges_while_original_thread_stays_untouched(tmp_path, monkeypatch, free_port):
    """The canonical LangTest scenario: fork right before add_random_number
    executes, edit its argument, replay — the forked thread should diverge
    from the original, and the original's history must be provably
    unchanged by the fork.
    """
    monkeypatch.setenv("LANGTEST_EXAMPLE_STUB", "1")

    db_path = str(tmp_path / "checkpoints.db")
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"

    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = build_graph(checkpointer)
        wrapped = langtest(graph, port=port)
        try:
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            original_result = wrapped.invoke(
                {"messages": [HumanMessage("add a random number to 8")]}, config
            )
            assert _tool_message(original_result).content == f"{8 + RANDOM_NUMBER_OFFSET}.0"

            history_before = list(graph.get_state_history(config))
            fork_point = next(s for s in history_before if s.next == ("tools",))
            pending_call = fork_point.values["messages"][-1]
            assert pending_call.tool_calls[0]["name"] == "add_random_number"

            history_via_api_before = httpx.get(f"{base_url}/threads/{thread_id}/history", timeout=5).json()

            edited_messages = [m.model_dump() for m in fork_point.values["messages"]]
            edited_messages[-1]["tool_calls"][0]["args"] = {"a": 800}

            fork_response = httpx.post(
                f"{base_url}/fork",
                json={
                    "thread_id": thread_id,
                    "checkpoint_id": fork_point.config["configurable"]["checkpoint_id"],
                    "edited_state": {"messages": edited_messages},
                },
                timeout=5,
            )
            assert fork_response.status_code == 201
            new_thread_id = fork_response.json()["thread_id"]
            assert new_thread_id != thread_id

            forked_result = wrapped.invoke(None, {"configurable": {"thread_id": new_thread_id}})

            history_via_api_after = httpx.get(f"{base_url}/threads/{thread_id}/history", timeout=5).json()
        finally:
            if wrapped._langtest_process is not None:
                wrapped._langtest_process.terminate()
                wrapped._langtest_process.wait(timeout=5)

    assert history_via_api_before == history_via_api_after

    original_tool_message = _tool_message(original_result)
    forked_tool_message = _tool_message(forked_result)
    assert original_tool_message.content == f"{8 + RANDOM_NUMBER_OFFSET}.0"
    assert forked_tool_message.content == f"{800 + RANDOM_NUMBER_OFFSET}.0"
    assert forked_tool_message.content != original_tool_message.content
