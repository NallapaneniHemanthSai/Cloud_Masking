"""Typed visualization records (Milestone 5).

Backend-agnostic, serialisable dataclasses that describe *what* to plot and *what happened* when
rendering — never exposing plotting-library objects through the public API. Standard-library only.

* :class:`FigureSpec` — a serialisable description of a figure (kind, title, data payload, options).
* :class:`RenderResult` — the outcome of a render attempt (rendered / degraded / skipped / failed).
* :class:`Legend` / :class:`LegendEntry` — class colour legend.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class FigureKind(str, enum.Enum):
    """Supported, backend-agnostic figure kinds."""

    BAR = "bar"
    HISTOGRAM = "histogram"
    LINE = "line"
    IMAGE = "image"            # single/RGB/false-colour raster (rendered by a backend that can read it)
    OVERLAY = "overlay"        # image + semi-transparent mask
    PATCH_GRID = "patch_grid"  # rectangles over an (optional) image


class RenderStatus(str, enum.Enum):
    """Outcome of a render attempt."""

    RENDERED = "rendered"      # a real image file was written
    DEGRADED = "degraded"      # plotting backend unavailable/insufficient; metadata sidecar written
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class FigureSpec:
    """A serialisable, backend-independent description of a figure.

    ``payload`` and ``options`` contain only JSON-serialisable data (lists/dicts/scalars) or file-path
    references — never numpy arrays or plotting-library objects — so specs can be persisted and rendered
    by any backend.
    """

    kind: str
    title: str
    payload: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "title": self.title, "payload": self.payload, "options": self.options}


@dataclass(frozen=True)
class RenderResult:
    """The outcome of rendering a :class:`FigureSpec`."""

    status: str
    backend: str
    output_path: str | None = None
    message: str = ""
    sidecar_path: str | None = None

    @property
    def ok(self) -> bool:
        """True when the render either produced an image or a metadata sidecar (not failed/skipped)."""
        return self.status in {RenderStatus.RENDERED.value, RenderStatus.DEGRADED.value}

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "backend": self.backend,
            "output_path": self.output_path,
            "message": self.message,
            "sidecar_path": self.sidecar_path,
        }


@dataclass(frozen=True)
class LegendEntry:
    """A single legend entry (label + colour)."""

    label: str
    color: str            # hex string, e.g. "#2c7bb6"
    index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "color": self.color, "index": self.index}


@dataclass
class Legend:
    """An ordered legend of class colours."""

    entries: list[LegendEntry] = field(default_factory=list)

    def labels(self) -> list[str]:
        return [e.label for e in self.entries]

    def colors(self) -> list[str]:
        return [e.color for e in self.entries]

    def to_dict(self) -> dict[str, Any]:
        return {"entries": [e.to_dict() for e in self.entries]}
