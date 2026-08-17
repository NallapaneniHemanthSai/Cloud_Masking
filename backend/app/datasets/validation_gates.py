"""Experimental-dataset validation gates (Milestone 12).

Produces a structured :class:`DatasetValidationReport` (file existence / checksum / metadata / label /
dimension / band-count / completeness) for an experimental dataset. **Reuses M3 integrity** (checksums,
existence) and takes an **injectable label reader** so both real GeoTIFF (rasterio) and the synthetic
``.npy`` fixture validate through the same logic — no duplicated integrity code. Standard-library only
(numpy used only if a reader hands back arrays). Nothing is invented: absent checks stay ``NOT_VERIFIED``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Sequence

from app.datasets.integrity import verify_checksum
from app.datasets.records import (
    CHECK_FAIL,
    CHECK_NA,
    CHECK_NOT_VERIFIED,
    CHECK_PASS,
    CHECK_WARN,
    INCOMPLETE,
    INVALID,
    NOT_PRESENT,
    READY,
    READY_WITH_WARNINGS,
    REGIME_REAL,
    DatasetValidationReport,
)
from app.preprocessing.records import SampleRecord

logger = logging.getLogger(__name__)

#: A label reader maps a label path -> a 2-D integer array-like (``.shape`` + iterable of rows).
LabelReader = Callable[[Path], Any]


def _sample_files(sample: SampleRecord) -> list[Path]:
    files = [Path(p) for p in sample.image_paths]
    if sample.label_path is not None:
        files.append(Path(sample.label_path))
    return files


def _label_values_in_range(arr: Any, num_classes: int) -> tuple[bool, set[int]]:
    """Return (in_range, present_class_set) for a label array, without requiring numpy."""
    try:
        import numpy as np  # local import keeps the module importable on a bare interpreter
        a = np.asarray(arr)
        present = {int(v) for v in np.unique(a)}
    except Exception:  # noqa: BLE001 - fall back to pure-python iteration
        present = {int(v) for row in arr for v in row}
    in_range = all(0 <= v < num_classes for v in present)
    return in_range, present


def validate_experimental_dataset(
    dataset_id: str,
    samples: Sequence[SampleRecord],
    *,
    num_classes: int,
    required_classes: Sequence[str],
    class_mapping: dict[int, str],
    label_reader: LabelReader | None = None,
    checksums: dict[str, str] | None = None,
    checksum_algorithm: str = "sha256",
    expected_bands: int | None = None,
    metadata_ok: bool = True,
    data_regime: str = REGIME_REAL,
) -> DatasetValidationReport:
    """Validate an experimental dataset and return a structured :class:`DatasetValidationReport`.

    Args:
        dataset_id: Dataset identifier.
        samples: Discovered/curated samples (image + label paths).
        num_classes / required_classes / class_mapping: label schema.
        label_reader: Optional callable ``path -> 2-D label array``; when ``None`` label/dimension checks
            stay ``NOT_VERIFIED`` (never fabricated).
        checksums: Optional ``file_path -> sha256`` map; verified when present.
        expected_bands: Optional expected image band-file count per sample.
        metadata_ok: Whether provenance/metadata is present & consistent.
        data_regime: ``REAL`` or ``SYNTHETIC``.
    """
    report = DatasetValidationReport(dataset_id=dataset_id, data_regime=data_regime,
                                     manifest_status=CHECK_PASS)
    samples = list(samples)
    if not samples:
        report.overall_status = NOT_PRESENT
        report.file_status = report.completeness_status = CHECK_NA
        report.failures.append("No samples present (dataset not downloaded / empty pool).")
        return report

    # --- file existence + completeness --------------------------------------------------------------
    missing: list[str] = []
    all_files: list[Path] = []
    for s in samples:
        for f in _sample_files(s):
            all_files.append(f)
            if not f.exists():
                missing.append(str(f))
    if missing:
        report.file_status = CHECK_FAIL
        report.completeness_status = INCOMPLETE
        report.failures.append(f"{len(missing)} expected file(s) missing (e.g. {missing[0]}).")
    else:
        report.file_status = CHECK_PASS
        report.completeness_status = CHECK_PASS

    # --- band-count consistency ---------------------------------------------------------------------
    if expected_bands is not None:
        bad_bands = [s.sample_id for s in samples if len(s.image_paths) not in (expected_bands, 1)]
        if bad_bands:
            report.dimension_status = CHECK_FAIL
            report.failures.append(f"{len(bad_bands)} sample(s) have an unexpected band-file count.")

    # --- checksums (reuse M3) -----------------------------------------------------------------------
    if checksums:
        mismatches = []
        for f in all_files:
            expected = checksums.get(str(f))
            if expected and f.exists() and not verify_checksum(f, expected, checksum_algorithm):
                mismatches.append(str(f))
        if mismatches:
            report.checksum_status = CHECK_FAIL
            report.failures.append(f"{len(mismatches)} checksum mismatch(es) (e.g. {mismatches[0]}).")
        else:
            report.checksum_status = CHECK_PASS
    else:
        report.checksum_status = CHECK_NOT_VERIFIED
        report.warnings.append("No checksums provided — integrity NOT VERIFIED.")

    # --- metadata -----------------------------------------------------------------------------------
    report.metadata_status = CHECK_PASS if metadata_ok else CHECK_WARN
    if not metadata_ok:
        report.warnings.append("Provenance/metadata incomplete.")

    # --- labels + dimensions (needs a reader) -------------------------------------------------------
    present_classes: set[int] = set()
    if label_reader is not None and report.file_status == CHECK_PASS:
        label_bad = False
        sizes: set[tuple[int, int]] = set()
        for s in samples:
            if s.label_path is None:
                continue
            try:
                arr = label_reader(Path(s.label_path))
            except Exception as exc:  # noqa: BLE001
                report.failures.append(f"Failed to read label {s.label_path}: {exc}")
                label_bad = True
                continue
            in_range, present = _label_values_in_range(arr, num_classes)
            present_classes |= present
            if not in_range:
                report.failures.append(f"Label {s.label_path} has values outside [0,{num_classes-1}].")
                label_bad = True
            shape = getattr(arr, "shape", None)
            if shape and len(shape) >= 2:
                sizes.add((int(shape[-2]), int(shape[-1])))
        report.label_status = CHECK_FAIL if label_bad else CHECK_PASS
        if report.dimension_status == CHECK_NA:
            report.dimension_status = CHECK_PASS if sizes else CHECK_NOT_VERIFIED

        # Required-class presence (thin cloud must exist).
        present_names = {class_mapping.get(i, str(i)) for i in present_classes}
        missing_classes = [c for c in required_classes if c not in present_names]
        if missing_classes:
            report.failures.append(f"Required class(es) absent from labels: {missing_classes}.")
            report.label_status = CHECK_FAIL
    else:
        report.label_status = CHECK_NOT_VERIFIED
        if report.dimension_status == CHECK_NA:
            report.dimension_status = CHECK_NOT_VERIFIED
        report.warnings.append("No label reader available — label/dimension checks NOT VERIFIED.")

    report.overall_status = _overall(report)
    logger.info("Validation %s: overall=%s (%d failures, %d warnings).",
                dataset_id, report.overall_status, len(report.failures), len(report.warnings))
    return report


def _overall(report: DatasetValidationReport) -> str:
    """Derive the overall status from the per-check statuses (honest, conservative)."""
    corrupt = {report.checksum_status, report.label_status, report.dimension_status}
    if CHECK_FAIL in corrupt:
        return INVALID
    if report.file_status == CHECK_FAIL or report.completeness_status == INCOMPLETE:
        return INCOMPLETE
    if report.warnings:
        return READY_WITH_WARNINGS
    return READY
