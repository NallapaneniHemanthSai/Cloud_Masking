"""Stratified evaluation (Milestone 8).

Always produces an **Overall** result plus a **per-class view** (Clear / Thick / Thin / Cloud Shadow —
thin cloud always visible), and optional breakdowns by **sample group** (dataset/split/region/season).
**Haze is not a class** — it is approximated under thin cloud (Charter §3.1). Standard-library only.
"""

from __future__ import annotations

from typing import Any, Iterable

from app.evaluation.config import EvaluationConfig
from app.evaluation.confusion import ConfusionMatrix
from app.evaluation.records import ClassMetrics, EvaluationResult, StratifiedResult
from app.evaluation.runner import EvaluationRunner, build_result


def class_view(result: EvaluationResult) -> dict[str, ClassMetrics]:
    """Map each class name to its :class:`ClassMetrics` (per-class visibility)."""
    return {cm.class_name: cm for cm in result.per_class}


def stratified_evaluation(
    config: EvaluationConfig,
    grouped_batches: Iterable[tuple[Any, Any, str]],
    *,
    is_logits: bool = False,
) -> StratifiedResult:
    """Evaluate overall and per group.

    Args:
        config: Evaluation configuration.
        grouped_batches: Iterable of ``(targets, predictions, group)`` — batches tagged with a stratum key.
        is_logits: Whether ``predictions`` are logits (argmax applied).

    Returns:
        A :class:`StratifiedResult` (overall + per-class view + per-group results).
    """
    overall = EvaluationRunner(config)
    per_group: dict[str, EvaluationRunner] = {}
    for targets, predictions, group in grouped_batches:
        overall.update(targets, predictions, is_logits=is_logits)
        runner = per_group.setdefault(group, EvaluationRunner(config))
        runner.update(targets, predictions, is_logits=is_logits)

    overall_result = overall.compute_result()
    return StratifiedResult(
        overall=overall_result,
        by_class=class_view(overall_result),
        by_group={group: runner.compute_result() for group, runner in sorted(per_group.items())},
    )


def stratified_from_confusions(config: EvaluationConfig,
                               group_confusions: dict[str, ConfusionMatrix]) -> StratifiedResult:
    """Build a stratified result from pre-accumulated per-group confusion matrices (deterministic)."""
    overall_cm = ConfusionMatrix.zeros(config.num_classes, config.class_names, config.ignore_index)
    for cm in group_confusions.values():
        overall_cm = overall_cm.add(cm)
    overall_result = build_result(overall_cm, config)
    return StratifiedResult(
        overall=overall_result,
        by_class=class_view(overall_result),
        by_group={g: build_result(cm, config) for g, cm in sorted(group_confusions.items())},
    )
