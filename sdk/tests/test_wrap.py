import uuid
from typing import TypedDict

import httpx
import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from langtest import langtest


class CounterState(TypedDict):
    x: int


def _increment(state: CounterState) -> CounterState:
    return {"x": state["x"] + 1}


def _build_graph(checkpointer):
    builder = StateGraph(CounterState)
    builder.add_node("increment", _increment)
    builder.add_edge(START, "increment")
    builder.add_edge("increment", END)
    return builder.compile(checkpointer=checkpointer)


@pytest.fixture
def graph(tmp_path):
    db_path = str(tmp_path / "checkpoints.db")
    with SqliteSaver.from_conn_string(db_path) as saver:
        yield _build_graph(saver)


@pytest.fixture
def wrapped(graph, free_port):
    wrapper = langtest(graph, port=free_port())
    yield wrapper
    if wrapper._langtest_process is not None:
        wrapper._langtest_process.terminate()
        wrapper._langtest_process.wait(timeout=5)


@pytest.fixture
async def async_graph(tmp_path):
    db_path = str(tmp_path / "async_checkpoints.db")
    async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
        yield _build_graph(saver)


@pytest.fixture
def async_wrapped(async_graph, free_port):
    wrapper = langtest(async_graph, port=free_port())
    yield wrapper
    if wrapper._langtest_process is not None:
        wrapper._langtest_process.terminate()
        wrapper._langtest_process.wait(timeout=5)


def test_requires_checkpointer():
    builder = StateGraph(CounterState)
    builder.add_node("increment", _increment)
    builder.add_edge(START, "increment")
    builder.add_edge("increment", END)
    graph_without_checkpointer = builder.compile()

    with pytest.raises(ValueError, match="checkpointer"):
        langtest(graph_without_checkpointer)


def test_invoke_is_transparent(graph, wrapped):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = wrapped.invoke({"x": 1}, config)

    assert result == {"x": 2}
    assert result == graph.invoke({"x": 1}, {"configurable": {"thread_id": str(uuid.uuid4())}})


async def test_ainvoke_is_transparent(async_graph, async_wrapped):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = await async_wrapped.ainvoke({"x": 1}, config)

    assert result == {"x": 2}


def test_server_starts_and_reports_db_path(graph, wrapped, tmp_path):
    response = httpx.get(f"http://127.0.0.1:{wrapped._langtest_port}/health", timeout=5)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db_path"] == str(tmp_path / "checkpoints.db")


def test_does_not_spawn_a_second_server_on_same_port(graph, wrapped):
    other_wrapper = langtest(graph, port=wrapped._langtest_port)

    assert other_wrapper._langtest_process is None


def test_refuses_to_reuse_a_port_serving_a_different_database(tmp_path, wrapped):
    db_path = str(tmp_path / "a_different_checkpoints.db")
    with SqliteSaver.from_conn_string(db_path) as other_saver:
        other_graph = _build_graph(other_saver)

        with pytest.raises(RuntimeError, match="already in use"):
            langtest(other_graph, port=wrapped._langtest_port)


async def test_wrap_works_when_called_from_inside_a_running_event_loop(tmp_path, free_port):
    # langtest() is a plain sync call, but nothing stops a caller from making it
    # inside an async function — e.g. a FastAPI startup hook. Recovering an
    # AsyncSqliteSaver's db path needs an awaitable PRAGMA query, and naively
    # doing that with asyncio.run() would crash here since this test body
    # itself already runs inside pytest-asyncio's event loop.
    db_path = str(tmp_path / "from_loop.db")
    async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
        graph = _build_graph(saver)
        wrapper = langtest(graph, port=free_port())
        try:
            result = await wrapper.ainvoke({"x": 1}, {"configurable": {"thread_id": str(uuid.uuid4())}})
            assert result == {"x": 2}
        finally:
            if wrapper._langtest_process is not None:
                wrapper._langtest_process.terminate()
                wrapper._langtest_process.wait(timeout=5)
