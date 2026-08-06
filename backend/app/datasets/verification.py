"""Structured dataset verification (Milestone 3, revised).

Produces a machine-readable verification result per dataset (manifest / directory / checksum /
completeness / download status / overall) plus a human-readable summary table. Kept in the library
(not the CLI) so it is unit-testable without any network or real downloads.

Verification does **not** fail merely because a dataset has not been downloaded yet — that is reported as
``PENDING``. Failure is only asserted for genuine problems (missing expected files, checksum mismatch),
or, when ``require_present=True``, for a dataset that is still not present.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.datasets.integrity import check_paths_exist, directory_summary, verify_checksum
from app.datasets.manifest import DatasetRecord

logger = logging.getLogger(__name__)

# Status vocabulary (constants avoid magic strings).
MANIFEST_VALID = "VALID"
DIR_PRESENT = "PRESENT"
DIR_MISSING = "MISSING"
DL_DOWNLOADED = "DOWNLOADED"
DL_NOT_DOWNLOADED = "NOT_DOWNLOADED"
CK_VERIFIED = "VERIFIED"
CK_MISMATCH = "MISMATCH"
CK_UNAVAILABLE = "UNAVAILABLE"
CK_NA = "N/A"
COMP_COMPLETE = "COMPLETE"
COMP_INCOMPLETE = "INCOMPLETE"
COMP_UNKNOWN = "UNKNOWN"
COMP_NA = "N/A"
OVERALL_PASS = "PASS"
OVERALL_FAIL = "FAIL"
OVERALL_PENDING = "PENDING"


@dataclass
class DatasetVerification:
    """Structured verification result for a single dataset."""

    dataset_id: str
    manifest_status: str = MANIFEST_VALID
    directory_status: str = DIR_MISSING
    download_status: str = DL_NOT_DOWNLOADED
    checksum_status: str = CK_NA
    completeness: str = COMP_NA
    overall: str = OVERALL_PENDING
    details: list[str] = field(default_factory=list)


@dataclass
class VerificationReport:
    """Aggregate verification report over all datasets."""

    results: list[DatasetVerification] = field(default_factory=list)
    require_present: bool = False

    @property
    def passed(self) -> bool:
        """Overall pass/fail. PENDING passes unless ``require_present`` is set."""
        for r in self.results:
            if r.overall == OVERALL_FAIL:
                return False
            if r.overall == OVERALL_PENDING and self.require_present:
                return False
        return True


def verify_dataset(record: DatasetRecord, data_root: Path) -> DatasetVerification:
    """Verify one dataset against its expected directory and manifest metadata."""
    result = DatasetVerification(dataset_id=record.dataset_id)
    folder = (Path(data_root) / record.expected_directory).resolve()

    summary = directory_summary(folder)  # excludes README/.gitkeep scaffolding
    folder_exists = folder.is_dir()
    result.directory_status = DIR_PRESENT if folder_exists else DIR_MISSING

    if not summary["exists"] or summary["file_count"] == 0:
        result.download_status = DL_NOT_DOWNLOADED
        result.checksum_status = CK_NA
        result.completeness = COMP_NA
        result.overall = OVERALL_PENDING
        result.details.append(f"Expected folder {folder} has no dataset files yet.")
        return result

    # Data is present.
    result.download_status = DL_DOWNLOADED
    result.details.append(f"{summary['file_count']} file(s), {summary['total_bytes'] / (1024 * 1024):.2f} MiB")
    failed = False

    # Completeness (expected files).
    if record.expected_files:
        check = check_paths_exist(folder, record.expected_files)
        if check.missing:
            result.completeness = COMP_INCOMPLETE
            result.details.append("Missing: " + ", ".join(check.missing))
            failed = True
        else:
            result.completeness = COMP_COMPLETE
    else:
        result.completeness = COMP_UNKNOWN
        result.details.append("No expected_files recorded — completeness unknown.")

    # Checksum (when available).
    if record.checksum_available:
        target = folder / (record.expected_files[0] if record.expected_files else "")
        if target.is_file():
            if verify_checksum(target, record.checksum, record.checksum_algorithm):
                result.checksum_status = CK_VERIFIED
            else:
                result.checksum_status = CK_MISMATCH
                result.details.append(f"Checksum mismatch for {target.name}")
                failed = True
        else:
            result.checksum_status = CK_UNAVAILABLE
            result.details.append("Checksum recorded but target file not found.")
    else:
        result.checksum_status = CK_UNAVAILABLE
        result.details.append("No checksum recorded (placeholder) — integrity unverified.")

    result.overall = OVERALL_FAIL if failed else OVERALL_PASS
    return result


def verify_all(
    records: dict[str, DatasetRecord],
    data_root: Path,
    require_present: bool = False,
) -> VerificationReport:
    """Verify every dataset and return an aggregate report."""
    report = VerificationReport(require_present=require_present)
    for record in records.values():
        result = verify_dataset(record, data_root)
        if require_present and result.overall == OVERALL_PENDING:
            result.details.append("--require-present set: dataset must be downloaded.")
        report.results.append(result)
    return report


def render_table(report: VerificationReport) -> str:
    """Render a fixed-width, readable summary table of the verification report."""
    headers = ["Dataset", "Manifest", "Directory", "Download", "Checksum", "Complete", "Overall"]
    rows = [
        [
            r.dataset_id,
            r.manifest_status,
            r.directory_status,
            r.download_status,
            r.checksum_status,
            r.completeness,
            r.overall,
        ]
        for r in report.results
    ]
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i])
              for i in range(len(headers))]

    def fmt(cells: list[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    sep = "-+-".join("-" * w for w in widths)
    lines = [fmt(headers), sep]
    lines.extend(fmt(row) for row in rows)
    lines.append("")
    lines.append(f"Overall result: {'PASS' if report.passed else 'FAIL'}"
                 + (" (require_present)" if report.require_present else ""))
    return "\n".join(lines)
