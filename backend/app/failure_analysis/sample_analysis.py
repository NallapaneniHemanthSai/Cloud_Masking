"""Sample-level failure analysis (Milestone 9).

Computes a :class:`SampleFailure` per sample from its per-sample confusion matrix (reusing the M8
``ConfusionMatrix`` — no duplicated math). Requires per-sample predicted + target label arrays (numpy
guarded). Enforces **split isolation** — all samples must belong to the configured split (ADR-0009).
"""

from __future__ import annotations

from typing import Any, Iterable

from app.core.exceptions import FailureAnalysisError
from app.evaluation.confusion import ConfusionMatrix
from app.evaluation.runner import argmax_labels
from app.failure_analysis.config import FailureAnalysisConfig
from app.failure_analysis.records import SampleFailure
from app.failure_analysis.taxonomy import CLASS_FAILURE_CATEGORY, FailureCategory


def _dominant_offdiagonal(matrix: list[list[int]], k: int) -> tuple[int | None, int | None, int]:
    """Return ``(true_idx, pred_idx, count)`` for the largest off-diagonal cell (ties: lower indices)."""
    best = (None, None, 0)
    for r in range(k):
        for c in range(k):
            if r != c and matrix[r][c] > best[2]:
                best = (r, c, matrix[r][c])
    return best


def analyze_sample(config: FailureAnalysisConfig, sample_id: str, targets: Any, predictions: Any, *,
                   group: str = "", source_reference: str = "", is_logits: bool = False) -> SampleFailure:
    """Analyse a single sample into a :class:`SampleFailure`."""
    names = list(config.class_names) or [f"class_{i}" for i in range(config.params.get("num_classes", 0))]
    num_classes = len(names)
    cm = ConfusionMatrix.zeros(num_classes, names, config.ignore_index)
    if is_logits:
        predictions = argmax_labels(predictions, num_classes)
    cm.accumulate(targets, predictions)

    total = cm.total()
    errors = total - cm.diagonal_sum()
    rate = (errors / total) if total > 0 else 0.0
    per_class_errors = {names[c]: cm.fn(c) for c in range(num_classes) if cm.fn(c) > 0}

    ti, pi, _ = _dominant_offdiagonal(cm.matrix, num_classes)
    dom_true = names[ti] if ti is not None else ""
    dom_pred = names[pi] if pi is not None else ""

    categories: list[str] = []
    if errors > 0:
        categories = [FailureCategory.FALSE_POSITIVE.value, FailureCategory.FALSE_NEGATIVE.value,
                      FailureCategory.CLASS_CONFUSION.value]
        if config.mode == "multiclass":
            for name in per_class_errors:
                cat = CLASS_FAILURE_CATEGORY.get(name)
                if cat is not None:
                    categories.append(cat.value)

    return SampleFailure(
        sample_id=sample_id, dataset=config.dataset, split=config.split,
        total_pixels=total, error_count=errors, error_rate=rate, per_class_errors=per_class_errors,
        dominant_true_class=dom_true, dominant_predicted_class=dom_pred, categories=categories,
        severity=config.severity_thresholds.severity_for(rate).name, group=group,
        source_reference=source_reference, evaluation_version=config.evaluation_version,
        analysis_version=config.analysis_version, config_hash=config.config_hash())


def analyze_samples(config: FailureAnalysisConfig, samples: Iterable[dict[str, Any]], *,
                    is_logits: bool = False) -> list[SampleFailure]:
    """Analyse many samples. Each sample is a dict with keys: ``sample_id``, ``targets``,
    ``predictions`` (labels or logits), and optional ``group`` / ``split`` / ``source_reference``.

    Raises :class:`FailureAnalysisError` if a sample's split differs from the configured split
    (split isolation — never mix train/val/test).
    """
    results: list[SampleFailure] = []
    for sample in samples:
        split = sample.get("split", config.split)
        if config.split and split and split != config.split:
            raise FailureAnalysisError(
                f"Sample '{sample.get('sample_id')}' split {split!r} != configured split {config.split!r} "
                "(split isolation).")
        results.append(analyze_sample(
            config, str(sample["sample_id"]), sample["targets"], sample["predictions"],
            group=sample.get("group", ""), source_reference=sample.get("source_reference", ""),
            is_logits=is_logits))
    return results
