"""Typed evaluation records (Milestone 8).

Strongly-typed, deterministically-serialisable evaluation records. **Undefined metrics are represented
explicitly** (``MetricValue(value=None, defined=False, reason=…)``) — never silent zeros. No raw tensors
are stored. Standard-library only (imports the confusion matrix, which is numpy-guarded but plain data).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import (
    EVALUATION_VERSION,
    MODEL_VERSION,
    PREPROCESSING_VERSION,
)
from app.evaluation.confusion import ConfusionMatrix

# Canonical metric names.
METRIC_NAMES: tuple[str, ...] = ("iou", "dice", "precision", "recall", "f1")


@dataclass(frozen=True)
class MetricValue:
    """A single metric value, which may be explicitly undefined."""

    name: str
    value: float | None
    defined: bool
    reason: str = ""

    @classmethod
    def of(cls, name: str, value: float) -> "MetricValue":
        return cls(name=name, value=float(value), defined=True)

    @classmethod
    def undefined(cls, name: str, reason: str) -> "MetricValue":
        return cls(name=name, value=None, defined=False, reason=reason)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value, "defined": self.defined, "reason": self.reason}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MetricValue":
        return cls(name=str(data["name"]), value=data.get("value"),
                   defined=bool(data.get("defined", data.get("value") is not None)),
                   reason=str(data.get("reason", "")))


def _metrics_to_dict(metrics: dict[str, MetricValue]) -> dict[str, Any]:
    return {k: v.to_dict() for k, v in metrics.items()}


def _metrics_from_dict(data: dict[str, Any]) -> dict[str, MetricValue]:
    return {k: MetricValue.from_dict(v) for k, v in (data or {}).items()}


@dataclass
class ClassMetrics:
    """Per-class metrics + the counts they derive from."""

    class_index: int
    class_name: str
    tp: int
    fp: int
    fn: int
    tn: int
    support: int          # true pixels of this class (tp + fn)
    predicted: int        # pixels predicted as this class (tp + fp)
    metrics: dict[str, MetricValue] = field(default_factory=dict)

    def get(self, name: str) -> MetricValue:
        return self.metrics[name]

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_index": self.class_index, "class_name": self.class_name,
            "tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn,
            "support": self.support, "predicted": self.predicted,
            "metrics": _metrics_to_dict(self.metrics),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassMetrics":
        return cls(
            class_index=int(data["class_index"]), class_name=str(data["class_name"]),
            tp=int(data["tp"]), fp=int(data["fp"]), fn=int(data["fn"]), tn=int(data["tn"]),
            support=int(data["support"]), predicted=int(data["predicted"]),
            metrics=_metrics_from_dict(data.get("metrics", {})),
        )


@dataclass
class EvaluationResult:
    """Overall + per-class + aggregate metrics for one evaluation over given data."""

    num_classes: int
    class_names: list[str]
    ignore_index: int | None
    pixel_accuracy: MetricValue
    per_class: list[ClassMetrics]
    macro: dict[str, MetricValue]
    micro: dict[str, MetricValue]
    weighted: dict[str, MetricValue]
    confusion: ConfusionMatrix

    def class_metrics(self, class_name: str) -> ClassMetrics:
        for cm in self.per_class:
            if cm.class_name == class_name:
                return cm
        raise KeyError(class_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_classes": self.num_classes,
            "class_names": list(self.class_names),
            "ignore_index": self.ignore_index,
            "pixel_accuracy": self.pixel_accuracy.to_dict(),
            "per_class": [c.to_dict() for c in self.per_class],
            "macro": _metrics_to_dict(self.macro),
            "micro": _metrics_to_dict(self.micro),
            "weighted": _metrics_to_dict(self.weighted),
            "confusion": self.confusion.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationResult":
        return cls(
            num_classes=int(data["num_classes"]),
            class_names=list(data["class_names"]),
            ignore_index=data.get("ignore_index"),
            pixel_accuracy=MetricValue.from_dict(data["pixel_accuracy"]),
            per_class=[ClassMetrics.from_dict(c) for c in data["per_class"]],
            macro=_metrics_from_dict(data.get("macro", {})),
            micro=_metrics_from_dict(data.get("micro", {})),
            weighted=_metrics_from_dict(data.get("weighted", {})),
            confusion=ConfusionMatrix.from_dict(data["confusion"]),
        )


@dataclass
class StratifiedResult:
    """Overall result + per-class view (always) + optional per-group results."""

    overall: EvaluationResult
    by_class: dict[str, ClassMetrics] = field(default_factory=dict)
    by_group: dict[str, EvaluationResult] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall.to_dict(),
            "by_class": {k: v.to_dict() for k, v in self.by_class.items()},
            "by_group": {k: v.to_dict() for k, v in self.by_group.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StratifiedResult":
        return cls(
            overall=EvaluationResult.from_dict(data["overall"]),
            by_class={k: ClassMetrics.from_dict(v) for k, v in (data.get("by_class") or {}).items()},
            by_group={k: EvaluationResult.from_dict(v) for k, v in (data.get("by_group") or {}).items()},
        )


@dataclass
class EvaluationSummary:
    """Compact highlights — thin-cloud performance is always surfaced."""

    pixel_accuracy: float | None
    macro_iou: float | None
    macro_f1: float | None
    per_class_iou: dict[str, float | None]
    worst_class_by_iou: str | None
    thin_cloud_iou: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pixel_accuracy": self.pixel_accuracy,
            "macro_iou": self.macro_iou,
            "macro_f1": self.macro_f1,
            "per_class_iou": self.per_class_iou,
            "worst_class_by_iou": self.worst_class_by_iou,
            "thin_cloud_iou": self.thin_cloud_iou,
        }


@dataclass
class EvaluationRun:
    """Canonical top-level evaluation record."""

    config: dict[str, Any]
    result: EvaluationResult
    dataset: str
    split: str
    model_id: str
    model_version: str = MODEL_VERSION
    preprocessing_version: str = PREPROCESSING_VERSION
    evaluation_version: str = EVALUATION_VERSION
    config_hash: str = ""
    stratified: StratifiedResult | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config,
            "result": self.result.to_dict(),
            "stratified": self.stratified.to_dict() if self.stratified else None,
            "dataset": self.dataset,
            "split": self.split,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "preprocessing_version": self.preprocessing_version,
            "evaluation_version": self.evaluation_version,
            "config_hash": self.config_hash,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationRun":
        strat = data.get("stratified")
        return cls(
            config=dict(data.get("config", {}) or {}),
            result=EvaluationResult.from_dict(data["result"]),
            stratified=StratifiedResult.from_dict(strat) if strat else None,
            dataset=str(data.get("dataset", "")),
            split=str(data.get("split", "")),
            model_id=str(data.get("model_id", "")),
            model_version=str(data.get("model_version", MODEL_VERSION)),
            preprocessing_version=str(data.get("preprocessing_version", PREPROCESSING_VERSION)),
            evaluation_version=str(data.get("evaluation_version", EVALUATION_VERSION)),
            config_hash=str(data.get("config_hash", "")),
            timestamp=str(data.get("timestamp", "")),
            notes=str(data.get("notes", "")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "EvaluationRun":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "EvaluationRun":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
