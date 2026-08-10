"""Training artifact metadata (Milestone 7, revised).

:class:`TrainingArtifact` is the canonical, strongly-typed metadata object representing **one completed
training execution**. It aggregates the experiment run, model artifact, training metadata, checkpoint
state, config hash, and environment capture — **no evaluation metrics, inference outputs, or deployment
metadata**. Deterministic content hashing + JSON serialization/save/load (export/import).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import TRAINING_VERSION
from app.utils.hashing import stable_hash


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_dict(obj: Any) -> dict[str, Any] | None:
    """Normalise a typed metadata object (or dict / None) to a plain dict."""
    if obj is None:
        return None
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return dict(obj)


@dataclass
class TrainingArtifact:
    """Canonical metadata for one completed training execution (no metrics/inference/deploy)."""

    artifact_id: str
    experiment_run: dict[str, Any]
    training_metadata: dict[str, Any]
    training_config_hash: str
    environment_capture: dict[str, Any] = field(default_factory=dict)
    model_artifact: dict[str, Any] | None = None
    checkpoint_state: dict[str, Any] | None = None
    training_version: str = TRAINING_VERSION
    created_at: str = field(default_factory=_now)
    notes: str = ""

    # --- deterministic content hashing ------------------------------------------------------------
    def _identity(self) -> dict[str, Any]:
        """Identity-defining fields (excludes ``artifact_id``, ``created_at``, ``notes``)."""
        return {
            "experiment_id": (self.experiment_run or {}).get("experiment_id", ""),
            "training_config_hash": self.training_config_hash,
            "model_content_hash": (self.model_artifact or {}).get("content_hash", ""),
            "checkpoint_config_hash": (self.checkpoint_state or {}).get("config_hash", ""),
            "checkpoint_epoch": (self.checkpoint_state or {}).get("epoch", ""),
        }

    def content_hash(self) -> str:
        """Deterministic hash of identity fields (stable across time; ignores created_at/notes)."""
        return stable_hash(self._identity())

    # --- serialisation ----------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "experiment_run": self.experiment_run,
            "training_metadata": self.training_metadata,
            "training_config_hash": self.training_config_hash,
            "environment_capture": self.environment_capture,
            "model_artifact": self.model_artifact,
            "checkpoint_state": self.checkpoint_state,
            "training_version": self.training_version,
            "created_at": self.created_at,
            "notes": self.notes,
            "content_hash": self.content_hash(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingArtifact":
        return cls(
            artifact_id=str(data["artifact_id"]),
            experiment_run=dict(data.get("experiment_run", {}) or {}),
            training_metadata=dict(data.get("training_metadata", {}) or {}),
            training_config_hash=str(data.get("training_config_hash", "")),
            environment_capture=dict(data.get("environment_capture", {}) or {}),
            model_artifact=data.get("model_artifact"),
            checkpoint_state=data.get("checkpoint_state"),
            training_version=str(data.get("training_version", TRAINING_VERSION)),
            created_at=str(data.get("created_at", "")),
            notes=str(data.get("notes", "")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "TrainingArtifact":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "TrainingArtifact":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    # --- construction -----------------------------------------------------------------------------
    @classmethod
    def create(cls, *, experiment_run: Any, training_metadata: Any, training_config_hash: str,
               environment_capture: dict[str, Any] | None = None, model_artifact: Any = None,
               checkpoint_state: Any = None, created_at: str | None = None,
               notes: str = "") -> "TrainingArtifact":
        """Assemble an artifact from typed objects (or dicts), deriving ``artifact_id`` from its hash."""
        artifact = cls(
            artifact_id="",
            experiment_run=_as_dict(experiment_run) or {},
            training_metadata=_as_dict(training_metadata) or {},
            training_config_hash=training_config_hash,
            environment_capture=dict(environment_capture or {}),
            model_artifact=_as_dict(model_artifact),
            checkpoint_state=_as_dict(checkpoint_state),
            created_at=created_at or _now(), notes=notes,
        )
        artifact.artifact_id = f"train-{artifact.content_hash()[:12]}"
        return artifact
