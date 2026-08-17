"""Dataset availability check (Milestone 12).

Inspects the **local filesystem** (never the network) and reports, per dataset, whether it is
``PRESENT`` / ``PARTIAL`` / ``NOT_PRESENT`` — plus whether processed samples, metadata, manifest, and
recorded checksums exist. A README/.gitkeep is **not** data (the M3 ``directory_summary`` already excludes
those), so a documented-but-empty folder correctly reads as ``NOT_PRESENT``. Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.constants import DEFAULT_PROCESSED_DIRNAME
from app.datasets.integrity import check_paths_exist, directory_summary
from app.datasets.manifest import DatasetRecord

# Availability vocabulary.
PRESENT = "PRESENT"
PARTIAL = "PARTIAL"
NOT_PRESENT = "NOT_PRESENT"


@dataclass
class DatasetAvailability:
    """Availability of one dataset on the local filesystem."""

    dataset_id: str
    status: str
    expected_directory: str
    file_count: int = 0
    total_bytes: int = 0
    checksum_recorded: bool = False
    expected_files_complete: bool | None = None      # None = no expected_files recorded
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id, "status": self.status,
            "expected_directory": self.expected_directory, "file_count": self.file_count,
            "total_bytes": self.total_bytes, "checksum_recorded": self.checksum_recorded,
            "expected_files_complete": self.expected_files_complete, "notes": self.notes,
        }


@dataclass
class AvailabilityReport:
    """Aggregate availability across datasets + supporting artifacts."""

    datasets: list[DatasetAvailability] = field(default_factory=list)
    processed_present: bool = False
    metadata_present: bool = False
    manifest_present: bool = False
    checksums_present: bool = False

    def status_for(self, dataset_id: str) -> str:
        for d in self.datasets:
            if d.dataset_id == dataset_id:
                return d.status
        return NOT_PRESENT

    def to_dict(self) -> dict[str, Any]:
        return {
            "datasets": [d.to_dict() for d in self.datasets],
            "processed_present": self.processed_present, "metadata_present": self.metadata_present,
            "manifest_present": self.manifest_present, "checksums_present": self.checksums_present,
        }

    def render_table(self) -> str:
        lines = ["Dataset availability", "-" * 20]
        for d in self.datasets:
            lines.append(f"  {d.dataset_id:<14} {d.status:<12} files={d.file_count} "
                         f"checksum={'yes' if d.checksum_recorded else 'no'}")
        lines.append(f"  {'processed':<14} {'PRESENT' if self.processed_present else 'NOT_PRESENT'}")
        lines.append(f"  {'metadata':<14} {'PRESENT' if self.metadata_present else 'NOT_PRESENT'}")
        lines.append(f"  {'manifest':<14} {'PRESENT' if self.manifest_present else 'NOT_PRESENT'}")
        lines.append(f"  {'checksums':<14} {'PRESENT' if self.checksums_present else 'NOT_PRESENT'}")
        return "\n".join(lines)


def check_dataset_availability(record: DatasetRecord, data_root: Path) -> DatasetAvailability:
    """Availability of a single dataset from its manifest record + expected directory."""
    folder = Path(data_root) / record.expected_directory
    summary = directory_summary(folder)          # excludes README/.gitkeep
    file_count = int(summary["file_count"])
    checksum_recorded = record.checksum_available

    if file_count == 0:
        status, complete, note = NOT_PRESENT, None, "No dataset files present (not downloaded)."
    else:
        complete = None
        if record.expected_files:
            complete = check_paths_exist(folder, record.expected_files).ok
        if complete is False:
            status, note = PARTIAL, "Some expected files are missing."
        elif not checksum_recorded or complete is None:
            status = PARTIAL
            note = "Data present but not fully verifiable (no checksum and/or no expected-file list)."
        else:
            status, note = PRESENT, "Files present and complete."

    return DatasetAvailability(
        dataset_id=record.dataset_id, status=status, expected_directory=record.expected_directory,
        file_count=file_count, total_bytes=int(summary["total_bytes"]),
        checksum_recorded=checksum_recorded, expected_files_complete=complete, notes=note)


def check_availability(records: dict[str, DatasetRecord], data_root: Path, *,
                       metadata_dir: Path | None = None,
                       manifest_path: Path | None = None) -> AvailabilityReport:
    """Build the full availability report for all manifest datasets + supporting artifacts."""
    data_root = Path(data_root)
    report = AvailabilityReport()
    for record in records.values():
        report.datasets.append(check_dataset_availability(record, data_root))

    processed = data_root / DEFAULT_PROCESSED_DIRNAME
    report.processed_present = processed.is_dir() and directory_summary(processed)["file_count"] > 0
    if metadata_dir is not None:
        report.metadata_present = Path(metadata_dir).is_dir() and any(Path(metadata_dir).glob("*.md"))
    if manifest_path is not None:
        report.manifest_present = Path(manifest_path).is_file()
    report.checksums_present = any(d.checksum_recorded for d in report.datasets)
    return report
