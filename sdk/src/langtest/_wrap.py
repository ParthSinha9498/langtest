import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any

from langtest._checkpointer import sqlite_path
from langtest._net import port_in_use, wait_for_port

DEFAULT_PORT = 8010


def _running_server_db_path(port: int) -> str | None:
    """The db_path a LangTest server already on this port reports via /health,
    or None if nothing there is answering as a LangTest server at all.
    """
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            return json.loads(response.read())["db_path"]
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, OSError):
        return None


class LangTestWrapper:
    """Transparent proxy around a compiled LangGraph graph.

    Every attribute access — invoke, ainvoke, get_state_history,
    update_state, get_graph, ... — is forwarded to the wrapped graph
    unchanged, so callers see exactly the same behavior as the unwrapped
    object. The only side effect is starting the LangTest server subprocess
    when the wrapper is created.
    """

    def __init__(self, graph: Any, port: int):
        self._langtest_graph = graph
        self._langtest_port = port
        self._langtest_process: subprocess.Popen | None = None
        self._start_server()

    def _start_server(self) -> None:
        db_path = sqlite_path(self._langtest_graph.checkpointer)

        if port_in_use(self._langtest_port):
            if _running_server_db_path(self._langtest_port) == db_path:
                return
            raise RuntimeError(
                f"Port {self._langtest_port} is already in use by something other than a "
                f"LangTest server for this graph's database ({db_path}) — pass a different "
                f"port to langtest(graph, port=...)."
            )

        env = {
            **os.environ,
            "LANGTEST_DB_PATH": db_path,
            "LANGTEST_PORT": str(self._langtest_port),
        }
        self._langtest_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "langtest_server.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self._langtest_port),
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        wait_for_port(self._langtest_port)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._langtest_graph, name)


def langtest(graph: Any, port: int = DEFAULT_PORT) -> Any:
    """Wrap an already-compiled LangGraph graph so LangTest can debug it.

    Reads the checkpointer the graph was already compiled with — langtest()
    never provisions one. Starts the LangTest server (a separate process)
    pointed at that checkpointer's storage, then returns a wrapper that
    behaves exactly like the original graph.
    """
    if graph.checkpointer is None:
        raise ValueError(
            "langtest(graph) requires the graph to be compiled with a checkpointer "
            "(graph.compile(checkpointer=...)). LangTest never provisions one for you."
        )
    return LangTestWrapper(graph, port)
