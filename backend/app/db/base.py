"""Database engine/session management (Milestone 13).

A thin, testable wrapper around SQLAlchemy 2.0 for the dev **SQLite** backend. The schema is written so a
later Postgres swap needs no domain-code change (ADR-0013). SQLAlchemy is a required M13 dependency and is
imported at module top — this module is **not** part of the bare-interpreter import contract (the
``app.db`` package ``__init__`` stays stdlib-clean).
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Database:
    """Owns one engine + session factory and creates the schema idempotently."""

    def __init__(self, url: str | None = None) -> None:
        self.url = url or get_settings().database_url
        connect_args = {"check_same_thread": False} if self.url.startswith("sqlite") else {}
        # Ensure the parent directory exists for a file-based sqlite URL.
        if self.url.startswith("sqlite:///") and ":memory:" not in self.url:
            db_path = Path(self.url.replace("sqlite:///", "", 1))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(self.url, connect_args=connect_args, future=True)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def create_all(self) -> "Database":
        # Import models so their tables are registered on Base.metadata before create_all.
        from app import db as _db_pkg  # noqa: F401
        from app.db import models as _models  # noqa: F401
        Base.metadata.create_all(self.engine)
        return self

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Transactional session scope: commit on success, rollback on error, always close."""
        s = self.session_factory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()


_DEFAULT: Database | None = None


def default_database() -> Database:
    """Process-wide default database (from settings). Created + schema-initialised on first use."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Database().create_all()
    return _DEFAULT


def reset_default_database(db: Database | None = None) -> None:
    """Override/reset the process default (used by tests to point at a temp SQLite file)."""
    global _DEFAULT
    _DEFAULT = db


def init_db() -> Database:
    """Initialise the default database schema (idempotent)."""
    return default_database()
