"""FastAPI dependencies (Milestone 13)."""

from __future__ import annotations

from app.db.base import Database, default_database


def get_db() -> Database:
    """Provide the process-wide default database to route handlers."""
    return default_database()
