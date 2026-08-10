"""Band visualization spec builders (Milestone 5).

Builds backend-agnostic :class:`FigureSpec` descriptions for RGB composites, false-colour composites, and
single bands. The builders are pure (they only produce serialisable specs referencing a source raster);
actual pixel rendering — which needs rasterio/numpy — is done by a plotting backend and **degrades
gracefully** when those libraries are unavailable.
"""

from __future__ import annotations

from pathlib import Path

from app.core.constants import Dataset
from app.visualization.records import FigureKind, FigureSpec

# Default band index selections assuming the conventional band ordering per dataset.
# CloudSEN12 L1C order [B01,B02,B03,B04,B05,B06,B07,B08,B8A,B09,B10,B11,B12]; On Cloud N [B02,B03,B04,B08].
# Exact ordering must be confirmed against the downloaded data (source-to-claim C-1/C-2).
DEFAULT_RGB_BANDS: dict[str, tuple[int, int, int]] = {
    Dataset.CLOUDSEN12.value: (3, 2, 1),    # B04, B03, B02
    Dataset.ON_CLOUD_N.value: (2, 1, 0),    # B04, B03, B02
}
DEFAULT_FALSE_COLOR_BANDS: dict[str, tuple[int, int, int]] = {
    Dataset.CLOUDSEN12.value: (7, 3, 2),    # B08 (NIR), B04, B03
    Dataset.ON_CLOUD_N.value: (3, 2, 1),    # B08 (NIR), B04, B03
}


def default_rgb_bands(dataset: str) -> tuple[int, int, int]:
    return DEFAULT_RGB_BANDS.get(dataset, (0, 1, 2))


def default_false_color_bands(dataset: str) -> tuple[int, int, int]:
    return DEFAULT_FALSE_COLOR_BANDS.get(dataset, (0, 1, 2))


def rgb_composite_spec(source_image: Path, band_indices: tuple[int, int, int],
                       title: str = "RGB composite") -> FigureSpec:
    """A true-colour RGB composite spec."""
    return FigureSpec(
        kind=FigureKind.IMAGE.value, title=title,
        payload={"source_image": str(source_image), "band_indices": list(band_indices), "mode": "rgb"},
        options={"stretch": "percentile"},
    )


def false_color_spec(source_image: Path, band_indices: tuple[int, int, int],
                     title: str = "False-colour composite") -> FigureSpec:
    """A false-colour composite spec (e.g. NIR/Red/Green)."""
    return FigureSpec(
        kind=FigureKind.IMAGE.value, title=title,
        payload={"source_image": str(source_image), "band_indices": list(band_indices),
                 "mode": "false_color"},
        options={"stretch": "percentile"},
    )


def single_band_spec(source_image: Path, band_index: int, title: str | None = None,
                     cmap: str = "gray") -> FigureSpec:
    """A single-band grayscale (or colormap) spec."""
    return FigureSpec(
        kind=FigureKind.IMAGE.value, title=title or f"Band {band_index}",
        payload={"source_image": str(source_image), "band_index": band_index, "mode": "single"},
        options={"cmap": cmap},
    )
