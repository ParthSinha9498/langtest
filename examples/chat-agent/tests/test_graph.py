import uuid

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from chat_agent.graph import build_graph
from chat_agent.tools import RANDOM_NUMBER_OFFSET


def _invoke(checkpointer, thread_id, text):
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke({"messages": [HumanMessage(text)]}, config)


def test_chitchat_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGTEST_EXAMPLE_STUB", "1")
    db_path = str(tmp_path / "chat.db")

    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        result = _invoke(checkpointer, str(uuid.uuid4()), "hello there, how are you?")

    last = result["messages"][-1]
    assert isinstance(last, AIMessage)
    assert not getattr(last, "tool_calls", None)


def test_calculator_turn_runs_the_tool_loop(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGTEST_EXAMPLE_STUB", "1")
    db_path = str(tmp_path / "chat.db")

    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        result = _invoke(checkpointer, str(uuid.uuid4()), "add 3 and 5")

    message_types = [type(m).__name__ for m in result["messages"]]
    assert "ToolMessage" in message_types
    tool_message = next(m for m in result["messages"] if type(m).__name__ == "ToolMessage")
    assert tool_message.content == "8.0"
    assert "8.0" in result["messages"][-1].content


def test_plain_add_never_calls_the_random_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGTEST_EXAMPLE_STUB", "1")
    db_path = str(tmp_path / "chat.db")

    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        first = _invoke(checkpointer, str(uuid.uuid4()), "add 3 and 5")
        second = _invoke(checkpointer, str(uuid.uuid4()), "add 3 and 5")

    for result in (first, second):
        tool_call_message = next(m for m in result["messages"] if getattr(m, "tool_calls", None))
        assert tool_call_message.tool_calls[0]["name"] == "add"
    first_tool_message = next(m for m in first["messages"] if type(m).__name__ == "ToolMessage")
    second_tool_message = next(m for m in second["messages"] if type(m).__name__ == "ToolMessage")
    assert first_tool_message.content == second_tool_message.content == "8.0"


def test_calculator_symbol_and_keyword_phrasing_agree(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGTEST_EXAMPLE_STUB", "1")
    db_path = str(tmp_path / "chat.db")

    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        symbol_result = _invoke(checkpointer, str(uuid.uuid4()), "12 - 5")
        keyword_result = _invoke(checkpointer, str(uuid.uuid4()), "subtract 5 from 12")

    for result in (symbol_result, keyword_result):
        tool_message = next(m for m in result["messages"] if type(m).__name__ == "ToolMessage")
        assert tool_message.content == "7.0"


def test_conversation_history_persists_across_turns(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGTEST_EXAMPLE_STUB", "1")
    db_path = str(tmp_path / "chat.db")
    thread_id = str(uuid.uuid4())

    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        first = _invoke(checkpointer, thread_id, "hi")
        second = _invoke(checkpointer, thread_id, "how are you")

    assert len(second["messages"]) > len(first["messages"])
    first_contents = {m.content for m in first["messages"]}
    second_contents = {m.content for m in second["messages"]}
    assert first_contents.issubset(second_contents)


def test_add_random_number_is_only_called_when_explicitly_asked(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGTEST_EXAMPLE_STUB", "1")
    db_path = str(tmp_path / "chat.db")

    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        result = _invoke(checkpointer, str(uuid.uuid4()), "add a random number to 8")

    tool_call_message = next(m for m in result["messages"] if getattr(m, "tool_calls", None))
    assert tool_call_message.tool_calls[0]["name"] == "add_random_number"
    tool_message = next(m for m in result["messages"] if type(m).__name__ == "ToolMessage")
    assert tool_message.content == f"{8 + RANDOM_NUMBER_OFFSET}.0"


def test_add_random_number_is_deterministic_and_tunable(tmp_path, monkeypatch):
    # Not actually random — a fixed offset, so the same input always gives the
    # same output. Changing RANDOM_NUMBER_OFFSET and re-running is how you
    # repeatably test the fork/replay flow against this tool.
    monkeypatch.setenv("LANGTEST_EXAMPLE_STUB", "1")
    db_path = str(tmp_path / "chat.db")

    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        first = _invoke(checkpointer, str(uuid.uuid4()), "add a random number to 8")
        second = _invoke(checkpointer, str(uuid.uuid4()), "add a random number to 8")

    first_tool_message = next(m for m in first["messages"] if type(m).__name__ == "ToolMessage")
    second_tool_message = next(m for m in second["messages"] if type(m).__name__ == "ToolMessage")
    assert first_tool_message.content == second_tool_message.content == f"{8 + RANDOM_NUMBER_OFFSET}.0"
