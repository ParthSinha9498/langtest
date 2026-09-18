import os
import socket
import subprocess
import sys
import time

import httpx
from langgraph.checkpoint.sqlite import SqliteSaver

from conftest import build_toy_graph


def _wait_for_port(port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise RuntimeError(f"server did not start on port {port}")


def _spawn_server(db_path: str, port: int) -> subprocess.Popen:
    env = {**os.environ, "LANGTEST_DB_PATH": db_path, "LANGTEST_PORT": str(port)}
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "langtest_server.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_port(port)
    return process


def test_thread_list_survives_a_server_restart(tmp_path, free_port):
    db_path = str(tmp_path / "restart.db")
    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = build_toy_graph(checkpointer)
        graph.invoke({"messages": [], "total": 1}, {"configurable": {"thread_id": "t1"}})

    port = free_port()
    process = _spawn_server(db_path, port)
    try:
        before = httpx.get(f"http://127.0.0.1:{port}/threads", timeout=5).json()
    finally:
        process.terminate()
        process.wait(timeout=5)

    port2 = free_port()
    process2 = _spawn_server(db_path, port2)
    try:
        after = httpx.get(f"http://127.0.0.1:{port2}/threads", timeout=5).json()
    finally:
        process2.terminate()
        process2.wait(timeout=5)

    assert before == after
    assert len(before) == 1
