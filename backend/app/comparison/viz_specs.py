"""Comparison visualization specs (Milestone 11).

Backend-independent :class:`FigureSpec`s for the baseline-vs-improved comparison, reusing the M5
visualization abstraction. **matplotlib is never imported here** — rendering stays behind the M5 backend
and remains optional. All specs are grouped bar charts (baseline vs improved series). Standard-library only.
"""

from __future__ import annotations

from typing import Any

from app.comparison.records import (
    ComputeComparison,
    FailureComparison,
    MetricComparison,
)
from app.visualization.records import FigureKind, FigureSpec


def _grouped_bar(title: str, labels: list[str], baseline: list[Any], improved: list[Any],
                 *, xlabel: str, ylabel: str, status: str) -> FigureSpec:
    """A backend-agnostic grouped bar chart: baseline vs improved series over shared labels."""
    return FigureSpec(
        kind=FigureKind.BAR.value, title=title,
        payload={"labels": labels, "series": {"baseline": baseline, "improved": improved}},
        options={"xlabel": xlabel, "ylabel": ylabel, "grouped": True,
                 "series_order": ["baseline", "improved"], "status": status},
    )


def metric_comparison_spec(metric: MetricComparison, *, aggregate: str = "macro",
                           key: str = "iou") -> FigureSpec:
    """Aggregate (macro/micro/weighted) metric for both arms."""
    base = metric.baseline_summary or {}
    impr = metric.improved_summary or {}
    field = f"{aggregate}_{key}"
    return _grouped_bar(
        f"Aggregate {aggregate} {key.upper()}", [f"{aggregate}_{key}"],
        [base.get(field)], [impr.get(field)],
        xlabel="metric", ylabel=key.upper(), status=metric.status)


def per_class_comparison_spec(metric: MetricComparison, *, key: str = "iou") -> FigureSpec:
    """Per-class metric (default IoU) for both arms — thin cloud is one of the bars."""
    labels = [c.class_name for c in metric.per_class]
    baseline = [c.baseline.get(key) for c in metric.per_class]
    improved = [c.improved.get(key) for c in metric.per_class]
    return _grouped_bar(f"Per-class {key.upper()}", labels, baseline, improved,
                        xlabel="class", ylabel=key.upper(), status=metric.status)


def thin_cloud_comparison_spec(metric: MetricComparison) -> FigureSpec:
    """PRIMARY thin-cloud comparison: IoU / Dice / Recall for both arms."""
    t = metric.thin_cloud
    return _grouped_bar(
        "Thin-cloud IoU / Dice / Recall", ["iou", "dice", "recall"],
        [t.baseline_iou, t.baseline_dice, t.baseline_recall],
        [t.improved_iou, t.improved_dice, t.improved_recall],
        xlabel="metric", ylabel="score", status=t.status)


def compute_vs_quality_spec(metric: MetricComparison, compute: ComputeComparison) -> FigureSpec:
    """Compute cost (parameters, training time) vs quality (thin-cloud IoU) for both arms."""
    t = metric.thin_cloud
    labels = ["parameters", "training_seconds", "thin_cloud_iou"]
    baseline = [compute.baseline.parameter_count, compute.baseline.total_training_seconds, t.baseline_iou]
    improved = [compute.improved.parameter_count, compute.improved.total_training_seconds, t.improved_iou]
    return _grouped_bar("Compute cost vs quality", labels, baseline, improved,
                        xlabel="dimension", ylabel="value (mixed units)", status=compute.status)


def failure_category_comparison_spec(failure: FailureComparison) -> FigureSpec:
    """Failure counts by category (FP / FN / class confusion / thin-cloud) for both arms."""
    labels = ["false_positives", "false_negatives", "class_confusion", "thin_cloud_failures"]
    baseline = [failure.baseline.false_positives, failure.baseline.false_negatives,
                failure.baseline.class_confusion, failure.baseline.thin_cloud_failures]
    improved = [failure.improved.false_positives, failure.improved.false_negatives,
                failure.improved.class_confusion, failure.improved.thin_cloud_failures]
    return _grouped_bar("Failure counts by category", labels, baseline, improved,
                        xlabel="category", ylabel="count", status=failure.status)


def comparison_viz_specs(metric: MetricComparison, failure: FailureComparison,
                         compute: ComputeComparison) -> dict[str, dict[str, Any]]:
    """All comparison specs as serialisable dicts (rendering optional, done by the M5 backend)."""
    return {
        "metric_comparison": metric_comparison_spec(metric).to_dict(),
        "per_class_comparison": per_class_comparison_spec(metric).to_dict(),
        "thin_cloud_comparison": thin_cloud_comparison_spec(metric).to_dict(),
        "compute_vs_quality": compute_vs_quality_spec(metric, compute).to_dict(),
        "failure_category_comparison": failure_category_comparison_spec(failure).to_dict(),
    }
