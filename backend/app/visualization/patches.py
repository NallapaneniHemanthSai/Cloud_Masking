"""Patch grid visualization (Milestone 5).

Derives visualization metadata and a backend-agnostic :class:`FigureSpec` for a patch grid from
preprocessing :class:`PatchRecord`s (reusing the patch manifest). Shows patch boundaries, overlap regions,
and patch indexing. Deterministic; standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from app.preprocessing.records import PatchRecord
from app.visualization.records import FigureKind, FigureSpec


@dataclass
class PatchGridMetadata:
    """Serialisable metadata describing a patch grid."""

    num_patches: int = 0
    patch_size: int | None = None
    overlap: int | None = None
    has_overlap: bool = False
    indices: list[int] = field(default_factory=list)
    windows: list[dict[str, int]] = field(default_factory=list)   # index/row_off/col_off/height/width

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_patches": self.num_patches,
            "patch_size": self.patch_size,
            "overlap": self.overlap,
            "has_overlap": self.has_overlap,
            "indices": self.indices,
            "windows": self.windows,
        }


def patch_grid_metadata(records: Iterable[PatchRecord]) -> PatchGridMetadata:
    """Build :class:`PatchGridMetadata` from patch records."""
    records = list(records)
    windows = [
        {"index": r.patch_index, "row_off": r.row_off, "col_off": r.col_off,
         "height": r.height, "width": r.width}
        for r in records
    ]
    overlap = records[0].overlap if records else None
    return PatchGridMetadata(
        num_patches=len(records),
        patch_size=records[0].patch_size if records else None,
        overlap=overlap,
        has_overlap=bool(overlap),
        indices=[r.patch_index for r in records],
        windows=windows,
    )


def patch_grid_spec(records: Iterable[PatchRecord], image_size: tuple[int, int],
                    title: str = "Patch grid", source_image: Path | None = None) -> FigureSpec:
    """A :class:`FigureSpec` describing patch rectangles over an image of ``image_size`` (H, W)."""
    meta = patch_grid_metadata(records)
    payload: dict[str, Any] = {
        "image_size": list(image_size),
        "rectangles": meta.windows,
        "overlap": meta.overlap,
        "patch_size": meta.patch_size,
    }
    if source_image is not None:
        payload["source_image"] = str(source_image)
    return FigureSpec(kind=FigureKind.PATCH_GRID.value, title=title, payload=payload)
