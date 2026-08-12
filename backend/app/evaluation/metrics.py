"""Segmentation metrics (Milestone 8).

Per-class metrics computed from confusion counts (TP/FP/FN/TN). Pure standard-library integer/float math —
no numpy required. Undefined metrics (zero denominators / absent classes) are returned as explicit
:class:`MetricValue` with ``defined=False`` and a reason — **never misleading zeros** (ADR-0008).

Definitions (per class):
    IoU       = TP / (TP + FP + FN)
    Dice      = 2·TP / (2·TP + FP + FN)
    Precision = TP / (TP + FP)          undefined when no predicted positives
    Recall    = TP / (TP + FN)          undefined when the class is absent from ground truth
    F1        = 2·P·R / (P + R)          undefined when P or R is undefined (or P+R == 0)
Pixel accuracy (global) = Σ diag / Σ all.
"""

from __future__ import annotations

from app.evaluation.confusion import ConfusionMatrix
from app.evaluation.records import ClassMetrics, MetricValue

_ABSENT_BOTH = "class absent in both prediction and ground truth (0/0)"
_NO_PRED_POS = "no predicted positives for this class"
_ABSENT_GT = "class absent in ground truth"


def _ratio(name: str, numerator: float, denominator: float, reason: str) -> MetricValue:
    if denominator == 0:
        return MetricValue.undefined(name, reason)
    return MetricValue.of(name, numerator / denominator)


def iou_from_counts(tp: int, fp: int, fn: int) -> MetricValue:
    return _ratio("iou", tp, tp + fp + fn, _ABSENT_BOTH)


def dice_from_counts(tp: int, fp: int, fn: int) -> MetricValue:
    return _ratio("dice", 2 * tp, 2 * tp + fp + fn, _ABSENT_BOTH)


def precision_from_counts(tp: int, fp: int) -> MetricValue:
    return _ratio("precision", tp, tp + fp, _NO_PRED_POS)


def recall_from_counts(tp: int, fn: int) -> MetricValue:
    return _ratio("recall", tp, tp + fn, _ABSENT_GT)


def f1_from_precision_recall(precision: MetricValue, recall: MetricValue) -> MetricValue:
    if not precision.defined or not recall.defined:
        return MetricValue.undefined("f1", "precision or recall undefined")
    p, r = precision.value, recall.value
    if (p + r) == 0:
        return MetricValue.undefined("f1", "precision + recall == 0")
    return MetricValue.of("f1", 2 * p * r / (p + r))


def pixel_accuracy(confusion: ConfusionMatrix) -> MetricValue:
    total = confusion.total()
    return _ratio("pixel_accuracy", confusion.diagonal_sum(), total, "empty mask (no pixels)")


def class_metrics_for(confusion: ConfusionMatrix, c: int) -> ClassMetrics:
    """Compute :class:`ClassMetrics` for one class index."""
    tp, fp, fn, tn = confusion.tp(c), confusion.fp(c), confusion.fn(c), confusion.tn(c)
    precision = precision_from_counts(tp, fp)
    recall = recall_from_counts(tp, fn)
    metrics = {
        "iou": iou_from_counts(tp, fp, fn),
        "dice": dice_from_counts(tp, fp, fn),
        "precision": precision,
        "recall": recall,
        "f1": f1_from_precision_recall(precision, recall),
    }
    name = confusion.class_names[c] if c < len(confusion.class_names) else f"class_{c}"
    return ClassMetrics(class_index=c, class_name=name, tp=tp, fp=fp, fn=fn, tn=tn,
                        support=confusion.support(c), predicted=confusion.predicted(c), metrics=metrics)


def compute_class_metrics(confusion: ConfusionMatrix) -> list[ClassMetrics]:
    """Compute per-class metrics for every class (always all classes)."""
    return [class_metrics_for(confusion, c) for c in range(confusion.num_classes)]
