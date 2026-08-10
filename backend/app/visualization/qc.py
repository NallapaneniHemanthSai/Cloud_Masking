"""Quality-control reporting (Milestone 5).

Builds a structured, serialisable :class:`QualityControlReport` from a preprocessing
:class:`ValidationReport`, plus a human-readable Markdown rendering. Reuses preprocessing records — no
duplicated validation logic. Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.preprocessing.records import SEVERITY_WARNING, ValidationRecord
from app.preprocessing.validation import ValidationReport


@dataclass
class QualityControlReport:
    """Structured QC result for a dataset."""

    dataset: str
    missing_labels: int = 0
    corrupted_samples: int = 0
    invalid_dimensions: int = 0
    duplicate_identifiers: int = 0
    unsupported_files: int = 0
    warnings: list[str] = field(default_factory=list)
    records: list[ValidationRecord] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "passed": self.passed,
            "missing_labels": self.missing_labels,
            "corrupted_samples": self.corrupted_samples,
            "invalid_dimensions": self.invalid_dimensions,
            "duplicate_identifiers": self.duplicate_identifiers,
            "unsupported_files": self.unsupported_files,
            "warnings": self.warnings,
            "records": [r.to_dict() for r in self.records],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Quality-control report: {self.dataset}",
            "",
            f"**Result:** {'PASS' if self.passed else 'FAIL'}",
            "",
            "## Summary",
            "",
            "| check | count |",
            "| --- | --- |",
            f"| missing labels | {self.missing_labels} |",
            f"| corrupted samples | {self.corrupted_samples} |",
            f"| invalid dimensions | {self.invalid_dimensions} |",
            f"| duplicate identifiers | {self.duplicate_identifiers} |",
            f"| unsupported files | {self.unsupported_files} |",
            "",
        ]
        if self.warnings:
            lines.append("## Warnings")
            lines.append("")
            lines.extend(f"- {w}" for w in self.warnings)
            lines.append("")
        if self.records:
            lines.append("## Details")
            lines.append("")
            lines.append("| sample_id | category | severity | message |")
            lines.append("| --- | --- | --- | --- |")
            for r in self.records:
                lines.append(f"| {r.sample_id} | {r.category} | {r.severity} | {r.message} |")
            lines.append("")
        return "\n".join(lines)


def build_qc_report(
    dataset: str,
    validation_report: ValidationReport,
    *,
    extra_warnings: list[str] | None = None,
) -> QualityControlReport:
    """Build a :class:`QualityControlReport` from a validation report."""
    summary = validation_report.summary()
    warnings = list(extra_warnings or [])
    warnings.extend(
        f"{r.sample_id}: {r.message}" for r in validation_report.records
        if r.severity == SEVERITY_WARNING
    )
    return QualityControlReport(
        dataset=dataset,
        missing_labels=summary.missing_labels,
        corrupted_samples=summary.corrupted_files,
        invalid_dimensions=summary.inconsistent_dimensions,
        duplicate_identifiers=summary.duplicate_ids,
        unsupported_files=summary.unsupported_files,
        warnings=warnings,
        records=list(validation_report.records),
        passed=validation_report.ok,
    )
