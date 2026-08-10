"""Chart spec builders (Milestone 5).

Builds backend-agnostic :class:`FigureSpec`s for common EDA charts (class distribution, split counts,
patch counts, image sizes). These are pure functions producing serialisable specs — rendering is handled
by a backend via :mod:`app.visualization.exporters`. Deterministic given the same inputs.
"""

from __future__ import annotations

from app.visualization.colormap import ColorMap
from app.visualization.records import FigureKind, FigureSpec
from app.visualization.statistics import (
    ClassDistribution,
    DatasetStatistics,
    PatchStatistics,
    SplitStatistics,
)


def class_distribution_chart(dist: ClassDistribution, title: str = "Class distribution",
                             colormap: ColorMap | None = None) -> FigureSpec:
    """A bar chart of per-class counts (colours from a colormap when provided)."""
    labels = [str(k) for k in sorted(dist.counts)]
    values = [dist.counts[int(k)] for k in labels]
    colors = None
    if colormap is not None:
        try:
            colors = [colormap.get(int(k)).hex for k in labels]
        except Exception:  # noqa: BLE001 - missing colour just falls back to defaults
            colors = None
    return FigureSpec(
        kind=FigureKind.BAR.value, title=title,
        payload={"labels": labels, "values": values},
        options={"xlabel": "class", "ylabel": "count", "colors": colors},
    )


def split_distribution_chart(stats: SplitStatistics, title: str = "Split distribution") -> FigureSpec:
    return FigureSpec(
        kind=FigureKind.BAR.value, title=title,
        payload={"labels": list(stats.counts.keys()), "values": list(stats.counts.values())},
        options={"xlabel": "split", "ylabel": "samples"},
    )


def patch_per_split_chart(stats: PatchStatistics, title: str = "Patches per split") -> FigureSpec:
    return FigureSpec(
        kind=FigureKind.BAR.value, title=title,
        payload={"labels": list(stats.per_split.keys()), "values": list(stats.per_split.values())},
        options={"xlabel": "split", "ylabel": "patches"},
    )


def image_size_chart(stats: DatasetStatistics, title: str = "Image sizes") -> FigureSpec:
    return FigureSpec(
        kind=FigureKind.BAR.value, title=title,
        payload={"labels": list(stats.image_size_counts.keys()),
                 "values": list(stats.image_size_counts.values())},
        options={"xlabel": "size (HxW)", "ylabel": "count"},
    )
