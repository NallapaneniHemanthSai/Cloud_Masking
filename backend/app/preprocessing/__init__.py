"""Preprocessing pipeline (Milestone 4).

Reusable, modular preprocessing utilities — no model/training/inference code:

* :mod:`app.preprocessing.records` — typed records (SampleRecord, PatchRecord, ValidationRecord, SplitRecord).
* :mod:`app.preprocessing.config` — validated :class:`PreprocessingConfig` (patch size, overlap,
  normalization mode, augmentation toggle, seed, split ratios).
* :mod:`app.preprocessing.loader` — dataset layout + sample discovery (CloudSEN12, On Cloud N).
* :mod:`app.preprocessing.validation` — structured validation report + summary.
* :mod:`app.preprocessing.patching` — deterministic patch grid + geotransform propagation.
* :mod:`app.preprocessing.patch_manifest` — per-patch manifest with JSONL/CSV export.
* :mod:`app.preprocessing.normalization` — per-band normalization + :class:`NormalizationStatistics`.
* :mod:`app.preprocessing.splitting` — reproducible, group-aware train/val/test splits.
* :mod:`app.preprocessing.augmentation` — backend-agnostic augmentation framework + Albumentations adapter.
* :mod:`app.preprocessing.raster_io` — guarded rasterio reader.
* :mod:`app.preprocessing.pipeline` — orchestration (dry plan + array processing + patch manifest).

numpy / rasterio / albumentations are guarded imports so this package imports on a bare interpreter;
the functions that need them raise a clear error when they are absent.
"""

from app.preprocessing.config import PreprocessingConfig, SplitRatios
from app.preprocessing.records import (
    PatchRecord,
    SampleRecord,
    SplitRecord,
    ValidationRecord,
)

__all__ = [
    "PreprocessingConfig",
    "SplitRatios",
    "SampleRecord",
    "PatchRecord",
    "SplitRecord",
    "ValidationRecord",
]
