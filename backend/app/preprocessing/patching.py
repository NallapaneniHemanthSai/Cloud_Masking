"""Patch generation (Milestone 4).

Deterministic tiling of an image into fixed-size patches with configurable overlap. The **grid**
computation and geotransform propagation are pure-standard-library (and unit-testable without numpy);
the array **extraction** helper uses numpy (guarded import). No training/model code.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import PreprocessingError

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None  # type: ignore

logger = logging.getLogger(__name__)

# Number of coefficients in an affine geotransform (a, b, c, d, e, f).
_AFFINE_COEFFS = 6


@dataclass(frozen=True)
class PatchWindow:
    """A rectangular read window in pixel coordinates (top-left origin)."""

    row_off: int
    col_off: int
    height: int
    width: int


def generate_patch_grid(
    height: int,
    width: int,
    patch_size: int,
    overlap: int = 0,
) -> list[PatchWindow]:
    """Compute a deterministic grid of patch windows covering an ``height`` x ``width`` image.

    The stride is ``patch_size - overlap``. The final row/column are clamped so the last patch ends at
    the image edge (kept full-size by shifting its origin back), guaranteeing full ``patch_size`` patches
    and complete coverage without padding. Output order is row-major and deterministic.

    Args:
        height: Image height in pixels.
        width: Image width in pixels.
        patch_size: Square patch edge length (> 0).
        overlap: Overlap between adjacent patches (0 <= overlap < patch_size).

    Returns:
        Ordered list of :class:`PatchWindow`.

    Raises:
        PreprocessingError: On invalid arguments.
    """
    if patch_size <= 0:
        raise PreprocessingError(f"patch_size must be > 0, got {patch_size}.")
    if not (0 <= overlap < patch_size):
        raise PreprocessingError(f"overlap must satisfy 0 <= overlap < patch_size, got {overlap}.")
    if height <= 0 or width <= 0:
        raise PreprocessingError(f"image dimensions must be positive, got {height}x{width}.")

    stride = patch_size - overlap
    row_offsets = _axis_offsets(height, patch_size, stride)
    col_offsets = _axis_offsets(width, patch_size, stride)

    windows = [
        PatchWindow(row_off=r, col_off=c,
                    height=min(patch_size, height), width=min(patch_size, width))
        for r in row_offsets
        for c in col_offsets
    ]
    logger.debug("Generated %d patch window(s) for %dx%d (patch=%d, overlap=%d).",
                 len(windows), height, width, patch_size, overlap)
    return windows


def _axis_offsets(length: int, patch_size: int, stride: int) -> list[int]:
    """Deterministic 1-D offsets covering ``length`` with the final offset clamped to the edge."""
    if length <= patch_size:
        return [0]
    offsets = list(range(0, length - patch_size + 1, stride))
    last = length - patch_size
    if offsets[-1] != last:
        offsets.append(last)  # ensure full coverage of the trailing edge
    return offsets


def window_transform(
    parent_transform: tuple[float, float, float, float, float, float],
    window: PatchWindow,
) -> tuple[float, float, float, float, float, float]:
    """Propagate an affine geotransform to a patch window (preserve geospatial metadata).

    Uses the rasterio/GDAL affine convention ``(a, b, c, d, e, f)`` where a pixel ``(col, row)`` maps to
    ``x = a*col + b*row + c`` and ``y = d*col + e*row + f``. Only the origin (c, f) shifts.

    Returns:
        The window's affine geotransform tuple.
    """
    if len(parent_transform) != _AFFINE_COEFFS:
        raise PreprocessingError(
            f"parent_transform must have {_AFFINE_COEFFS} coefficients, got {len(parent_transform)}."
        )
    a, b, c, d, e, f = parent_transform
    new_c = c + a * window.col_off + b * window.row_off
    new_f = f + d * window.col_off + e * window.row_off
    return (a, b, new_c, d, e, new_f)


def extract_patch(array: Any, window: PatchWindow) -> Any:
    """Extract a single patch from a (C, H, W) or (H, W) numpy array (numpy required)."""
    if np is None:
        raise PreprocessingError("numpy is required for patch extraction but is not installed.")
    arr = np.asarray(array)
    r, c, h, w = window.row_off, window.col_off, window.height, window.width
    if arr.ndim == 2:
        return arr[r:r + h, c:c + w]
    if arr.ndim == 3:
        return arr[:, r:r + h, c:c + w]
    raise PreprocessingError(f"array must be 2D (H,W) or 3D (C,H,W), got {arr.ndim}D.")


def extract_patches(array: Any, patch_size: int, overlap: int = 0) -> list[Any]:
    """Extract all patches from a (C, H, W) or (H, W) numpy array using the deterministic grid."""
    if np is None:
        raise PreprocessingError("numpy is required for patch extraction but is not installed.")
    arr = np.asarray(array)
    height, width = (arr.shape[-2], arr.shape[-1])
    grid = generate_patch_grid(height, width, patch_size, overlap)
    return [extract_patch(arr, window) for window in grid]
