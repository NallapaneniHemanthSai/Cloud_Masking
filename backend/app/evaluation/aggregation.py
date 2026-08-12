"""Metric aggregation (Milestone 8).

Macro / micro / weighted aggregation from per-class metrics and confusion counts. Standard-library only.

* **Macro** — unweighted mean over **defined** classes only (undefined excluded; count recorded). Every
  class counts equally, so a rare class (e.g. thin cloud) cannot be hidden by a dominant class.
* **Micro** — computed from **globally summed** TP/FP/FN (ratio of sums, not mean of ratios).
* **Weighted** — mean weighted by per-class support (true-pixel count); absent classes get zero weight.
"""

from __future__ import annotations

from app.evaluation.confusion import ConfusionMatrix
from app.evaluation.metrics import (
    dice_from_counts,
    f1_from_precision_recall,
    iou_from_counts,
    precision_from_counts,
    recall_from_counts,
)
from app.evaluation.records import METRIC_NAMES, ClassMetrics, MetricValue


def macro_average(per_class: list[ClassMetrics], metric_name: str) -> MetricValue:
    """Unweighted mean over classes where ``metric_name`` is defined."""
    values = [cm.metrics[metric_name] for cm in per_class]
    defined = [v.value for v in values if v.defined and v.value is not None]
    name = f"macro_{metric_name}"
    if not defined:
        return MetricValue.undefined(name, "no classes with a defined value")
    return MetricValue(name=name, value=sum(defined) / len(defined), defined=True,
                       reason=f"{len(defined)}/{len(values)} classes included")


def weighted_average(per_class: list[ClassMetrics], metric_name: str) -> MetricValue:
    """Support-weighted mean over classes where ``metric_name`` is defined."""
    pairs = [(cm.metrics[metric_name].value, cm.support) for cm in per_class
             if cm.metrics[metric_name].defined and cm.metrics[metric_name].value is not None]
    total_weight = sum(w for _, w in pairs)
    name = f"weighted_{metric_name}"
    if total_weight == 0:
        return MetricValue.undefined(name, "total support of defined classes is zero")
    return MetricValue(name=name, value=sum(v * w for v, w in pairs) / total_weight, defined=True,
                       reason=f"weighted by support over {len(pairs)} classes")


def micro_metrics(confusion: ConfusionMatrix) -> dict[str, MetricValue]:
    """Metrics from globally summed TP/FP/FN across all classes."""
    sum_tp = sum(confusion.tp(c) for c in range(confusion.num_classes))
    sum_fp = sum(confusion.fp(c) for c in range(confusion.num_classes))
    sum_fn = sum(confusion.fn(c) for c in range(confusion.num_classes))
    precision = precision_from_counts(sum_tp, sum_fp)
    recall = recall_from_counts(sum_tp, sum_fn)
    out = {
        "iou": iou_from_counts(sum_tp, sum_fp, sum_fn),
        "dice": dice_from_counts(sum_tp, sum_fp, sum_fn),
        "precision": precision,
        "recall": recall,
        "f1": f1_from_precision_recall(precision, recall),
    }
    # Rename with a micro_ prefix for clarity in reports.
    return {k: MetricValue(name=f"micro_{k}", value=v.value, defined=v.defined, reason=v.reason)
            for k, v in out.items()}


def compute_aggregates(per_class: list[ClassMetrics],
                       confusion: ConfusionMatrix) -> dict[str, dict[str, MetricValue]]:
    """Return ``{"macro": {...}, "micro": {...}, "weighted": {...}}`` over all metric names."""
    macro = {name: macro_average(per_class, name) for name in METRIC_NAMES}
    weighted = {name: weighted_average(per_class, name) for name in METRIC_NAMES}
    micro = micro_metrics(confusion)
    return {"macro": macro, "micro": micro, "weighted": weighted}
