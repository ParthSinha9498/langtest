from typing import Annotated

import pytest
from chat_agent.graph import build_graph
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ToyState(TypedDict):
    messages: Annotated[list, add_messages]
    total: int


def _reply(state: ToyState) -> dict:
    return {"messages": [AIMessage(content=f"total is now {state.get('total', 0)}")]}


def build_toy_graph(checkpointer):
    builder = StateGraph(ToyState)
    builder.add_node("reply", _reply)
    builder.add_edge(START, "reply")
    builder.add_edge("reply", END)
    return builder.compile(checkpointer=checkpointer)


@pytest.fixture
def populated_db(tmp_path, monkeypatch):
    """Generic checkpoint data from a graph shape LangTest's server doesn't know
    about — valid for the schema-agnostic /threads endpoint, but NOT for
    /history (see chat_agent_db): that endpoint now rebuilds an actual
    chat_agent graph to compute next/produced_by_node, so it can't make sense
    of a "total" channel that graph doesn't define.
    """
    db_path = str(tmp_path / "checkpoints.db")
    monkeypatch.setenv("LANGTEST_DB_PATH", db_path)

    thread_ids = ["thread-a", "thread-b"]
    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = build_toy_graph(checkpointer)
        for thread_id in thread_ids:
            config = {"configurable": {"thread_id": thread_id}}
            graph.invoke({"messages": [HumanMessage("hi")], "total": 1}, config)
            graph.invoke({"messages": [HumanMessage("hi again")], "total": 2}, config)

    return db_path, thread_ids


@pytest.fixture
def chat_agent_db(tmp_path, monkeypatch):
    """Real chat_agent-shaped checkpoint data (stub LLM), for endpoints that
    now rebuild the actual chat_agent graph: /history and /fork.
    """
    monkeypatch.setenv("LANGTEST_EXAMPLE_STUB", "1")
    db_path = str(tmp_path / "chat_agent.db")
    monkeypatch.setenv("LANGTEST_DB_PATH", db_path)

    thread_ids = ["thread-a", "thread-b"]
    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = build_graph(checkpointer)
        for thread_id in thread_ids:
            config = {"configurable": {"thread_id": thread_id}}
            graph.invoke({"messages": [HumanMessage("hi")]}, config)
            graph.invoke({"messages": [HumanMessage("hi again")]}, config)

    return db_path, thread_ids
