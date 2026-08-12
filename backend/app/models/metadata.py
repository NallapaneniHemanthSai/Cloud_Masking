"""Model / checkpoint / experiment metadata (Milestone 6).

Strongly-typed, serialisable metadata records. No weights are saved and no metrics are recorded here —
this milestone provides the metadata *framework* only. Standard-library only; importable without PyTorch.
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ModelMetadata:
    """Descriptive + capability metadata for a registered architecture (no training state).

    Capability fields describe what the architecture supports. Empty lists mean "unconstrained"
    (e.g. an empty ``supported_input_channels`` means any positive channel count is accepted).
    """

    name: str
    architecture: str
    version: str = MODEL_VERSION
    description: str = ""
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    # --- capability metadata ----------------------------------------------------------------------
    supported_input_channels: list[int] = field(default_factory=list)
    supported_output_classes: list[int] = field(default_factory=list)
    minimum_patch_size: int = 0
    optional_dependencies: list[str] = field(default_factory=list)
    supported_normalization: list[str] = field(default_factory=list)
    supported_preprocessing_versions: list[str] = field(default_factory=list)
    # --- improvement metadata (why this architecture is expected to improve; M10) ----------------
    improvement_mechanism: list[str] = field(default_factory=list)
    improves_over: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "architecture": self.architecture,
            "version": self.version,
            "description": self.description,
            "tags": list(self.tags),
            "aliases": list(self.aliases),
            "supported_input_channels": list(self.supported_input_channels),
            "supported_output_classes": list(self.supported_output_classes),
            "minimum_patch_size": self.minimum_patch_size,
            "optional_dependencies": list(self.optional_dependencies),
            "supported_normalization": list(self.supported_normalization),
            "supported_preprocessing_versions": list(self.supported_preprocessing_versions),
            "improvement_mechanism": list(self.improvement_mechanism),
            "improves_over": self.improves_over,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelMetadata":
        return cls(
            name=str(data["name"]),
            architecture=str(data.get("architecture", data["name"])),
            version=str(data.get("version", MODEL_VERSION)),
            description=str(data.get("description", "")),
            tags=list(data.get("tags", []) or []),
            aliases=list(data.get("aliases", []) or []),
            supported_input_channels=list(data.get("supported_input_channels", []) or []),
            supported_output_classes=list(data.get("supported_output_classes", []) or []),
            minimum_patch_size=int(data.get("minimum_patch_size", 0)),
            optional_dependencies=list(data.get("optional_dependencies", []) or []),
            supported_normalization=list(data.get("supported_normalization", []) or []),
            supported_preprocessing_versions=list(data.get("supported_preprocessing_versions", []) or []),
            improvement_mechanism=list(data.get("improvement_mechanism", []) or []),
            improves_over=str(data.get("improves_over", "")),
        )


@dataclass
class CheckpointMetadata:
    """Metadata describing a model checkpoint (weights are NOT saved in this milestone)."""

    model_id: str
    architecture: str
    version: str = MODEL_VERSION
    preprocessing_version: str = PREPROCESSING_VERSION
    visualization_version: str = VISUALIZATION_VERSION
    created_at: str = field(default_factory=_now)
    config_hash: str = ""
    parameter_count: int = 0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "architecture": self.architecture,
            "version": self.version,
            "preprocessing_version": self.preprocessing_version,
            "visualization_version": self.visualization_version,
            "created_at": self.created_at,
            "config_hash": self.config_hash,
            "parameter_count": self.parameter_count,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckpointMetadata":
        return cls(
            model_id=str(data["model_id"]),
            architecture=str(data.get("architecture", "")),
            version=str(data.get("version", MODEL_VERSION)),
            preprocessing_version=str(data.get("preprocessing_version", PREPROCESSING_VERSION)),
            visualization_version=str(data.get("visualization_version", VISUALIZATION_VERSION)),
            created_at=str(data.get("created_at", "")),
            config_hash=str(data.get("config_hash", "")),
            parameter_count=int(data.get("parameter_count", 0)),
            notes=str(data.get("notes", "")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "CheckpointMetadata":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "CheckpointMetadata":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


@dataclass
class ExperimentMetadata:
    """Metadata linking a dataset + preprocessing + model config (no metrics in this milestone)."""

    experiment_id: str
    dataset: str
    preprocessing_version: str = PREPROCESSING_VERSION
    visualization_version: str = VISUALIZATION_VERSION
    model_version: str = MODEL_VERSION
    config_hash: str = ""
    checkpoint: CheckpointMetadata | None = None
    created_at: str = field(default_factory=_now)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "dataset": self.dataset,
            "preprocessing_version": self.preprocessing_version,
            "visualization_version": self.visualization_version,
            "model_version": self.model_version,
            "config_hash": self.config_hash,
            "checkpoint": self.checkpoint.to_dict() if self.checkpoint else None,
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentMetadata":
        ckpt = data.get("checkpoint")
        return cls(
            experiment_id=str(data["experiment_id"]),
            dataset=str(data.get("dataset", "")),
            preprocessing_version=str(data.get("preprocessing_version", PREPROCESSING_VERSION)),
            visualization_version=str(data.get("visualization_version", VISUALIZATION_VERSION)),
            model_version=str(data.get("model_version", MODEL_VERSION)),
            config_hash=str(data.get("config_hash", "")),
            checkpoint=CheckpointMetadata.from_dict(ckpt) if ckpt else None,
            created_at=str(data.get("created_at", "")),
            notes=str(data.get("notes", "")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "ExperimentMetadata":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "ExperimentMetadata":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
