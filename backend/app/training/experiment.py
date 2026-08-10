"""Experiment management (Milestone 7).

:class:`ExperimentRun` tracks a training run's configuration, checkpoints, logs, artifacts, and the
preprocessing/visualization/model/training versions, with serialization. Also lays out the experiment
directory structure defined in ADR-0007. Standard-library only.
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
    TRAINING_VERSION,
    VISUALIZATION_VERSION,
)
from app.training.config import TrainingConfig


def experiment_id_for(config: TrainingConfig) -> str:
    """Deterministic experiment id: ``<experiment_name>-<config_hash[:8]>``."""
    return f"{config.experiment_name}-{config.config_hash()[:8]}"


@dataclass
class ExperimentPaths:
    """Filesystem layout for one experiment (ADR-0007)."""

    root: Path
    config: Path
    run: Path
    checkpoints: Path
    logs: Path
    artifacts: Path

    def mkdirs(self) -> "ExperimentPaths":
        for d in (self.root, self.checkpoints, self.logs, self.artifacts):
            d.mkdir(parents=True, exist_ok=True)
        return self


def build_experiment_paths(base_dir: Path, experiment_id: str) -> ExperimentPaths:
    root = Path(base_dir) / experiment_id
    return ExperimentPaths(
        root=root, config=root / "config.json", run=root / "run.json",
        checkpoints=root / "checkpoints", logs=root / "logs", artifacts=root / "artifacts",
    )


@dataclass
class ExperimentRun:
    """Serialisable record of a training run and its outputs."""

    experiment_id: str
    name: str
    config: dict[str, Any] = field(default_factory=dict)
    training_metadata: dict[str, Any] = field(default_factory=dict)
    preprocessing_version: str = PREPROCESSING_VERSION
    visualization_version: str = VISUALIZATION_VERSION
    model_version: str = MODEL_VERSION
    training_version: str = TRAINING_VERSION
    checkpoints: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_checkpoint(self, path: Path | str) -> None:
        self.checkpoints.append(str(path))

    def add_log(self, path: Path | str) -> None:
        self.logs.append(str(path))

    def add_artifact(self, path: Path | str) -> None:
        self.artifacts.append(str(path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "config": self.config,
            "training_metadata": self.training_metadata,
            "preprocessing_version": self.preprocessing_version,
            "visualization_version": self.visualization_version,
            "model_version": self.model_version,
            "training_version": self.training_version,
            "checkpoints": self.checkpoints,
            "logs": self.logs,
            "artifacts": self.artifacts,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentRun":
        return cls(
            experiment_id=str(data["experiment_id"]),
            name=str(data.get("name", "")),
            config=dict(data.get("config", {}) or {}),
            training_metadata=dict(data.get("training_metadata", {}) or {}),
            preprocessing_version=str(data.get("preprocessing_version", PREPROCESSING_VERSION)),
            visualization_version=str(data.get("visualization_version", VISUALIZATION_VERSION)),
            model_version=str(data.get("model_version", MODEL_VERSION)),
            training_version=str(data.get("training_version", TRAINING_VERSION)),
            checkpoints=list(data.get("checkpoints", []) or []),
            logs=list(data.get("logs", []) or []),
            artifacts=list(data.get("artifacts", []) or []),
            created_at=str(data.get("created_at", "")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "ExperimentRun":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "ExperimentRun":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def create_experiment(config: TrainingConfig, base_dir: Path,
                      training_metadata: dict[str, Any] | None = None) -> tuple[ExperimentRun, ExperimentPaths]:
    """Create the experiment directory layout and an :class:`ExperimentRun`, writing ``config.json``."""
    experiment_id = experiment_id_for(config)
    paths = build_experiment_paths(base_dir, experiment_id).mkdirs()
    paths.config.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    run = ExperimentRun(
        experiment_id=experiment_id, name=config.experiment_name,
        config=config.to_dict(), training_metadata=training_metadata or {},
    )
    return run, paths
