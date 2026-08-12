"""Failure analyzer (Milestone 9).

Orchestrates confusing-case analysis: pixel-level (from the M8 confusion matrix) + optional sample-level,
deterministic ranking, hard-example mining, stratified summaries, taxonomy + limitations — assembled into
the canonical :class:`FailureAnalysisResult`. Reuses M8 primitives; contains no metric recomputation and no
model/training/inference code.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable

from app.evaluation.confusion import ConfusionMatrix
from app.failure_analysis.config import FailureAnalysisConfig
from app.failure_analysis.pixel_analysis import analyze_pixels
from app.failure_analysis.ranking import rank_samples, top_k
from app.failure_analysis.records import FailureAnalysisResult, HardExample, SampleFailure
from app.failure_analysis.sample_analysis import analyze_samples
from app.failure_analysis.stratification import (
    class_summaries,
    error_type_summaries,
    group_summaries,
)
from app.failure_analysis.taxonomy import (
    CATEGORY_MEASURABILITY,
    FailureCategory,
    Measurability,
    taxonomy_table,
)

logger = logging.getLogger(__name__)

_THIN_CLOUD = "thin_cloud"


def _limitations(config: FailureAnalysisConfig, has_samples: bool) -> list[str]:
    lines = ["Real-data failure statistics: NOT YET MEASURED (synthetic inputs only)."]
    for category, measurability in CATEGORY_MEASURABILITY.items():
        if measurability == Measurability.DEFERRED:
            lines.append(f"{category.value}: DEFERRED (needs spatial mask analysis).")
        elif measurability == Measurability.NOT_MEASURABLE:
            lines.append(f"{category.value}: NOT MEASURABLE (needs predicted probabilities/confidence).")
    if not has_samples:
        lines.append("Sample-level analysis: not available (no per-sample predictions provided).")
    return lines


def analyze_failures(
    config: FailureAnalysisConfig,
    *,
    confusion: ConfusionMatrix | None = None,
    evaluation_result: Any | None = None,
    samples: Iterable[dict[str, Any]] | None = None,
    is_logits: bool = False,
) -> FailureAnalysisResult:
    """Run failure analysis and return a :class:`FailureAnalysisResult`.

    Args:
        config: Failure-analysis configuration.
        confusion: A confusion matrix (pixel-level source). Alternatively pass ``evaluation_result``.
        evaluation_result: An M8 ``EvaluationResult`` (its ``.confusion`` is used).
        samples: Optional per-sample dicts for sample-level analysis (see :func:`analyze_samples`).
        is_logits: Whether sample ``predictions`` are logits.
    """
    cm = confusion
    if cm is None and evaluation_result is not None:
        cm = evaluation_result.confusion

    pixel_errors = analyze_pixels(cm, config) if cm is not None else []

    sample_failures: list[SampleFailure] = []
    if samples is not None:
        # A zero-error sample is not a failure; only rank samples that actually failed.
        analyzed = [sf for sf in analyze_samples(config, samples, is_logits=is_logits)
                    if sf.error_count > 0]
        sample_failures = rank_samples(analyzed)

    hard_examples: dict[str, list[HardExample]] = {}
    if sample_failures:
        hard_examples["by_error_rate"] = top_k(sample_failures, config.top_k, criterion="error_rate")
        hard_examples["by_error_count"] = top_k(sample_failures, config.top_k, criterion="error_count")
        if config.mode == "multiclass":
            hard_examples["thin_cloud"] = top_k(sample_failures, config.top_k, class_name=_THIN_CLOUD)
        hard_examples["class_confusion"] = top_k(
            sample_failures, config.top_k, error_type=FailureCategory.CLASS_CONFUSION.value)

    return FailureAnalysisResult(
        config=config.to_dict(), dataset=config.dataset, split=config.split, model_id=config.model_id,
        taxonomy=taxonomy_table(), pixel_errors=pixel_errors, sample_failures=sample_failures,
        hard_examples=hard_examples,
        class_summaries=class_summaries(config, pixel_errors, sample_failures),
        error_type_summaries=error_type_summaries(pixel_errors, sample_failures),
        group_summaries=group_summaries(sample_failures),
        limitations=_limitations(config, bool(sample_failures)),
        analysis_version=config.analysis_version, evaluation_version=config.evaluation_version,
        config_hash=config.config_hash(),
        timestamp=datetime.now(timezone.utc).isoformat())
