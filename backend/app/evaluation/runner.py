"""Evaluation runner (Milestone 8).

Consumes model predictions + targets, accumulates confusion statistics across batches, and computes the
overall/per-class/aggregate metrics **once from the totals** (ADR-0008 aggregation). Produces an
:class:`EvaluationResult` and the canonical :class:`EvaluationRun`. Does **not** modify the training engine
and contains no model/inference logic. numpy is only needed to convert logits → labels / accumulate arrays.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable

from app.core.exceptions import EvaluationError
from app.evaluation.aggregation import compute_aggregates
from app.evaluation.config import EvaluationConfig
from app.evaluation.confusion import ConfusionMatrix
from app.evaluation.metrics import compute_class_metrics, pixel_accuracy
from app.evaluation.records import EvaluationResult, EvaluationRun, StratifiedResult

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None  # type: ignore

logger = logging.getLogger(__name__)


def argmax_labels(logits: Any, num_classes: int) -> Any:
    """Convert logits/probabilities to class-index labels via argmax over the class axis."""
    if np is None:
        raise EvaluationError("numpy is required to argmax logits into labels.")
    arr = np.asarray(logits)
    class_axes = [ax for ax, size in enumerate(arr.shape) if size == num_classes]
    if not class_axes:
        raise EvaluationError(
            f"Could not locate a class axis of size {num_classes} in logits of shape {arr.shape}.")
    return arr.argmax(axis=class_axes[0])


def _copy_confusion(cm: ConfusionMatrix) -> ConfusionMatrix:
    return ConfusionMatrix(cm.num_classes, [row[:] for row in cm.matrix], list(cm.class_names),
                           cm.ignore_index)


def build_result(confusion: ConfusionMatrix, config: EvaluationConfig) -> EvaluationResult:
    """Compute an :class:`EvaluationResult` from an accumulated confusion matrix."""
    per_class = compute_class_metrics(confusion)
    aggregates = compute_aggregates(per_class, confusion)
    return EvaluationResult(
        num_classes=config.num_classes, class_names=list(config.class_names),
        ignore_index=config.ignore_index, pixel_accuracy=pixel_accuracy(confusion),
        per_class=per_class, macro=aggregates["macro"], micro=aggregates["micro"],
        weighted=aggregates["weighted"], confusion=_copy_confusion(confusion))


class EvaluationRunner:
    """Accumulates confusion statistics and computes evaluation results (deterministic)."""

    def __init__(self, config: EvaluationConfig) -> None:
        self.config = config
        self.confusion = ConfusionMatrix.zeros(config.num_classes, config.class_names, config.ignore_index)

    def reset(self) -> "EvaluationRunner":
        self.confusion = ConfusionMatrix.zeros(
            self.config.num_classes, self.config.class_names, self.config.ignore_index)
        return self

    def update(self, targets: Any, predictions: Any, *, is_logits: bool = False) -> "EvaluationRunner":
        """Accumulate one batch. ``targets`` are label arrays; ``predictions`` are labels or logits."""
        if is_logits:
            predictions = argmax_labels(predictions, self.config.num_classes)
        self.confusion.accumulate(targets, predictions)
        return self

    def compute_result(self) -> EvaluationResult:
        return build_result(self.confusion, self.config)

    def run(self, batches: Iterable[tuple[Any, Any]], *, is_logits: bool = False) -> EvaluationResult:
        """Accumulate all ``(targets, predictions)`` batches and compute the result."""
        for targets, predictions in batches:
            self.update(targets, predictions, is_logits=is_logits)
        return self.compute_result()

    def build_run(self, result: EvaluationResult, *, stratified: StratifiedResult | None = None,
                  notes: str = "") -> EvaluationRun:
        """Wrap a result in the canonical :class:`EvaluationRun` with metadata."""
        return EvaluationRun(
            config=self.config.to_dict(), result=result, stratified=stratified,
            dataset=self.config.dataset, split=self.config.split, model_id=self.config.model_id,
            model_version=self.config.model_version,
            preprocessing_version=self.config.preprocessing_version,
            evaluation_version=self.config.evaluation_version,
            config_hash=self.config.config_hash(),
            timestamp=datetime.now(timezone.utc).isoformat(), notes=notes)
