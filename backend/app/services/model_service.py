"""Model services: list architectures + register/list model versions (Milestone 13).

Reuses the M6 `ModelRegistry` (no duplication) for architecture metadata and persists registered model
versions to SQLite. Standard-library + SQLAlchemy; torch only needed to count parameters when registering.
"""

from __future__ import annotations

from typing import Any

from app.db.base import Database
from app.db.models import ModelVersionRow
from app.models.config import ModelConfig
from app.models.registry import default_registry


def list_architectures() -> list[dict[str, Any]]:
    """All registered architectures with their metadata (from the M6 registry)."""
    reg = default_registry()
    out: list[dict[str, Any]] = []
    for name in reg.list_models():
        meta = reg.metadata(name)
        out.append({
            "architecture": name, "version": meta.version, "description": meta.description,
            "aliases": reg.aliases(name), "improves_over": getattr(meta, "improves_over", ""),
            "supported_input_channels": list(getattr(meta, "supported_input_channels", [])),
            "supported_output_classes": list(getattr(meta, "supported_output_classes", [])),
        })
    return out


def list_registered(db: Database) -> list[dict[str, Any]]:
    """Model versions previously registered in the DB (newest first)."""
    with db.session() as s:
        rows = s.query(ModelVersionRow).order_by(ModelVersionRow.created_at.desc()).all()
        return [r.to_dict() for r in rows]


def register_version(db: Database, config: ModelConfig, *, notes: str = "") -> dict[str, Any]:
    """Register a model version (counts parameters via M6; requires torch) and persist it."""
    from app.models.factory import ModelFactory
    reg = default_registry()
    architecture = reg.resolve(config.name)
    version = reg.metadata(architecture).version
    param_count: int | None = None
    try:
        summary = ModelFactory().summary(config)
        param_count = summary.parameter_count
    except Exception:  # noqa: BLE001 - registration still valid without torch (param_count unknown)
        param_count = None
    model_id = f"{architecture}-{config.config_hash()[:8]}"
    with db.session() as s:
        row = ModelVersionRow(model_id=model_id, architecture=architecture, version=version,
                              config_hash=config.config_hash(), parameter_count=param_count, notes=notes)
        s.add(row)
        s.flush()
        return row.to_dict()
