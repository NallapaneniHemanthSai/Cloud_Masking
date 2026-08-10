"""Figure manifest (Milestone 5, revised).

A strongly-typed, serialisable record of the metadata for a single generated figure. Never holds a
plotting-library object — only the figure's descriptive metadata and output file paths. Supports JSON
serialization/deserialization and file export/import.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import VISUALIZATION_VERSION
from app.visualization.records import FigureSpec, RenderResult

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def stable_hash(obj: Any) -> str:
    """Return a deterministic sha256 hex digest of a JSON-serialisable object.

    Keys are sorted and separators normalised so equal content always yields the same hash, regardless
    of insertion order. Non-JSON values fall back to ``str``.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _slug(text: str) -> str:
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-") or "figure"


@dataclass
class FigureManifest:
    """Metadata describing one generated figure (no plotting objects)."""

    figure_id: str
    title: str
    figure_type: str
    backend: str
    created_at: str
    visualization_version: str = VISUALIZATION_VERSION
    config_hash: str = ""
    input_source: str | None = None
    output_files: list[str] = field(default_factory=list)
    notes: str = ""

    # --- serialisation ----------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "figure_id": self.figure_id,
            "title": self.title,
            "figure_type": self.figure_type,
            "backend": self.backend,
            "created_at": self.created_at,
            "visualization_version": self.visualization_version,
            "config_hash": self.config_hash,
            "input_source": self.input_source,
            "output_files": self.output_files,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FigureManifest":
        return cls(
            figure_id=str(data["figure_id"]),
            title=str(data.get("title", "")),
            figure_type=str(data.get("figure_type", "")),
            backend=str(data.get("backend", "")),
            created_at=str(data.get("created_at", "")),
            visualization_version=str(data.get("visualization_version", VISUALIZATION_VERSION)),
            config_hash=str(data.get("config_hash", "")),
            input_source=data.get("input_source"),
            output_files=list(data.get("output_files", []) or []),
            notes=str(data.get("notes", "")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "FigureManifest":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        """Export the manifest to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "FigureManifest":
        """Import a manifest from a JSON file."""
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    # --- construction from a render result --------------------------------------------------------
    @classmethod
    def from_render(cls, spec: FigureSpec, result: RenderResult, *,
                    figure_id: str | None = None, created_at: str | None = None,
                    notes: str = "") -> "FigureManifest":
        """Build a manifest from a :class:`FigureSpec` and its :class:`RenderResult`.

        The ``config_hash`` is a deterministic hash of the spec; ``figure_id`` (if not provided) is derived
        from the title + config hash, so the same figure yields a stable id.
        """
        config_hash = stable_hash(spec.to_dict())
        fid = figure_id or f"{_slug(spec.title)}-{config_hash[:8]}"
        input_source = spec.payload.get("source_image") or spec.payload.get("mask_source")
        outputs = [p for p in (result.output_path, result.sidecar_path) if p]
        created = created_at or datetime.now(timezone.utc).isoformat()
        return cls(
            figure_id=fid, title=spec.title, figure_type=spec.kind, backend=result.backend,
            created_at=created, config_hash=config_hash, input_source=input_source,
            output_files=outputs, notes=notes,
        )
