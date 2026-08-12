"""Failure-analysis reporting (Milestone 9).

Builds a failure report (analysis + evaluation versions, model/dataset/split, taxonomy + measurability,
failure counts, class + error-type summaries, top-K hard examples, limitations) and exports it to
JSON/CSV/Markdown. Reuses ``app.visualization.reports.Report`` — no duplicated serialisation. Explicitly
labels NOT MEASURABLE / DEFERRED / NOT YET MEASURED.
"""

from __future__ import annotations

from pathlib import Path

from app.failure_analysis.records import FailureAnalysisResult
from app.visualization.reports import Report, ReportSection, SectionKind


def _pixel_error_rows(result: FailureAnalysisResult) -> list[dict]:
    return [{
        "class": e.class_name, "error_type": e.error_type, "predicted": e.predicted_class,
        "error_count": e.error_count,
        "error_rate": round(e.error_rate, 6) if e.error_rate is not None else "undefined",
        "support": e.support, "severity": e.severity,
    } for e in result.pixel_errors]


def build_failure_report(result: FailureAnalysisResult) -> Report:
    """Assemble a failure :class:`Report` from a :class:`FailureAnalysisResult`."""
    report = Report(title=f"Failure analysis: {result.dataset}/{result.split}",
                    created_utc=result.timestamp)
    report.add(ReportSection(title="Metadata", data={
        "model_id": result.model_id, "dataset": result.dataset, "split": result.split,
        "analysis_version": result.analysis_version, "evaluation_version": result.evaluation_version,
        "config_hash": result.config_hash, "timestamp": result.timestamp,
    }))
    report.add(ReportSection(title="Failure taxonomy", kind=SectionKind.TABLE.value,
                             columns=["category", "measurability"], rows=result.taxonomy))
    report.add(ReportSection(title="Pixel-level errors", kind=SectionKind.TABLE.value,
                             columns=["class", "error_type", "predicted", "error_count", "error_rate",
                                      "support", "severity"],
                             rows=_pixel_error_rows(result)))
    report.add(ReportSection(title="Class summaries", kind=SectionKind.TABLE.value,
                             columns=["key", "total_errors", "sample_count", "error_rate"],
                             rows=[{"key": s.key, "total_errors": s.total_errors,
                                    "sample_count": s.sample_count,
                                    "error_rate": s.error_rate if s.error_rate is not None else "undefined"}
                                   for s in result.class_summaries]))
    report.add(ReportSection(title="Error-type summaries", kind=SectionKind.TABLE.value,
                             columns=["key", "total_errors", "sample_count"],
                             rows=[{"key": s.key, "total_errors": s.total_errors,
                                    "sample_count": s.sample_count} for s in result.error_type_summaries]))

    # Top-K hard examples (flattened across criteria).
    hard_rows = []
    for criterion, examples in result.hard_examples.items():
        for h in examples:
            hard_rows.append({"criterion": criterion, "rank": h.rank, "sample_id": h.sample_id,
                              "value": round(h.value, 6), "severity": h.severity})
    if hard_rows:
        report.add(ReportSection(title="Top-K hard examples", kind=SectionKind.TABLE.value,
                                 columns=["criterion", "rank", "sample_id", "value", "severity"],
                                 rows=hard_rows))

    report.add(ReportSection(title="Limitations", data={
        f"note_{i}": line for i, line in enumerate(result.limitations)}))
    return report


def export_failure_report(result: FailureAnalysisResult, path_stem: Path,
                          formats: tuple[str, ...] = ("json", "csv", "md")) -> dict[str, Path]:
    """Build and write the failure report in the requested formats."""
    return build_failure_report(result).save(Path(path_stem), formats=formats)
