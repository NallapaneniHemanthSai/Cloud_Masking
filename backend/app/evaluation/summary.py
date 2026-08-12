"""Evaluation summary (Milestone 8).

Compact highlights derived from an :class:`EvaluationResult`. Thin-cloud IoU is surfaced explicitly, and
the worst class by IoU is identified — so a strong overall score cannot conceal a weak class. Standard-
library only; undefined values remain ``None``.
"""

from __future__ import annotations

from app.core.constants import CloudClass
from app.evaluation.records import EvaluationResult, EvaluationSummary

_THIN_CLOUD_NAME = CloudClass.THIN_CLOUD.name.lower()


def build_summary(result: EvaluationResult) -> EvaluationSummary:
    """Build an :class:`EvaluationSummary` from a result."""
    per_class_iou: dict[str, float | None] = {
        cm.class_name: cm.metrics["iou"].value for cm in result.per_class
    }

    # Worst defined class by IoU (None if no class has a defined IoU).
    defined = [(name, value) for name, value in per_class_iou.items() if value is not None]
    worst = min(defined, key=lambda kv: kv[1])[0] if defined else None

    return EvaluationSummary(
        pixel_accuracy=result.pixel_accuracy.value,
        macro_iou=result.macro["iou"].value,
        macro_f1=result.macro["f1"].value,
        per_class_iou=per_class_iou,
        worst_class_by_iou=worst,
        thin_cloud_iou=per_class_iou.get(_THIN_CLOUD_NAME),
    )
