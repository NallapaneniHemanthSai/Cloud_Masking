"""Normalization utilities (Milestone 4).

Per-band normalization with configurable methods, value clipping, and missing-value handling. Operates
on numpy arrays shaped ``(C, H, W)`` (channels-first). numpy is a guarded import — functions raise a
clear error if it is unavailable. No model-specific transforms live here.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import (
    DEFAULT_PERCENTILE_RANGE,
    PREPROCESSING_VERSION,
    NormalizationMode,
)
from app.core.exceptions import PreprocessingError

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None  # type: ignore

logger = logging.getLogger(__name__)

# Small constant to avoid division-by-zero on constant bands.
_EPSILON = 1e-8


def _require_numpy() -> None:
    if np is None:
        raise PreprocessingError("numpy is required for normalization but is not installed.")


@dataclass
class BandStats:
    """Per-band statistics used by normalization (lists indexed by band)."""

    minimum: list[float]
    maximum: list[float]
    mean: list[float]
    std: list[float]
    p_low: list[float]
    p_high: list[float]


@dataclass
class NormalizationStatistics:
    """Serialisable record of per-band normalization statistics + metadata.

    This is the reusable framework for persisting/reloading normalization state (e.g. fit on train,
    applied to val/test). It is **standard-library only** (lists of floats) and does not require numpy —
    Milestone 4 provides the framework and does not compute statistics over the real dataset.
    """

    means: list[float] = field(default_factory=list)
    stds: list[float] = field(default_factory=list)
    minimums: list[float] = field(default_factory=list)
    maximums: list[float] = field(default_factory=list)
    p_low: list[float] = field(default_factory=list)
    p_high: list[float] = field(default_factory=list)
    clip_low: float | None = None
    clip_high: float | None = None
    percentile_range: tuple[float, float] = DEFAULT_PERCENTILE_RANGE
    normalization_mode: str = NormalizationMode.MINMAX.value
    num_bands: int = 0
    created_utc: str = ""
    preprocessing_version: str = PREPROCESSING_VERSION

    @classmethod
    def from_band_stats(
        cls,
        stats: BandStats,
        normalization_mode: str = NormalizationMode.MINMAX.value,
        *,
        clip_low: float | None = None,
        clip_high: float | None = None,
        percentile_range: tuple[float, float] = DEFAULT_PERCENTILE_RANGE,
    ) -> "NormalizationStatistics":
        """Build from a :class:`BandStats` plus normalization metadata."""
        return cls(
            means=list(stats.mean), stds=list(stats.std),
            minimums=list(stats.minimum), maximums=list(stats.maximum),
            p_low=list(stats.p_low), p_high=list(stats.p_high),
            clip_low=clip_low, clip_high=clip_high,
            percentile_range=percentile_range, normalization_mode=normalization_mode,
            num_bands=len(stats.mean),
            created_utc=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "means": self.means, "stds": self.stds,
            "minimums": self.minimums, "maximums": self.maximums,
            "p_low": self.p_low, "p_high": self.p_high,
            "clip_low": self.clip_low, "clip_high": self.clip_high,
            "percentile_range": list(self.percentile_range),
            "normalization_mode": self.normalization_mode,
            "num_bands": self.num_bands,
            "created_utc": self.created_utc,
            "preprocessing_version": self.preprocessing_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NormalizationStatistics":
        pr = data.get("percentile_range", list(DEFAULT_PERCENTILE_RANGE))
        return cls(
            means=list(data.get("means", [])), stds=list(data.get("stds", [])),
            minimums=list(data.get("minimums", [])), maximums=list(data.get("maximums", [])),
            p_low=list(data.get("p_low", [])), p_high=list(data.get("p_high", [])),
            clip_low=data.get("clip_low"), clip_high=data.get("clip_high"),
            percentile_range=(float(pr[0]), float(pr[1])),
            normalization_mode=str(data.get("normalization_mode", NormalizationMode.MINMAX.value)),
            num_bands=int(data.get("num_bands", 0)),
            created_utc=str(data.get("created_utc", "")),
            preprocessing_version=str(data.get("preprocessing_version", PREPROCESSING_VERSION)),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        logger.info("Wrote normalization statistics: %s", path)
        return path

    @classmethod
    def load_json(cls, path: Path) -> "NormalizationStatistics":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _as_chw_float(array: Any) -> Any:
    arr = np.asarray(array)
    if arr.ndim == 2:
        arr = arr[np.newaxis, ...]  # promote (H,W) -> (1,H,W)
    if arr.ndim != 3:
        raise PreprocessingError(f"array must be (C,H,W) or (H,W), got {arr.ndim}D.")
    return arr.astype("float64", copy=True)


def apply_nodata_mask(array: Any, nodata: float | None) -> Any:
    """Return a float copy with ``nodata`` values replaced by NaN (per-band-safe for stats)."""
    _require_numpy()
    arr = _as_chw_float(array)
    if nodata is not None:
        arr[arr == nodata] = np.nan
    return arr


def compute_band_stats(
    array: Any,
    nodata: float | None = None,
    percentile_range: tuple[float, float] = DEFAULT_PERCENTILE_RANGE,
) -> BandStats:
    """Compute per-band statistics, ignoring NaN / nodata values."""
    _require_numpy()
    arr = apply_nodata_mask(array, nodata)
    p_low, p_high = percentile_range
    stats = BandStats(minimum=[], maximum=[], mean=[], std=[], p_low=[], p_high=[])
    for band in arr:
        finite = band[np.isfinite(band)]
        if finite.size == 0:  # entirely missing band
            for lst in (stats.minimum, stats.maximum, stats.mean, stats.std, stats.p_low, stats.p_high):
                lst.append(0.0)
            continue
        stats.minimum.append(float(np.min(finite)))
        stats.maximum.append(float(np.max(finite)))
        stats.mean.append(float(np.mean(finite)))
        stats.std.append(float(np.std(finite)))
        stats.p_low.append(float(np.percentile(finite, p_low)))
        stats.p_high.append(float(np.percentile(finite, p_high)))
    return stats


def clip_values(array: Any, low: float, high: float) -> Any:
    """Clip an array to ``[low, high]`` (numpy required)."""
    _require_numpy()
    return np.clip(np.asarray(array), low, high)


def normalize(
    array: Any,
    mode: str = NormalizationMode.MINMAX.value,
    *,
    stats: BandStats | None = None,
    nodata: float | None = None,
    fill_value: float = 0.0,
) -> Any:
    """Normalize a (C, H, W) array per band.

    Args:
        array: Input array (C, H, W) or (H, W).
        mode: One of :class:`NormalizationMode` values.
        stats: Optional precomputed :class:`BandStats` (recommended so train stats apply to val/test).
        nodata: Optional sentinel treated as missing; replaced by NaN, then filled after scaling.
        fill_value: Value substituted for missing pixels in the output.

    Returns:
        A float64 numpy array of the same shape, with missing pixels set to ``fill_value``.
    """
    _require_numpy()
    valid_modes = {m.value for m in NormalizationMode}
    if mode not in valid_modes:
        raise PreprocessingError(f"Unknown normalization mode {mode!r}; expected one of {sorted(valid_modes)}.")

    arr = apply_nodata_mask(array, nodata)
    missing = ~np.isfinite(arr)
    if stats is None:
        stats = compute_band_stats(arr, nodata=None)  # already NaN-masked

    out = np.empty_like(arr)
    for i, band in enumerate(arr):
        out[i] = _normalize_band(band, mode, stats, i)

    out[missing] = fill_value
    return out


def _normalize_band(band: Any, mode: str, stats: BandStats, index: int) -> Any:
    if mode == NormalizationMode.NONE.value:
        return band
    if mode == NormalizationMode.MINMAX.value:
        lo, hi = stats.minimum[index], stats.maximum[index]
        return (band - lo) / (hi - lo + _EPSILON)
    if mode == NormalizationMode.ZSCORE.value:
        mean, std = stats.mean[index], stats.std[index]
        return (band - mean) / (std + _EPSILON)
    if mode == NormalizationMode.PERCENTILE.value:
        lo, hi = stats.p_low[index], stats.p_high[index]
        clipped = np.clip(band, lo, hi)
        return (clipped - lo) / (hi - lo + _EPSILON)
    raise PreprocessingError(f"Unhandled normalization mode {mode!r}.")  # pragma: no cover
