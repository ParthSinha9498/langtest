import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str | None
    port: int


def load_settings() -> Settings:
    return Settings(
        db_path=os.environ.get("LANGTEST_DB_PATH"),
        port=int(os.environ.get("LANGTEST_PORT", "8010")),
    )
