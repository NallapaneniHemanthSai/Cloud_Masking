"""Training metadata dataclasses (Milestone 7).

Strongly-typed, serialisable training records — no weights, no evaluation metrics (metrics are optional
metadata only). Standard-library only; importable without PyTorch.
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TrainingState:
    """Mutable training progress state (dispatched to callbacks)."""

    epoch: int = 0
    global_step: int = 0
    monitor: str = "train_loss"
    best_metric: float | None = None
    best_epoch: int | None = None
    last_metrics: dict[str, float] = field(default_factory=dict)
    stop_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "global_step": self.global_step,
            "monitor": self.monitor,
            "best_metric": self.best_metric,
            "best_epoch": self.best_epoch,
            "last_metrics": self.last_metrics,
            "stop_requested": self.stop_requested,
        }


@dataclass
class CheckpointState:
    """Serialisable metadata for a saved checkpoint (optional eval metrics only)."""

    epoch: int
    global_step: int
    monitor: str = "train_loss"
    mode: str = "min"
    metric_value: float | None = None
    has_model_weights: bool = False
    has_optimizer_state: bool = False
    has_scheduler_state: bool = False
    training_version: str = TRAINING_VERSION
    config_hash: str = ""
    created_at: str = field(default_factory=_now)
    metrics: dict[str, float] = field(default_factory=dict)   # OPTIONAL metadata only
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "global_step": self.global_step,
            "monitor": self.monitor,
            "mode": self.mode,
            "metric_value": self.metric_value,
            "has_model_weights": self.has_model_weights,
            "has_optimizer_state": self.has_optimizer_state,
            "has_scheduler_state": self.has_scheduler_state,
            "training_version": self.training_version,
            "config_hash": self.config_hash,
            "created_at": self.created_at,
            "metrics": self.metrics,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckpointState":
        return cls(
            epoch=int(data["epoch"]),
            global_step=int(data.get("global_step", 0)),
            monitor=str(data.get("monitor", "train_loss")),
            mode=str(data.get("mode", "min")),
            metric_value=data.get("metric_value"),
            has_model_weights=bool(data.get("has_model_weights", False)),
            has_optimizer_state=bool(data.get("has_optimizer_state", False)),
            has_scheduler_state=bool(data.get("has_scheduler_state", False)),
            training_version=str(data.get("training_version", TRAINING_VERSION)),
            config_hash=str(data.get("config_hash", "")),
            created_at=str(data.get("created_at", "")),
            metrics=dict(data.get("metrics", {}) or {}),
            notes=str(data.get("notes", "")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "CheckpointState":
        return cls.from_dict(json.loads(text))


@dataclass
class TrainingMetadata:
    """Reproducibility metadata for a training run."""

    experiment_id: str
    training_version: str = TRAINING_VERSION
    model_version: str = MODEL_VERSION
    preprocessing_version: str = PREPROCESSING_VERSION
    visualization_version: str = VISUALIZATION_VERSION
    config_hash: str = ""
    seed: int = 0
    deterministic: bool = False
    device: str = "cpu"
    environment: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "training_version": self.training_version,
            "model_version": self.model_version,
            "preprocessing_version": self.preprocessing_version,
            "visualization_version": self.visualization_version,
            "config_hash": self.config_hash,
            "seed": self.seed,
            "deterministic": self.deterministic,
            "device": self.device,
            "environment": self.environment,
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingMetadata":
        return cls(
            experiment_id=str(data["experiment_id"]),
            training_version=str(data.get("training_version", TRAINING_VERSION)),
            model_version=str(data.get("model_version", MODEL_VERSION)),
            preprocessing_version=str(data.get("preprocessing_version", PREPROCESSING_VERSION)),
            visualization_version=str(data.get("visualization_version", VISUALIZATION_VERSION)),
            config_hash=str(data.get("config_hash", "")),
            seed=int(data.get("seed", 0)),
            deterministic=bool(data.get("deterministic", False)),
            device=str(data.get("device", "cpu")),
            environment=dict(data.get("environment", {}) or {}),
            created_at=str(data.get("created_at", "")),
            notes=str(data.get("notes", "")),
        )


@dataclass
class TrainerSummary:
    """Summary of a completed (or stopped) training run — no evaluation metrics."""

    experiment_id: str
    epochs_planned: int
    epochs_run: int
    best_metric: float | None = None
    best_epoch: int | None = None
    stopped_early: bool = False
    final_metrics: dict[str, float] = field(default_factory=dict)
    duration_seconds: float = 0.0
    config_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "epochs_planned": self.epochs_planned,
            "epochs_run": self.epochs_run,
            "best_metric": self.best_metric,
            "best_epoch": self.best_epoch,
            "stopped_early": self.stopped_early,
            "final_metrics": self.final_metrics,
            "duration_seconds": self.duration_seconds,
            "config_hash": self.config_hash,
        }
