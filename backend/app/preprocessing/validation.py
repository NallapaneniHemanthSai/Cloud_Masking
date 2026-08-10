"""Dataset validation (Milestone 4, revised).

Produces a **structured** validation report over discovered samples, plus summary statistics and a
human-readable table. Checks:

* missing files, unsupported file types, missing labels,
* duplicate identifiers,
* inconsistent dimensions (optional; needs a metadata reader),
* corrupted metadata (optional).

Records are typed (:class:`app.preprocessing.records.ValidationRecord`). Dimension/metadata checks take an
injectable ``meta_reader`` so validation logic is unit-testable with synthetic readers and no file IO.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from app.core.constants import SUPPORTED_RASTER_EXTENSIONS
from app.preprocessing.records import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SampleRecord,
    ValidationRecord,
)
from app.preprocessing.raster_io import RasterMeta, read_raster_meta

logger = logging.getLogger(__name__)

# Issue categories.
MISSING_FILE = "missing_file"
MISSING_LABEL = "missing_label"
UNSUPPORTED_TYPE = "unsupported_type"
DUPLICATE_ID = "duplicate_id"
INCONSISTENT_DIMENSIONS = "inconsistent_dimensions"
CORRUPTED_METADATA = "corrupted_metadata"

MetaReader = Callable[[Path], RasterMeta]


@dataclass
class ValidationSummary:
    """Structured summary statistics for a validation run."""

    total_samples: int = 0
    valid_samples: int = 0
    invalid_samples: int = 0
    duplicate_ids: int = 0
    corrupted_files: int = 0
    missing_labels: int = 0
    missing_files: int = 0
    unsupported_files: int = 0
    inconsistent_dimensions: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "total_samples": self.total_samples,
            "valid_samples": self.valid_samples,
            "invalid_samples": self.invalid_samples,
            "duplicate_ids": self.duplicate_ids,
            "corrupted_files": self.corrupted_files,
            "missing_labels": self.missing_labels,
            "missing_files": self.missing_files,
            "unsupported_files": self.unsupported_files,
            "inconsistent_dimensions": self.inconsistent_dimensions,
        }


@dataclass
class ValidationReport:
    """Structured validation result (list of typed records + summary)."""

    records: list[ValidationRecord] = field(default_factory=list)
    samples_checked: int = 0

    def add(self, sample_id: str, category: str, message: str, severity: str = SEVERITY_ERROR) -> None:
        self.records.append(ValidationRecord(sample_id, category, message, severity))

    @property
    def errors(self) -> list[ValidationRecord]:
        return [r for r in self.records if r.severity == SEVERITY_ERROR]

    @property
    def ok(self) -> bool:
        """True when there are no ERROR-severity records."""
        return not self.errors

    def counts_by_category(self) -> dict[str, int]:
        return dict(Counter(r.category for r in self.records))

    def summary(self) -> ValidationSummary:
        """Compute structured summary statistics."""
        cats = self.counts_by_category()
        invalid_ids = {r.sample_id for r in self.errors}
        return ValidationSummary(
            total_samples=self.samples_checked,
            invalid_samples=len(invalid_ids),
            valid_samples=max(self.samples_checked - len(invalid_ids), 0),
            duplicate_ids=cats.get(DUPLICATE_ID, 0),
            corrupted_files=cats.get(CORRUPTED_METADATA, 0),
            missing_labels=cats.get(MISSING_LABEL, 0),
            missing_files=cats.get(MISSING_FILE, 0),
            unsupported_files=cats.get(UNSUPPORTED_TYPE, 0),
            inconsistent_dimensions=cats.get(INCONSISTENT_DIMENSIONS, 0),
        )

    def render_table(self) -> str:
        """Render a fixed-width, human-readable summary table."""
        s = self.summary()
        rows = [
            ("total samples", s.total_samples),
            ("valid samples", s.valid_samples),
            ("invalid samples", s.invalid_samples),
            ("duplicate ids", s.duplicate_ids),
            ("corrupted files", s.corrupted_files),
            ("missing labels", s.missing_labels),
            ("missing files", s.missing_files),
            ("unsupported files", s.unsupported_files),
            ("inconsistent dimensions", s.inconsistent_dimensions),
        ]
        label_w = max(len(name) for name, _ in rows)
        lines = ["Validation summary", "-" * (label_w + 8)]
        lines.extend(f"{name.ljust(label_w)} : {value}" for name, value in rows)
        lines.append(f"Result: {'PASS' if self.ok else 'FAIL'}")
        return "\n".join(lines)

    # Backwards-compatible short summary.
    def render(self) -> str:
        return self.render_table()


def validate_samples(
    samples: Iterable[SampleRecord],
    *,
    check_dimensions: bool = False,
    meta_reader: MetaReader = read_raster_meta,
    expected_bands: int | None = None,
) -> ValidationReport:
    """Validate a collection of samples and return a structured report.

    Args:
        samples: Discovered samples to validate.
        check_dimensions: If True, read metadata to check band/label size consistency (requires a working
            ``meta_reader`` / rasterio). If False (default), only path/type/id checks run.
        meta_reader: Callable returning :class:`RasterMeta` for a path (injectable for tests).
        expected_bands: If set, flag samples whose band count differs.

    Returns:
        A :class:`ValidationReport`.
    """
    report = ValidationReport()
    samples = list(samples)
    report.samples_checked = len(samples)

    id_counts = Counter(s.sample_id for s in samples)
    for sample_id, n in id_counts.items():
        if n > 1:
            report.add(sample_id, DUPLICATE_ID, f"Sample id appears {n} times.")

    for sample in samples:
        _validate_paths_and_types(sample, report, expected_bands)
        if check_dimensions:
            _validate_dimensions(sample, report, meta_reader)

    logger.info("Validation complete: %d record(s) across %d sample(s).",
                len(report.records), report.samples_checked)
    return report


def _validate_paths_and_types(sample: SampleRecord, report: ValidationReport,
                              expected_bands: int | None) -> None:
    for path in list(sample.image_paths) + ([sample.label_path] if sample.label_path else []):
        if not Path(path).exists():
            report.add(sample.sample_id, MISSING_FILE, f"Missing file: {path}")
        elif Path(path).suffix.lower() not in SUPPORTED_RASTER_EXTENSIONS:
            report.add(sample.sample_id, UNSUPPORTED_TYPE, f"Unsupported file type: {path}")
    if sample.label_path is None:
        report.add(sample.sample_id, MISSING_LABEL, "No label file associated.", SEVERITY_WARNING)
    if expected_bands is not None and len(sample.image_paths) != expected_bands:
        report.add(sample.sample_id, INCONSISTENT_DIMENSIONS,
                   f"Expected {expected_bands} band file(s), found {len(sample.image_paths)}.")


def _validate_dimensions(sample: SampleRecord, report: ValidationReport, meta_reader: MetaReader) -> None:
    sizes: set[tuple[int, int]] = set()
    for path in sample.image_paths:
        try:
            meta = meta_reader(Path(path))
        except Exception as exc:  # noqa: BLE001 - any reader failure is "corrupted metadata"
            report.add(sample.sample_id, CORRUPTED_METADATA, f"Failed to read {path}: {exc}")
            continue
        sizes.add((meta.height, meta.width))
    if len(sizes) > 1:
        report.add(sample.sample_id, INCONSISTENT_DIMENSIONS,
                   f"Band rasters have differing sizes: {sorted(sizes)}.")
    if sample.label_path is not None:
        try:
            label_meta = meta_reader(Path(sample.label_path))
        except Exception as exc:  # noqa: BLE001
            report.add(sample.sample_id, CORRUPTED_METADATA,
                       f"Failed to read label {sample.label_path}: {exc}")
            return
        if sizes and (label_meta.height, label_meta.width) not in sizes:
            report.add(sample.sample_id, INCONSISTENT_DIMENSIONS,
                       f"Label size {(label_meta.height, label_meta.width)} != image size {sorted(sizes)}.")
