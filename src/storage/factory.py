# src/storage/factory.py
from __future__ import annotations
from typing import Optional
from src.storage.interfaces import RunRepository
from src.storage.inmem_repo import InMemoryRunRepository

def get_repository(db_url_or_path: Optional[str]) -> RunRepository | None:
    """
    Examples:
      None or "memory://" -> in-memory
      "sqlite:///data/solver.db" or "data/solver.db" -> SQLite
      (future) "postgresql://..." -> Postgres repo
      (future) "http://..." -> HTTP repo
    """
    if not db_url_or_path or db_url_or_path.startswith("memory://"):
        return InMemoryRunRepository()

    if db_url_or_path.startswith("sqlite:///"):
        path = db_url_or_path.replace("sqlite:///", "", 1)
    else:
        path = db_url_or_path  # bare path

    from src.storage.sqlite_repo import SQLiteRunRepository
    return SQLiteRunRepository(path)