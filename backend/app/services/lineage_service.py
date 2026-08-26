"""Lineage + idempotent persistence (Milestone 15 / NT-5).

Implements the NT-5 guarantees on the persistence layer:

* **detect-before-commit** — a record is validated *before* any row is written; an invalid record raises
  :class:`GuardrailViolation` and **nothing is persisted** (the transactional session rolls back);
* **idempotent replay** — :func:`idempotent_get_or_create` keys a row by a deterministic value and returns
  the existing row on replay (no duplicate, same result);
* **complete lineage** — :func:`record_lineage` writes a queryable provenance chain (artifact + inputs +
  parent), idempotent by a content-derived ``lineage_id``.

Reuses the M13 :class:`Database` and the shared ``stable_hash``. Standard-library + SQLAlchemy.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from app.core.exceptions import GuardrailViolation
from app.db.base import Database
from app.db.models import LineageRow
from app.utils.hashing import stable_hash


def idempotent_get_or_create(
    db: Database,
    *,
    model: type,
    key_field: str,
    key_value: str,
    build: Callable[[], Any],
    validate: Callable[[], None] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Validate (before commit), then get-or-create a row keyed by ``key_field == key_value``.

    Returns ``(row_dict, created)``. On replay (same key) the existing row is returned unchanged and
    ``created`` is ``False`` — idempotent. If ``validate`` raises, **no row is written** (detect-before-commit).
    """
    if validate is not None:
        validate()  # runs BEFORE any DB write; raising here leaves the DB untouched
    with db.session() as s:
        existing = s.query(model).filter(getattr(model, key_field) == key_value).one_or_none()
        if existing is not None:
            return existing.to_dict(), False
        row = build()
        s.add(row)
        s.flush()
        return row.to_dict(), True


def lineage_id_for(artifact_type: str, content_hash: str, parent_lineage_id: str | None = None) -> str:
    """Deterministic lineage id (idempotent across replays)."""
    return "lin-" + stable_hash({"t": artifact_type, "h": content_hash, "p": parent_lineage_id or ""})[:16]


def record_lineage(
    db: Database,
    *,
    artifact_type: str,
    content_hash: str,
    artifact_ref: str = "",
    parent_lineage_id: str | None = None,
    inputs: dict[str, Any] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Record (idempotently) one lineage node and return it."""
    lid = lineage_id_for(artifact_type, content_hash, parent_lineage_id)

    def _validate() -> None:
        if not artifact_type:
            raise GuardrailViolation("lineage record rejected before commit: artifact_type is required.")
        if not content_hash:
            raise GuardrailViolation("lineage record rejected before commit: content_hash is required.")
        if parent_lineage_id:  # referential integrity: the parent must already exist
            with db.session() as s:
                if s.query(LineageRow).filter(LineageRow.lineage_id == parent_lineage_id).one_or_none() is None:
                    raise GuardrailViolation(
                        f"lineage record rejected before commit: parent {parent_lineage_id} does not exist.")

    row, _created = idempotent_get_or_create(
        db, model=LineageRow, key_field="lineage_id", key_value=lid, validate=_validate,
        build=lambda: LineageRow(
            lineage_id=lid, artifact_type=artifact_type, artifact_ref=artifact_ref,
            content_hash=content_hash, parent_lineage_id=parent_lineage_id,
            inputs=json.dumps(inputs or {}), notes=notes))
    return row


def list_lineage(db: Database, *, limit: int = 100) -> list[dict[str, Any]]:
    with db.session() as s:
        rows = s.query(LineageRow).order_by(LineageRow.created_at.desc()).limit(limit).all()
        return [r.to_dict() for r in rows]


def get_chain(db: Database, lineage_id: str) -> list[dict[str, Any]]:
    """Walk parent links from ``lineage_id`` back to the root — the complete provenance chain."""
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    current: str | None = lineage_id
    with db.session() as s:
        while current and current not in seen:
            seen.add(current)
            row = s.query(LineageRow).filter(LineageRow.lineage_id == current).one_or_none()
            if row is None:
                break
            chain.append(row.to_dict())
            current = row.parent_lineage_id
    return chain
