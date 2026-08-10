"""Model artifact metadata (Milestone 6, revised).

:class:`ModelArtifact` is the canonical, strongly-typed metadata object describing a saved model — it holds
**no weights**, only metadata. It links a model to the preprocessing/visualization/model/dataset versions
and its checkpoint metadata, with deterministic content hashing and JSON serialization/save/load.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import (
    MODEL_VERSION,
    PREPROCESSING_VERSION,
    VISUALIZATION_VERSION,
)
from app.models.metadata import CheckpointMetadata
from app.utils.hashing import stable_hash


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ModelArtifact:
    """Canonical metadata for a saved model (no weights)."""

    artifact_id: str
    model_id: str
    architecture: str
    model_version: str = MODEL_VERSION
    preprocessing_version: str = PREPROCESSING_VERSION
    visualization_version: str = VISUALIZATION_VERSION
    dataset_version: str = ""
    checkpoint_metadata: CheckpointMetadata | None = None
    config_hash: str = ""
    created_at: str = field(default_factory=_now)
    notes: str = ""

    # --- deterministic content hashing ------------------------------------------------------------
    def _identity(self) -> dict[str, Any]:
        """Identity-defining fields (excludes ``artifact_id``, ``created_at``, ``notes``)."""
        return {
            "model_id": self.model_id,
            "architecture": self.architecture,
            "model_version": self.model_version,
            "preprocessing_version": self.preprocessing_version,
            "visualization_version": self.visualization_version,
            "dataset_version": self.dataset_version,
            "config_hash": self.config_hash,
            "checkpoint_config_hash": (
                self.checkpoint_metadata.config_hash if self.checkpoint_metadata else ""
            ),
        }

    def content_hash(self) -> str:
        """Deterministic hash of the identity fields (stable across time; ignores created_at/notes)."""
        return stable_hash(self._identity())

    # --- serialisation ----------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "model_id": self.model_id,
            "architecture": self.architecture,
            "model_version": self.model_version,
            "preprocessing_version": self.preprocessing_version,
            "visualization_version": self.visualization_version,
            "dataset_version": self.dataset_version,
            "checkpoint_metadata": (
                self.checkpoint_metadata.to_dict() if self.checkpoint_metadata else None
            ),
            "config_hash": self.config_hash,
            "created_at": self.created_at,
            "notes": self.notes,
            "content_hash": self.content_hash(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelArtifact":
        ckpt = data.get("checkpoint_metadata")
        return cls(
            artifact_id=str(data["artifact_id"]),
            model_id=str(data.get("model_id", "")),
            architecture=str(data.get("architecture", "")),
            model_version=str(data.get("model_version", MODEL_VERSION)),
            preprocessing_version=str(data.get("preprocessing_version", PREPROCESSING_VERSION)),
            visualization_version=str(data.get("visualization_version", VISUALIZATION_VERSION)),
            dataset_version=str(data.get("dataset_version", "")),
            checkpoint_metadata=CheckpointMetadata.from_dict(ckpt) if ckpt else None,
            config_hash=str(data.get("config_hash", "")),
            created_at=str(data.get("created_at", "")),
            notes=str(data.get("notes", "")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "ModelArtifact":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "ModelArtifact":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    # --- construction -----------------------------------------------------------------------------
    @classmethod
    def create(cls, *, model_id: str, architecture: str, config_hash: str,
               checkpoint_metadata: CheckpointMetadata | None = None, dataset_version: str = "",
               model_version: str = MODEL_VERSION, preprocessing_version: str = PREPROCESSING_VERSION,
               visualization_version: str = VISUALIZATION_VERSION,
               created_at: str | None = None, notes: str = "") -> "ModelArtifact":
        """Build an artifact, deriving ``artifact_id`` from the deterministic content hash."""
        artifact = cls(
            artifact_id="", model_id=model_id, architecture=architecture,
            model_version=model_version, preprocessing_version=preprocessing_version,
            visualization_version=visualization_version, dataset_version=dataset_version,
            checkpoint_metadata=checkpoint_metadata, config_hash=config_hash,
            created_at=created_at or _now(), notes=notes,
        )
        artifact.artifact_id = f"{architecture}-{artifact.content_hash()[:12]}"
        return artifact
