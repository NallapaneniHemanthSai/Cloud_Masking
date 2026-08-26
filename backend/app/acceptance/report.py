"""Acceptance reporting (Milestone 16 / D5).

Renders an :class:`AcceptanceReport` to JSON/CSV/Markdown, reusing the M5 :class:`Report` model — no
duplicated serialisation. Every NT row is fully explainable. Standard-library only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.acceptance.records import AcceptanceReport
from app.visualization.reports import Report, ReportSection, SectionKind


def build_acceptance_report(report: AcceptanceReport) -> Report:
    r = Report(title="Acceptance harness (D5)", created_utc=report.created_at)
    r.add(ReportSection(title="Overall", data={
        "overall": report.overall, "safety_passed": report.safety_passed,
        "kpi_acceptance": report.kpi_overall, "failed_nts": report.failed_nts() or "none",
        "acceptance_version": report.acceptance_version, "content_hash": report.content_hash(),
    }))

    nt_rows: list[dict[str, Any]] = []
    for nt in report.nt_results:
        nt_rows.append({
            "nt": nt.nt_id, "name": nt.name, "owner": nt.owner, "passed": nt.passed,
            "pass_fixture_fired": nt.pass_case.triggered, "fail_fixture_fired": nt.fail_case.triggered,
            "action_on_fail": nt.fail_case.action,
        })
    r.add(ReportSection(title="Negative tests (NT-1..NT-5)", kind=SectionKind.TABLE.value,
                        columns=["nt", "name", "owner", "passed", "pass_fixture_fired",
                                 "fail_fixture_fired", "action_on_fail"], rows=nt_rows))

    r.add(ReportSection(title="AC coverage", kind=SectionKind.TABLE.value,
                        columns=["ac", "description", "covered_by", "status"],
                        rows=[{k: a.get(k, "") for k in ("ac", "description", "covered_by", "status")}
                              for a in report.ac_coverage]))

    r.add(ReportSection(title="KPI status", kind=SectionKind.TABLE.value,
                        columns=["kpi", "status", "note"],
                        rows=[{k: kp.get(k, "") for k in ("kpi", "status", "note")}
                              for kp in report.kpi_status]))

    r.add(ReportSection(title="Coverage / test inventory", data={
        "line_coverage_percent": report.coverage.get("line_coverage_percent"),
        "line_coverage_note": report.coverage.get("line_coverage_note", ""),
        **{f"harness::{k}": v for k, v in (report.coverage.get("manual_harness_counts", {}) or {}).items()},
    }))
    return r


def export_acceptance_report(report: AcceptanceReport, path_stem: Path,
                             formats: tuple[str, ...] = ("json", "csv", "md")) -> dict[str, Path]:
    """Write the D5 report: canonical JSON (from the record) + CSV/MD (from the M5 Report)."""
    path_stem = Path(path_stem)
    written: dict[str, Path] = {}
    if "json" in formats:
        written["json"] = report.save_json(path_stem.with_suffix(".json"))
    md_formats = tuple(f for f in formats if f in ("csv", "md"))
    if md_formats:
        written.update(build_acceptance_report(report).save(path_stem, formats=md_formats))
    return written
