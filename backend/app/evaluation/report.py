"""Evaluation reporting (Milestone 8).

Builds an evaluation report (model, dataset, split, overall/per-class/macro/micro metrics, confusion
matrix, stratified results, config hash, evaluation version, timestamp) and exports it to JSON/CSV/Markdown.
Reuses the existing ``app.visualization.reports.Report`` model — no duplicated serialisation logic.
Undefined metrics are shown explicitly as ``"undefined"``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.evaluation.records import EvaluationResult, EvaluationRun, MetricValue
from app.visualization.reports import Report, ReportSection, SectionKind


def _fmt(mv: MetricValue) -> Any:
    return round(mv.value, 6) if (mv.defined and mv.value is not None) else "undefined"


def _per_class_section(result: EvaluationResult) -> ReportSection:
    rows = [{
        "class": cm.class_name, "support": cm.support,
        "iou": _fmt(cm.metrics["iou"]), "dice": _fmt(cm.metrics["dice"]),
        "precision": _fmt(cm.metrics["precision"]), "recall": _fmt(cm.metrics["recall"]),
        "f1": _fmt(cm.metrics["f1"]),
    } for cm in result.per_class]
    return ReportSection(title="Per-class metrics", kind=SectionKind.TABLE.value,
                         columns=["class", "support", "iou", "dice", "precision", "recall", "f1"],
                         rows=rows)


def _aggregates_section(result: EvaluationResult) -> ReportSection:
    rows = []
    for agg_name, agg in (("macro", result.macro), ("micro", result.micro), ("weighted", result.weighted)):
        rows.append({
            "aggregate": agg_name,
            "iou": _fmt(agg["iou"]), "dice": _fmt(agg["dice"]),
            "precision": _fmt(agg["precision"]), "recall": _fmt(agg["recall"]), "f1": _fmt(agg["f1"]),
        })
    return ReportSection(title="Aggregate metrics", kind=SectionKind.TABLE.value,
                         columns=["aggregate", "iou", "dice", "precision", "recall", "f1"], rows=rows)


def _confusion_section(result: EvaluationResult) -> ReportSection:
    names = result.confusion.class_names or [f"class_{i}" for i in range(result.num_classes)]
    columns = ["true\\pred"] + list(names)
    rows = []
    for r, name in enumerate(names):
        row: dict[str, Any] = {"true\\pred": name}
        for c, cname in enumerate(names):
            row[cname] = result.confusion.matrix[r][c]
        rows.append(row)
    return ReportSection(title="Confusion matrix (rows=true, cols=pred)", kind=SectionKind.TABLE.value,
                         columns=columns, rows=rows)


def build_evaluation_report(run: EvaluationRun) -> Report:
    """Assemble an evaluation :class:`Report` from an :class:`EvaluationRun`."""
    result = run.result
    report = Report(title=f"Evaluation: {run.dataset}/{run.split}", created_utc=run.timestamp)
    report.add(ReportSection(title="Metadata", data={
        "model_id": run.model_id, "model_version": run.model_version, "dataset": run.dataset,
        "split": run.split, "evaluation_version": run.evaluation_version,
        "config_hash": run.config_hash, "timestamp": run.timestamp,
    }))
    report.add(ReportSection(title="Overall", data={
        "pixel_accuracy": _fmt(result.pixel_accuracy),
        "macro_iou": _fmt(result.macro["iou"]), "macro_f1": _fmt(result.macro["f1"]),
        "micro_f1": _fmt(result.micro["f1"]),
    }))
    report.add(_per_class_section(result))
    report.add(_aggregates_section(result))
    report.add(_confusion_section(result))

    if run.stratified is not None and run.stratified.by_group:
        rows = []
        for group, gres in run.stratified.by_group.items():
            rows.append({"group": group, "pixel_accuracy": _fmt(gres.pixel_accuracy),
                         "macro_iou": _fmt(gres.macro["iou"])})
        report.add(ReportSection(title="Stratified (by group)", kind=SectionKind.TABLE.value,
                                 columns=["group", "pixel_accuracy", "macro_iou"], rows=rows))
    return report


def export_evaluation_report(run: EvaluationRun, path_stem: Path,
                             formats: tuple[str, ...] = ("json", "csv", "md")) -> dict[str, Path]:
    """Build and write the evaluation report in the requested formats."""
    return build_evaluation_report(run).save(Path(path_stem), formats=formats)
