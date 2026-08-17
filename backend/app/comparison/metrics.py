"""Quality comparison (Milestone 11).

Compares two **already-computed** M8 :class:`EvaluationResult`s — it never recomputes metrics. Produces
per-class deltas, aggregate (macro/micro/weighted) deltas, the worst class per arm, and the PRIMARY
thin-cloud comparison (IoU/Dice/Recall + false-negatives). Thin-cloud degradation can therefore never be
hidden by a stronger aggregate. Standard-library only.
"""

from __future__ import annotations

from app.comparison.records import (
    NOT_YET_MEASURED,
    ClassMetricDelta,
    MetricComparison,
    ThinCloudComparison,
    _delta,
)
from app.core.constants import CloudClass
from app.evaluation.records import ClassMetrics, EvaluationResult
from app.evaluation.summary import build_summary

_METRIC_KEYS = ("iou", "dice", "precision", "recall", "f1")
_THIN_CLOUD = CloudClass.THIN_CLOUD.name.lower()


def _metric_dict(cm: ClassMetrics) -> dict[str, float | None]:
    """Extract the standard metric values from a per-class record (undefined -> None)."""
    out: dict[str, float | None] = {}
    for key in _METRIC_KEYS:
        mv = cm.metrics.get(key)
        out[key] = mv.value if (mv is not None and mv.defined) else None
    return out


def _agg_dict(agg: dict) -> dict[str, float | None]:
    return {k: (agg[k].value if (k in agg and agg[k].defined) else None) for k in _METRIC_KEYS}


def _agg_delta(base: dict, impr: dict) -> dict[str, float | None]:
    b, i = _agg_dict(base), _agg_dict(impr)
    return {k: _delta(b[k], i[k]) for k in _METRIC_KEYS}


def _find_class(result: EvaluationResult, name: str) -> ClassMetrics | None:
    for cm in result.per_class:
        if cm.class_name == name:
            return cm
    return None


def extract_thin_cloud(baseline: EvaluationResult, improved: EvaluationResult, *,
                       status: str = NOT_YET_MEASURED) -> ThinCloudComparison:
    """Build the thin-cloud comparison (IoU/Dice/Recall + false-negatives) from two results."""
    b = _find_class(baseline, _THIN_CLOUD)
    i = _find_class(improved, _THIN_CLOUD)
    if b is None or i is None:
        return ThinCloudComparison(status=status)
    bm, im = _metric_dict(b), _metric_dict(i)
    iou_delta = _delta(bm["iou"], im["iou"])
    dice_delta = _delta(bm["dice"], im["dice"])
    regressed = None
    if iou_delta is not None or dice_delta is not None:
        regressed = ((iou_delta is not None and iou_delta < 0)
                     or (dice_delta is not None and dice_delta < 0))
    return ThinCloudComparison(
        baseline_iou=bm["iou"], improved_iou=im["iou"], iou_delta=iou_delta,
        baseline_dice=bm["dice"], improved_dice=im["dice"], dice_delta=dice_delta,
        baseline_recall=bm["recall"], improved_recall=im["recall"],
        recall_delta=_delta(bm["recall"], im["recall"]),
        baseline_false_negatives=b.fn, improved_false_negatives=i.fn,
        false_negative_delta=(i.fn - b.fn), regressed=regressed, status=status)


def compare_metrics(baseline: EvaluationResult, improved: EvaluationResult, *,
                    status: str = NOT_YET_MEASURED) -> MetricComparison:
    """Compare two evaluation results into a :class:`MetricComparison` (per-class + aggregate + thin)."""
    base_summary = build_summary(baseline)
    impr_summary = build_summary(improved)

    per_class: list[ClassMetricDelta] = []
    improved_by_name = {cm.class_name: cm for cm in improved.per_class}
    for b in baseline.per_class:
        i = improved_by_name.get(b.class_name)
        bm = _metric_dict(b)
        im = _metric_dict(i) if i is not None else {k: None for k in _METRIC_KEYS}
        per_class.append(ClassMetricDelta(
            class_name=b.class_name, baseline=bm, improved=im,
            delta={k: _delta(bm[k], im[k]) for k in _METRIC_KEYS}))

    return MetricComparison(
        baseline_summary=base_summary.to_dict(), improved_summary=impr_summary.to_dict(),
        per_class=per_class,
        macro_delta=_agg_delta(baseline.macro, improved.macro),
        micro_delta=_agg_delta(baseline.micro, improved.micro),
        weighted_delta=_agg_delta(baseline.weighted, improved.weighted),
        thin_cloud=extract_thin_cloud(baseline, improved, status=status),
        worst_class_baseline=base_summary.worst_class_by_iou,
        worst_class_improved=impr_summary.worst_class_by_iou,
        status=status)
