"""Evaluation configuration (Milestone 8).

Strongly-typed, validated, serialisable evaluation configuration with a deterministic config hash.
Standard-library only. Binary and multiclass are **separate modes** (never mixed — ADR-0008).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from app.core.constants import (
    EVALUATION_VERSION,
    MODEL_VERSION,
    PREPROCESSING_VERSION,
    CloudClass,
    OnCloudNLabel,
)
from app.core.exceptions import ConfigurationError
from app.utils.hashing import stable_hash

# Verified class names (M3): CloudSEN12 multiclass and On Cloud N binary.
CLOUDSEN12_CLASS_NAMES: tuple[str, ...] = (
    CloudClass.CLEAR.name.lower(), CloudClass.THICK_CLOUD.name.lower(),
    CloudClass.THIN_CLOUD.name.lower(), CloudClass.CLOUD_SHADOW.name.lower(),
)
ON_CLOUD_N_CLASS_NAMES: tuple[str, ...] = (
    OnCloudNLabel.NO_CLOUD.name.lower(), OnCloudNLabel.CLOUD.name.lower(),
)


class EvaluationMode(str, enum.Enum):
    """Evaluation modes — binary and multiclass are never mixed."""

    BINARY = "binary"
    MULTICLASS = "multiclass"


@dataclass(frozen=True)
class EvaluationConfig:
    """Validated evaluation configuration."""

    mode: str = EvaluationMode.MULTICLASS.value
    num_classes: int = 4
    class_names: tuple[str, ...] = CLOUDSEN12_CLASS_NAMES
    ignore_index: int | None = None
    dataset: str = ""
    split: str = ""
    model_id: str = ""
    model_version: str = MODEL_VERSION
    preprocessing_version: str = PREPROCESSING_VERSION
    evaluation_version: str = EVALUATION_VERSION
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.num_classes < 2:
            raise ConfigurationError(f"num_classes must be >= 2, got {self.num_classes}.")
        if len(self.class_names) != self.num_classes:
            raise ConfigurationError(
                f"class_names ({len(self.class_names)}) must match num_classes ({self.num_classes}).")
        if self.mode not in {m.value for m in EvaluationMode}:
            raise ConfigurationError(f"Unknown evaluation mode {self.mode!r}.")
        if self.mode == EvaluationMode.BINARY.value and self.num_classes != 2:
            raise ConfigurationError("Binary mode requires num_classes == 2.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "num_classes": self.num_classes,
            "class_names": list(self.class_names),
            "ignore_index": self.ignore_index,
            "dataset": self.dataset,
            "split": self.split,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "preprocessing_version": self.preprocessing_version,
            "evaluation_version": self.evaluation_version,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationConfig":
        data = dict(data or {})
        names = data.get("class_names")
        return cls(
            mode=data.get("mode", EvaluationMode.MULTICLASS.value),
            num_classes=int(data.get("num_classes", 4)),
            class_names=tuple(names) if names else CLOUDSEN12_CLASS_NAMES,
            ignore_index=data.get("ignore_index"),
            dataset=data.get("dataset", ""),
            split=data.get("split", ""),
            model_id=data.get("model_id", ""),
            model_version=data.get("model_version", MODEL_VERSION),
            preprocessing_version=data.get("preprocessing_version", PREPROCESSING_VERSION),
            evaluation_version=data.get("evaluation_version", EVALUATION_VERSION),
            params=dict(data.get("params", {}) or {}),
        )

    def config_hash(self) -> str:
        """Deterministic hash of the configuration."""
        return stable_hash(self.to_dict())

    # --- factories --------------------------------------------------------------------------------
    @classmethod
    def cloudsen12(cls, *, split: str = "", model_id: str = "", ignore_index: int | None = None,
                   **kwargs: Any) -> "EvaluationConfig":
        """Multiclass CloudSEN12 config (clear / thick / thin / shadow)."""
        return cls(mode=EvaluationMode.MULTICLASS.value, num_classes=4,
                   class_names=CLOUDSEN12_CLASS_NAMES, ignore_index=ignore_index,
                   dataset="cloudsen12", split=split, model_id=model_id, **kwargs)

    @classmethod
    def on_cloud_n(cls, *, split: str = "", model_id: str = "", ignore_index: int | None = None,
                   **kwargs: Any) -> "EvaluationConfig":
        """Binary On Cloud N config (non_cloud / cloud)."""
        return cls(mode=EvaluationMode.BINARY.value, num_classes=2,
                   class_names=ON_CLOUD_N_CLASS_NAMES, ignore_index=ignore_index,
                   dataset="on_cloud_n", split=split, model_id=model_id, **kwargs)
