"""Class colour mapping (Milestone 5).

Deterministic, backend-agnostic colour mapping for segmentation classes, with legend generation. Hex
strings only — no plotting-library dependency. Provides default palettes for CloudSEN12 (multi-class) and
On Cloud N (binary).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import CloudClass, OnCloudNLabel
from app.core.exceptions import CloudMaskingError
from app.visualization.records import Legend, LegendEntry


@dataclass(frozen=True)
class ClassColor:
    """A class index mapped to a human label and a hex colour."""

    index: int
    name: str
    hex: str

    def to_dict(self) -> dict[str, Any]:
        return {"index": self.index, "name": self.name, "hex": self.hex}


@dataclass
class ColorMap:
    """An ordered set of :class:`ClassColor` with lookup + legend generation."""

    colors: list[ClassColor] = field(default_factory=list)

    def __post_init__(self) -> None:
        seen = [c.index for c in self.colors]
        if len(seen) != len(set(seen)):
            raise CloudMaskingError("ColorMap has duplicate class indices.")

    def get(self, index: int) -> ClassColor:
        for c in self.colors:
            if c.index == index:
                return c
        raise CloudMaskingError(f"No colour registered for class index {index}.")

    def indices(self) -> list[int]:
        return [c.index for c in self.colors]

    def hex_list(self) -> list[str]:
        """Hex colours ordered by class index (useful for a listed colormap)."""
        return [c.hex for c in sorted(self.colors, key=lambda c: c.index)]

    def legend(self) -> Legend:
        """Generate a :class:`Legend` ordered by class index."""
        return Legend(entries=[
            LegendEntry(label=c.name, color=c.hex, index=c.index)
            for c in sorted(self.colors, key=lambda c: c.index)
        ])

    def to_dict(self) -> dict[str, Any]:
        return {"colors": [c.to_dict() for c in self.colors]}


# Accessible, high-contrast defaults. Snow/bright surfaces fall under "clear".
DEFAULT_CLOUDSEN12_COLORMAP = ColorMap([
    ClassColor(CloudClass.CLEAR.value, "clear", "#1a9850"),         # green
    ClassColor(CloudClass.THICK_CLOUD.value, "thick_cloud", "#f7f7f7"),  # near-white
    ClassColor(CloudClass.THIN_CLOUD.value, "thin_cloud", "#fdae61"),    # orange
    ClassColor(CloudClass.CLOUD_SHADOW.value, "cloud_shadow", "#4d4d4d"),  # dark grey
])

DEFAULT_ON_CLOUD_N_COLORMAP = ColorMap([
    ClassColor(OnCloudNLabel.NO_CLOUD.value, "no_cloud", "#1a9850"),
    ClassColor(OnCloudNLabel.CLOUD.value, "cloud", "#f7f7f7"),
])

#: Registry of named default colormaps.
DEFAULT_COLORMAPS: dict[str, ColorMap] = {
    "cloudsen12": DEFAULT_CLOUDSEN12_COLORMAP,
    "on_cloud_n": DEFAULT_ON_CLOUD_N_COLORMAP,
}


def get_colormap(dataset_id: str) -> ColorMap:
    """Return the default colormap for a dataset id, or raise if unknown."""
    if dataset_id not in DEFAULT_COLORMAPS:
        raise CloudMaskingError(
            f"No default colormap for '{dataset_id}'. Known: {sorted(DEFAULT_COLORMAPS)}."
        )
    return DEFAULT_COLORMAPS[dataset_id]
