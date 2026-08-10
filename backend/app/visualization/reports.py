"""Reusable statistical reporting (Milestone 5).

A generic, serialisable report model (:class:`Report` of typed :class:`ReportSection`) with export to
**JSON**, **CSV**, and **Markdown**, plus builders that assemble statistics into reports. Standard-library
only; deterministic given a fixed ``created_utc``.
"""

from __future__ import annotations

import csv
import enum
import io
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.constants import VISUALIZATION_VERSION
from app.visualization.inspection import DatasetInspectionReport
from app.visualization.statistics import (
    ClassDistribution,
    PatchStatistics,
    SplitStatistics,
)

logger = logging.getLogger(__name__)


class SectionKind(str, enum.Enum):
    TABLE = "table"
    KEYVALUE = "keyvalue"


@dataclass
class ReportSection:
    """A single report section: either a table (rows+columns) or key/value pairs."""

    title: str
    kind: str = SectionKind.KEYVALUE.value
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "kind": self.kind, "columns": self.columns,
                "rows": self.rows, "data": self.data}

    def to_markdown(self) -> str:
        lines = [f"## {self.title}", ""]
        if self.kind == SectionKind.TABLE.value:
            cols = self.columns or (list(self.rows[0].keys()) if self.rows else [])
            lines.append("| " + " | ".join(cols) + " |")
            lines.append("| " + " | ".join("---" for _ in cols) + " |")
            for row in self.rows:
                lines.append("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |")
        else:
            for key, value in self.data.items():
                lines.append(f"- **{key}**: {value}")
        lines.append("")
        return "\n".join(lines)


@dataclass
class Report:
    """A titled collection of sections with multi-format export."""

    title: str
    sections: list[ReportSection] = field(default_factory=list)
    created_utc: str = ""
    version: str = VISUALIZATION_VERSION

    def add(self, section: ReportSection) -> None:
        self.sections.append(section)

    # --- serialisation ----------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "created_utc": self.created_utc,
            "version": self.version,
            "sections": [s.to_dict() for s in self.sections],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        header = [f"# {self.title}", ""]
        if self.created_utc:
            header.append(f"_Generated: {self.created_utc} · v{self.version}_")
            header.append("")
        return "\n".join(header + [s.to_markdown() for s in self.sections])

    def to_csv(self) -> str:
        """Flatten all sections to a single CSV with a leading ``section`` column."""
        flat_rows: list[dict[str, Any]] = []
        for section in self.sections:
            if section.kind == SectionKind.TABLE.value:
                for row in section.rows:
                    flat_rows.append({"section": section.title, **row})
            else:
                for key, value in section.data.items():
                    flat_rows.append({"section": section.title, "key": key, "value": value})
        # Deterministic union of columns, preserving first-seen order.
        fieldnames: list[str] = []
        for row in flat_rows:
            for k in row:
                if k not in fieldnames:
                    fieldnames.append(k)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in flat_rows:
            writer.writerow(row)
        return buffer.getvalue()

    def save(self, path_stem: Path, formats: tuple[str, ...] = ("json", "md", "csv")) -> dict[str, Path]:
        """Write the report in the requested formats; returns {format: path}."""
        path_stem = Path(path_stem)
        path_stem.parent.mkdir(parents=True, exist_ok=True)
        renderers = {"json": self.to_json, "md": self.to_markdown, "csv": self.to_csv}
        written: dict[str, Path] = {}
        for fmt in formats:
            if fmt not in renderers:
                raise ValueError(f"Unsupported report format: {fmt}")
            out = path_stem.with_suffix(f".{fmt}")
            out.write_text(renderers[fmt](), encoding="utf-8")
            written[fmt] = out
        logger.info("Wrote report '%s' as %s", self.title, ", ".join(written))
        return written


# --------------------------------------------------------------------------------------------------
# Section / report builders.
# --------------------------------------------------------------------------------------------------

def class_frequency_section(dist: ClassDistribution) -> ReportSection:
    """A table of class -> count / frequency."""
    freqs = dist.frequencies()
    rows = [{"class": k, "count": v, "frequency": round(freqs[k], 6)}
            for k, v in sorted(dist.counts.items())]
    return ReportSection(title="Class frequency", kind=SectionKind.TABLE.value,
                         columns=["class", "count", "frequency"], rows=rows)


def build_dataset_report(inspection: DatasetInspectionReport, created_utc: str = "") -> Report:
    """Assemble a dataset EDA report from an inspection result."""
    report = Report(title=f"Dataset report: {inspection.dataset}", created_utc=created_utc)
    report.add(ReportSection(title="Dataset summary", data=inspection.statistics.to_dict()))
    report.add(ReportSection(title="Validation summary", data=inspection.validation_summary.to_dict()))
    if inspection.statistics.class_distribution is not None:
        report.add(class_frequency_section(inspection.statistics.class_distribution))
    if inspection.statistics.image_size_counts:
        rows = [{"size": s, "count": c} for s, c in inspection.statistics.image_size_counts.items()]
        report.add(ReportSection(title="Image sizes", kind=SectionKind.TABLE.value,
                                 columns=["size", "count"], rows=rows))
    return report


def build_patch_report(stats: PatchStatistics, created_utc: str = "") -> Report:
    report = Report(title="Patch report", created_utc=created_utc)
    report.add(ReportSection(title="Patch summary", data={
        "num_patches": stats.num_patches, "patch_size": stats.patch_size, "overlap": stats.overlap,
    }))
    report.add(ReportSection(title="Patches per split", kind=SectionKind.TABLE.value,
                             columns=["split", "count"],
                             rows=[{"split": k, "count": v} for k, v in stats.per_split.items()]))
    return report


def build_split_report(stats: SplitStatistics, created_utc: str = "") -> Report:
    report = Report(title="Split report", created_utc=created_utc)
    report.add(ReportSection(title="Split summary",
                             data={"seed": stats.seed, "grouped": stats.grouped}))
    report.add(ReportSection(title="Split counts", kind=SectionKind.TABLE.value,
                             columns=["split", "count", "ratio"],
                             rows=[{"split": k, "count": v, "ratio": stats.ratios.get(k)}
                                   for k, v in stats.counts.items()]))
    return report


def build_preprocessing_report(config_dict: dict[str, Any], created_utc: str = "") -> Report:
    """Assemble a preprocessing-configuration summary (from ``PreprocessingConfig.to_dict()``)."""
    report = Report(title="Preprocessing summary", created_utc=created_utc)
    flat = {k: v for k, v in config_dict.items() if k != "split_ratios"}
    report.add(ReportSection(title="Configuration", data=flat))
    ratios = config_dict.get("split_ratios", {})
    if ratios:
        report.add(ReportSection(title="Split ratios", kind=SectionKind.TABLE.value,
                                 columns=["split", "ratio"],
                                 rows=[{"split": k, "ratio": v} for k, v in ratios.items()]))
    return report
