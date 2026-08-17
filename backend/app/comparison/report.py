"""Comparison reporting (Milestone 11).

Builds a controlled-comparison report (metadata, fairness controls, model-by-model metric table, thin-cloud
emphasis, compute comparison, failure-analysis comparison, decision, limitations) and exports it to
JSON/CSV/Markdown. Reuses the M5 :class:`Report` model — **no duplicated serialisation**. Every quantity
keeps its honest status label. Standard-library only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.comparison.records import ModelComparisonArtifact
from app.visualization.reports import Report, ReportSection, SectionKind


def _fmt(v: Any) -> Any:
    if v is None:
        return "undefined"
    if isinstance(v, float):
        return round(v, 6)
    return v


def _metadata_section(a: ModelComparisonArtifact) -> ReportSection:
    return ReportSection(title="Metadata", data={
        "comparison_id": a.comparison_id, "comparison_config_hash": a.comparison_config_hash,
        "fairness_hash": a.fairness_hash, "data_regime": a.data_regime,
        "comparison_version": a.comparison_version, "created_at": a.created_at,
        "content_hash": a.content_hash(),
        "seeds_intended": a.seeds_intended, "seeds_executed": a.seeds_executed,
        "decision": (a.decision or {}).get("outcome", "INCONCLUSIVE"),
    })


def _fairness_section(a: ModelComparisonArtifact) -> ReportSection:
    fr = a.fairness_report or {}
    rows = [{"field": c["field"], "matches": c["matches"]} for c in fr.get("compared", [])]
    section = ReportSection(title=f"Fairness controls (passed={fr.get('passed')})",
                            kind=SectionKind.TABLE.value, columns=["field", "matches"], rows=rows)
    return section


def _per_class_section(a: ModelComparisonArtifact) -> ReportSection:
    mc = a.metric_comparison or {}
    rows = []
    for c in mc.get("per_class", []):
        b, i, d = c.get("baseline", {}), c.get("improved", {}), c.get("delta", {})
        rows.append({
            "class": c["class_name"],
            "iou_baseline": _fmt(b.get("iou")), "iou_improved": _fmt(i.get("iou")),
            "iou_delta": _fmt(d.get("iou")),
            "dice_baseline": _fmt(b.get("dice")), "dice_improved": _fmt(i.get("dice")),
            "f1_baseline": _fmt(b.get("f1")), "f1_improved": _fmt(i.get("f1")),
        })
    return ReportSection(
        title="Model-by-model per-class metrics", kind=SectionKind.TABLE.value,
        columns=["class", "iou_baseline", "iou_improved", "iou_delta", "dice_baseline",
                 "dice_improved", "f1_baseline", "f1_improved"], rows=rows)


def _aggregate_section(a: ModelComparisonArtifact) -> ReportSection:
    mc = a.metric_comparison or {}
    b, i = mc.get("baseline_summary", {}), mc.get("improved_summary", {})
    rows = [
        {"metric": "macro_iou", "baseline": _fmt(b.get("macro_iou")),
         "improved": _fmt(i.get("macro_iou")), "delta": _fmt((mc.get("macro_delta") or {}).get("iou"))},
        {"metric": "macro_f1", "baseline": _fmt(b.get("macro_f1")), "improved": _fmt(i.get("macro_f1")),
         "delta": _fmt((mc.get("macro_delta") or {}).get("f1"))},
        {"metric": "pixel_accuracy", "baseline": _fmt(b.get("pixel_accuracy")),
         "improved": _fmt(i.get("pixel_accuracy")), "delta": "undefined"},
    ]
    return ReportSection(title=f"Aggregate metrics (status={mc.get('status')})",
                         kind=SectionKind.TABLE.value,
                         columns=["metric", "baseline", "improved", "delta"], rows=rows)


def _thin_cloud_section(a: ModelComparisonArtifact) -> ReportSection:
    t = (a.metric_comparison or {}).get("thin_cloud", {})
    return ReportSection(title="Thin-cloud comparison (PRIMARY)", data={
        "status": t.get("status"),
        "iou": f"{_fmt(t.get('baseline_iou'))} -> {_fmt(t.get('improved_iou'))} (Δ {_fmt(t.get('iou_delta'))})",
        "dice": f"{_fmt(t.get('baseline_dice'))} -> {_fmt(t.get('improved_dice'))} (Δ {_fmt(t.get('dice_delta'))})",
        "recall": f"{_fmt(t.get('baseline_recall'))} -> {_fmt(t.get('improved_recall'))} (Δ {_fmt(t.get('recall_delta'))})",
        "false_negatives": f"{_fmt(t.get('baseline_false_negatives'))} -> {_fmt(t.get('improved_false_negatives'))} (Δ {_fmt(t.get('false_negative_delta'))})",
        "regressed": t.get("regressed"),
    })


def _compute_section(a: ModelComparisonArtifact) -> ReportSection:
    cc = a.compute_comparison or {}
    b, i = cc.get("baseline", {}), cc.get("improved", {})
    rows = [
        {"dimension": "parameters", "baseline": b.get("parameter_count"),
         "improved": i.get("parameter_count"), "ratio": _fmt(cc.get("parameter_ratio"))},
        {"dimension": "total_training_seconds", "baseline": _fmt(b.get("total_training_seconds")),
         "improved": _fmt(i.get("total_training_seconds")),
         "ratio": _fmt(cc.get("training_time_ratio"))},
        {"dimension": "avg_epoch_seconds", "baseline": _fmt(b.get("avg_epoch_seconds")),
         "improved": _fmt(i.get("avg_epoch_seconds")), "ratio": "—"},
        {"dimension": "inference_seconds", "baseline": _fmt(b.get("inference_seconds")),
         "improved": _fmt(i.get("inference_seconds")), "ratio": _fmt(cc.get("inference_time_ratio"))},
        {"dimension": "peak_memory", "baseline": b.get("peak_memory"),
         "improved": i.get("peak_memory"), "ratio": "—"},
    ]
    return ReportSection(
        title=f"Compute comparison (status={cc.get('status')}, "
              f"device={b.get('device')}, batch={b.get('batch_size')})",
        kind=SectionKind.TABLE.value, columns=["dimension", "baseline", "improved", "ratio"], rows=rows)


def _failure_section(a: ModelComparisonArtifact) -> ReportSection:
    fc = a.failure_comparison or {}
    b, i = fc.get("baseline", {}), fc.get("improved", {})
    rows = []
    for key in ("total_failures", "thin_cloud_failures", "false_positives", "false_negatives",
                "class_confusion"):
        rows.append({"category": key, "baseline": b.get(key), "improved": i.get(key)})
    return ReportSection(
        title=f"Failure-analysis comparison (status={fc.get('status')}, "
              f"hypothesis_supported={fc.get('hypothesis_supported')})",
        kind=SectionKind.TABLE.value, columns=["category", "baseline", "improved"], rows=rows)


def _decision_section(a: ModelComparisonArtifact) -> ReportSection:
    d = a.decision or {}
    data: dict[str, Any] = {
        "outcome": d.get("outcome", "INCONCLUSIVE"),
        "thin_cloud_iou_delta": _fmt(d.get("thin_cloud_iou_delta")),
        "macro_iou_delta": _fmt(d.get("macro_iou_delta")),
        "uncertainty_status": d.get("uncertainty_status"),
        "data_regime": d.get("data_regime"), "seeds_executed": d.get("seeds_executed"),
    }
    for idx, line in enumerate(d.get("rationale", [])):
        data[f"rationale_{idx}"] = line
    return ReportSection(title="Decision", data=data)


def build_comparison_report(artifact: ModelComparisonArtifact) -> Report:
    """Assemble a comparison :class:`Report` from a :class:`ModelComparisonArtifact`."""
    report = Report(title=f"Controlled comparison: {artifact.comparison_id}",
                    created_utc=artifact.created_at)
    report.add(_metadata_section(artifact))
    report.add(_fairness_section(artifact))
    report.add(_per_class_section(artifact))
    report.add(_aggregate_section(artifact))
    report.add(_thin_cloud_section(artifact))
    report.add(_compute_section(artifact))
    report.add(_failure_section(artifact))
    report.add(_decision_section(artifact))
    report.add(ReportSection(title="Limitations",
                             data={f"note_{i}": line for i, line in enumerate(artifact.limitations)}))
    return report


def export_comparison_report(artifact: ModelComparisonArtifact, path_stem: Path,
                             formats: tuple[str, ...] = ("json", "csv", "md")) -> dict[str, Path]:
    """Build and write the comparison report in the requested formats."""
    return build_comparison_report(artifact).save(Path(path_stem), formats=formats)
