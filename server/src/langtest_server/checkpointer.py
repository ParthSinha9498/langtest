from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException
from langgraph.checkpoint.sqlite import SqliteSaver

from langtest_server.settings import load_settings


@contextmanager
def open_checkpointer() -> Iterator[SqliteSaver]:
    settings = load_settings()
    if not settings.db_path:
        raise HTTPException(status_code=500, detail="LANGTEST_DB_PATH is not configured")
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(settings.db_path) as saver:
        yield saver
