"""Label overlay / mask visualization spec builders (Milestone 5).

Ground-truth label visualization only — **no model predictions**. Produces backend-agnostic
:class:`FigureSpec`s for a mask display and a semi-transparent image+mask overlay, plus a legend from a
:class:`ColorMap`. Rendering (which reads rasters) is done by a backend and degrades gracefully when
raster libraries are unavailable.
"""

from __future__ import annotations

from pathlib import Path

from app.visualization.colormap import ColorMap
from app.visualization.records import FigureKind, FigureSpec, Legend


def mask_spec(mask_source: Path, colormap: ColorMap, title: str = "Ground-truth mask") -> FigureSpec:
    """A coloured segmentation-mask display spec (ground truth)."""
    return FigureSpec(
        kind=FigureKind.IMAGE.value, title=title,
        payload={"source_image": str(mask_source), "mode": "mask", "colormap": colormap.to_dict()},
        options={},
    )


def overlay_spec(image_source: Path, mask_source: Path, colormap: ColorMap,
                 alpha: float = 0.5, title: str = "Mask overlay") -> FigureSpec:
    """A semi-transparent ground-truth mask overlaid on the source image."""
    if not (0.0 <= alpha <= 1.0):
        raise ValueError(f"alpha must be in [0, 1], got {alpha}.")
    return FigureSpec(
        kind=FigureKind.OVERLAY.value, title=title,
        payload={"source_image": str(image_source), "mask_source": str(mask_source),
                 "colormap": colormap.to_dict(), "alpha": alpha},
        options={},
    )


def legend_for(colormap: ColorMap) -> Legend:
    """Generate a legend from a colormap (delegates to the colormap)."""
    return colormap.legend()
