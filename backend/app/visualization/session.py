"""Visualization session (Milestone 5, revised).

A top-level, strongly-typed object representing a single visualization execution — the primary object
returned by visualization workflows. Aggregates the dataset summary, generated figure manifests, generated
reports, and the QC report, with full serialization/export/import. Holds no plotting-library objects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import VISUALIZATION_VERSION
from app.visualization.inspection import DatasetInspectionReport
from app.visualization.manifest import FigureManifest, stable_hash


@dataclass
class ReportRef:
    """A reference to a generated report and the files it produced."""

    title: str
    files: dict[str, str] = field(default_factory=dict)   # format -> path

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "files": self.files}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportRef":
        return cls(title=str(data.get("title", "")), files=dict(data.get("files", {}) or {}))


@dataclass
class VisualizationSession:
    """One visualization execution and its outputs."""

    session_id: str
    timestamp: str
    output_dir: str
    visualization_version: str = VISUALIZATION_VERSION
    config_hash: str = ""
    dataset_summary: dict[str, Any] = field(default_factory=dict)
    figures: list[FigureManifest] = field(default_factory=list)
    reports: list[ReportRef] = field(default_factory=list)
    qc_report: dict[str, Any] | None = None

    def add_figure(self, manifest: FigureManifest) -> None:
        self.figures.append(manifest)

    def add_report(self, title: str, files: dict[str, Path] | dict[str, str]) -> None:
        self.reports.append(ReportRef(title=title, files={k: str(v) for k, v in files.items()}))

    # --- serialisation ----------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "output_dir": self.output_dir,
            "visualization_version": self.visualization_version,
            "config_hash": self.config_hash,
            "dataset_summary": self.dataset_summary,
            "figures": [f.to_dict() for f in self.figures],
            "reports": [r.to_dict() for r in self.reports],
            "qc_report": self.qc_report,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisualizationSession":
        return cls(
            session_id=str(data["session_id"]),
            timestamp=str(data.get("timestamp", "")),
            output_dir=str(data.get("output_dir", "")),
            visualization_version=str(data.get("visualization_version", VISUALIZATION_VERSION)),
            config_hash=str(data.get("config_hash", "")),
            dataset_summary=dict(data.get("dataset_summary", {}) or {}),
            figures=[FigureManifest.from_dict(f) for f in data.get("figures", [])],
            reports=[ReportRef.from_dict(r) for r in data.get("reports", [])],
            qc_report=data.get("qc_report"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "VisualizationSession":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        """Export the session to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "VisualizationSession":
        """Import a session from a JSON file."""
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def build_session(
    dataset: str,
    inspection: DatasetInspectionReport,
    *,
    output_dir: Path | str = ".",
    config: dict[str, Any] | None = None,
    qc_report: dict[str, Any] | None = None,
    session_id: str | None = None,
    timestamp: str | None = None,
) -> VisualizationSession:
    """Assemble a :class:`VisualizationSession` from an inspection result.

    The ``config_hash`` is a deterministic hash of ``config`` (defaults to the dataset id), so the same
    configuration yields the same hash. ``session_id`` defaults to ``<dataset>-<config_hash[:8]>``.
    Figures and reports are attached by the caller via :meth:`add_figure` / :meth:`add_report`.
    """
    config = config or {"dataset": dataset}
    config_hash = stable_hash(config)
    return VisualizationSession(
        session_id=session_id or f"{dataset}-{config_hash[:8]}",
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        output_dir=str(output_dir),
        config_hash=config_hash,
        dataset_summary=inspection.to_dict(),
        qc_report=qc_report,
    )
