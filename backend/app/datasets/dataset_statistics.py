"""Real class distribution + train-only normalization fit (Milestone 12).

Computes the **real** per-class distribution (pixel + sample counts, per split, thin cloud surfaced) and
fits :class:`NormalizationStatistics` from the **training split only** (never val/test — leakage
prevention, section 10), **reusing M4** ``compute_band_stats`` / ``NormalizationStatistics``. numpy is a
guarded import; label/image reading is delegated to an injectable reader so both real GeoTIFF and the
synthetic ``.npy`` fixture flow through the same code. Deterministic statistics hash.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from app.core.exceptions import PreprocessingError
from app.datasets.records import REGIME_REAL, ClassDistributionReport
from app.preprocessing.normalization import NormalizationStatistics, compute_band_stats
from app.preprocessing.records import SampleRecord
from app.utils.hashing import stable_hash

logger = logging.getLogger(__name__)

ArrayReader = Callable[[Path], Any]


def _require_numpy():
    try:
        import numpy as np  # type: ignore
        return np
    except ImportError as exc:  # pragma: no cover
        raise PreprocessingError("numpy is required for dataset statistics but is not installed.") from exc


def class_distribution_report(
    samples_by_split: Mapping[str, Sequence[SampleRecord]],
    *,
    label_reader: ArrayReader,
    class_mapping: dict[int, str],
    data_regime: str = REGIME_REAL,
) -> ClassDistributionReport:
    """Compute the real per-class distribution over splits (thin cloud surfaced explicitly)."""
    np = _require_numpy()
    class_names = [class_mapping[i] for i in sorted(class_mapping)]
    pixel_counts: dict[str, int] = {c: 0 for c in class_names}
    sample_counts: dict[str, int] = {c: 0 for c in class_names}
    per_split: dict[str, dict[str, int]] = {}
    total = 0

    for split, samples in samples_by_split.items():
        split_counts: dict[str, int] = {c: 0 for c in class_names}
        for s in samples:
            if s.label_path is None:
                continue
            arr = np.asarray(label_reader(Path(s.label_path))).astype("int64")
            counts = np.bincount(arr.reshape(-1), minlength=len(class_names))
            present_here: set[str] = set()
            for idx, name in enumerate(class_names):
                c = int(counts[idx]) if idx < len(counts) else 0
                pixel_counts[name] += c
                split_counts[name] += c
                total += c
                if c > 0:
                    present_here.add(name)
            for name in present_here:
                sample_counts[name] += 1
        per_split[split] = split_counts

    report = ClassDistributionReport(
        class_names=class_names, pixel_counts=pixel_counts, sample_counts=sample_counts,
        per_split_pixels=per_split, total_pixels=total, data_regime=data_regime)
    logger.info("Class distribution: %s (thin_cloud fraction=%s).",
                report.percentages(), report.thin_cloud_fraction())
    return report


def fit_normalization(
    train_image_paths: Sequence[Path],
    *,
    image_reader: ArrayReader,
    normalization_mode: str,
    nodata_value: float | None = None,
) -> NormalizationStatistics:
    """Fit :class:`NormalizationStatistics` from the **training split only** (reuses M4).

    Reads each training image as a ``(C, H, W)`` array, concatenates per-band pixels, and computes per-band
    statistics once. Validation/test data are never touched here.
    """
    np = _require_numpy()
    paths = list(train_image_paths)
    if not paths:
        raise PreprocessingError("Cannot fit normalization: no training images provided.")

    per_band: Any = None
    for p in paths:
        arr = np.asarray(image_reader(Path(p)), dtype="float64")
        if arr.ndim == 2:
            arr = arr[np.newaxis, ...]
        flat = arr.reshape(arr.shape[0], -1)                     # (C, H*W)
        per_band = flat if per_band is None else np.concatenate([per_band, flat], axis=1)

    stacked = per_band[:, np.newaxis, :]                          # (C, 1, N) for compute_band_stats
    band_stats = compute_band_stats(stacked, nodata=nodata_value)
    stats = NormalizationStatistics.from_band_stats(band_stats, normalization_mode)
    logger.info("Fitted normalization on %d train image(s): %d band(s).", len(paths), stats.num_bands)
    return stats


def normalization_stats_hash(stats: NormalizationStatistics) -> str:
    """Deterministic hash of normalization statistics (ignores the created_utc timestamp)."""
    payload = stats.to_dict()
    payload.pop("created_utc", None)
    return stable_hash(payload)
