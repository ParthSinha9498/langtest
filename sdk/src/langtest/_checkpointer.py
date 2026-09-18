import asyncio
import sqlite3
import threading
from typing import Any


def sqlite_path(checkpointer: Any) -> str:
    """Recover the on-disk sqlite file path backing a checkpointer's connection.

    Works for both the sync SqliteSaver (sqlite3.Connection) and the async
    AsyncSqliteSaver (aiosqlite.Connection) — `PRAGMA database_list` reports
    the file path for either, but the async connection only exposes it
    through an awaitable API.
    """
    conn = getattr(checkpointer, "conn", None)
    if conn is None:
        raise TypeError(
            "langtest() only supports sqlite-backed checkpointers right now, "
            f"got {type(checkpointer).__name__}."
        )

    if isinstance(conn, sqlite3.Connection):
        rows = conn.execute("PRAGMA database_list").fetchall()
    else:
        async def _fetch() -> list[tuple[Any, ...]]:
            cursor = await conn.execute("PRAGMA database_list")
            return await cursor.fetchall()

        rows = _run_to_completion(_fetch())

    for _, name, file in rows:
        if name == "main":
            return file

    raise RuntimeError("Could not determine the sqlite file path for this checkpointer.")


def _run_to_completion(coro: Any) -> Any:
    """Run a coroutine even if called from code that's already inside an event
    loop (e.g. langtest(graph) called from an async function) — plain
    asyncio.run() raises in that case, so fall back to running it on a
    dedicated thread with its own loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: list[Any] = []
    error: list[BaseException] = []

    def _run() -> None:
        try:
            result.append(asyncio.run(coro))
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return result[0]
