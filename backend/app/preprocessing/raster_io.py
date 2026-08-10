"""Raster IO (Milestone 4) — guarded rasterio wrapper.

Reading geospatial rasters requires ``rasterio`` (declared in requirements.in). This module imports
cleanly without it, but the read functions raise a clear :class:`PreprocessingError` if it is missing.
Only metadata/array reading lives here — no preprocessing logic — so the rest of the pipeline can stay
testable with synthetic in-memory arrays (no file IO, no rasterio) in unit tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.exceptions import PreprocessingError

try:  # rasterio ships bundled GDAL wheels; may not be installed on a bare interpreter.
    import rasterio  # type: ignore
except ImportError:  # pragma: no cover
    rasterio = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class RasterMeta:
    """Lightweight raster metadata (subset of a rasterio profile)."""

    height: int
    width: int
    count: int                 # number of bands
    dtype: str
    crs: str | None
    transform: tuple[float, float, float, float, float, float] | None
    nodata: float | None


def _require_rasterio() -> None:
    if rasterio is None:
        raise PreprocessingError(
            "rasterio is required to read rasters but is not installed. "
            "Install project dependencies (see requirements.in) in the Python 3.11 environment."
        )


def read_raster_meta(path: Path) -> RasterMeta:
    """Read raster metadata without loading all pixels."""
    _require_rasterio()
    path = Path(path)
    if not path.is_file():
        raise PreprocessingError(f"Raster not found: {path}")
    with rasterio.open(path) as src:  # type: ignore[union-attr]
        transform = tuple(src.transform)[:6] if src.transform else None
        return RasterMeta(
            height=int(src.height),
            width=int(src.width),
            count=int(src.count),
            dtype=str(src.dtypes[0]) if src.dtypes else "unknown",
            crs=str(src.crs) if src.crs else None,
            transform=transform,  # type: ignore[arg-type]
            nodata=src.nodata,
        )


def read_raster(path: Path) -> tuple[Any, RasterMeta]:
    """Read a raster as a (bands, height, width) array plus its metadata.

    Returns:
        A tuple ``(array, meta)`` where ``array`` is a numpy ndarray shaped (C, H, W).
    """
    _require_rasterio()
    path = Path(path)
    if not path.is_file():
        raise PreprocessingError(f"Raster not found: {path}")
    with rasterio.open(path) as src:  # type: ignore[union-attr]
        array = src.read()  # (bands, rows, cols)
        transform = tuple(src.transform)[:6] if src.transform else None
        meta = RasterMeta(
            height=int(src.height), width=int(src.width), count=int(src.count),
            dtype=str(src.dtypes[0]) if src.dtypes else "unknown",
            crs=str(src.crs) if src.crs else None,
            transform=transform,  # type: ignore[arg-type]
            nodata=src.nodata,
        )
    return array, meta
