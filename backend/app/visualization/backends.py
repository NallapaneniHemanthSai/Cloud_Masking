"""Plotting backend abstraction (Milestone 5).

Defines a backend-independent interface for turning a :class:`FigureSpec` into an image file, plus two
implementations:

* :class:`NullBackend` — always available; writes a JSON **metadata sidecar** describing the figure and
  returns a ``DEGRADED`` result (used when no plotting library is present, preserving reporting/metadata).
* :class:`MatplotlibBackend` — renders with matplotlib (guarded import; non-interactive ``Agg``).

Matplotlib is imported only inside the matplotlib backend, so no plotting-library object ever crosses the
public API — callers pass a :class:`FigureSpec` and receive a :class:`RenderResult`.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from app.visualization.records import FigureKind, FigureSpec, RenderResult, RenderStatus

logger = logging.getLogger(__name__)


def matplotlib_available() -> bool:
    """True when matplotlib can be imported."""
    try:
        import matplotlib  # type: ignore  # noqa: F401
    except ImportError:
        return False
    return True


class PlotBackend(ABC):
    """Abstract plotting backend. Implementations must not leak library objects to callers."""

    name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """Whether this backend can actually render images."""

    @abstractmethod
    def render(self, spec: FigureSpec, path: Path) -> RenderResult:
        """Render ``spec`` to ``path`` (an image file), returning a structured result."""


class NullBackend(PlotBackend):
    """Fallback backend: writes a metadata sidecar instead of an image (graceful degradation)."""

    name = "null"

    def available(self) -> bool:
        return True

    def render(self, spec: FigureSpec, path: Path) -> RenderResult:
        path = Path(path)
        sidecar = path.with_suffix(path.suffix + ".spec.json") if path.suffix else path.with_suffix(".spec.json")
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(json.dumps(spec.to_dict(), indent=2), encoding="utf-8")
        logger.info("NullBackend: wrote figure spec sidecar %s (no image rendered).", sidecar)
        return RenderResult(
            status=RenderStatus.DEGRADED.value, backend=self.name, output_path=None,
            message="Plotting backend unavailable/insufficient; wrote figure metadata sidecar.",
            sidecar_path=str(sidecar),
        )


class MatplotlibBackend(PlotBackend):
    """Renders figures with matplotlib (Agg). Degrades to a sidecar for kinds it cannot render."""

    name = "matplotlib"

    def available(self) -> bool:
        return matplotlib_available()

    def render(self, spec: FigureSpec, path: Path) -> RenderResult:
        if not self.available():
            return NullBackend().render(spec, path)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import matplotlib
            matplotlib.use("Agg")  # non-interactive, file output only
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=spec.options.get("figsize", (8, 5)))
            handled = self._draw(ax, spec)
            if not handled:  # kind needs data we cannot access -> degrade
                plt.close(fig)
                return NullBackend().render(spec, path)
            ax.set_title(spec.title)
            fig.tight_layout()
            fig.savefig(path, dpi=spec.options.get("dpi", 120))
            plt.close(fig)
        except Exception as exc:  # noqa: BLE001 - rendering failure must not crash the pipeline
            logger.warning("MatplotlibBackend failed for %s: %s", spec.kind, exc)
            return RenderResult(status=RenderStatus.FAILED.value, backend=self.name,
                                output_path=None, message=str(exc))
        return RenderResult(status=RenderStatus.RENDERED.value, backend=self.name, output_path=str(path))

    # --- kind-specific drawing (matplotlib only lives here) --------------------------------------
    def _draw(self, ax, spec: FigureSpec) -> bool:
        kind = spec.kind
        if kind in (FigureKind.BAR.value, FigureKind.HISTOGRAM.value):
            labels = spec.payload.get("labels", [])
            values = spec.payload.get("values", [])
            ax.bar([str(x) for x in labels], values, color=spec.options.get("colors"))
            ax.set_xlabel(spec.options.get("xlabel", ""))
            ax.set_ylabel(spec.options.get("ylabel", ""))
            return True
        if kind == FigureKind.LINE.value:
            ax.plot(spec.payload.get("x", []), spec.payload.get("y", []))
            return True
        if kind == FigureKind.PATCH_GRID.value:
            return self._draw_patch_grid(ax, spec)
        if kind in (FigureKind.IMAGE.value, FigureKind.OVERLAY.value):
            # Requires reading a raster; delegate to the guarded reader and degrade if unavailable.
            return self._draw_raster(ax, spec)
        return False

    def _draw_patch_grid(self, ax, spec: FigureSpec) -> bool:
        from matplotlib.patches import Rectangle
        h, w = spec.payload.get("image_size", [0, 0])
        ax.set_xlim(0, w)
        ax.set_ylim(h, 0)  # image coordinates (row down)
        ax.set_aspect("equal")
        for rect in spec.payload.get("rectangles", []):
            ax.add_patch(Rectangle(
                (rect["col_off"], rect["row_off"]), rect["width"], rect["height"],
                fill=False, edgecolor="red", linewidth=1,
            ))
            ax.text(rect["col_off"] + 2, rect["row_off"] + 12, str(rect["index"]),
                    color="red", fontsize=7)
        return True

    def _draw_raster(self, ax, spec: FigureSpec) -> bool:
        try:
            import numpy as np  # type: ignore
            from app.preprocessing.raster_io import read_raster
        except ImportError:
            return False
        source = spec.payload.get("source_image")
        if not source or not Path(source).is_file():
            return False
        try:
            array, _ = read_raster(Path(source))  # (C, H, W)
        except Exception:  # noqa: BLE001 - guarded reader may raise if rasterio missing
            return False
        bands = spec.payload.get("band_indices")
        if bands and len(bands) == 3:
            rgb = np.stack([array[b] for b in bands], axis=-1).astype("float64")
            rgb = _stretch(rgb)
            ax.imshow(rgb)
        else:
            ax.imshow(array[spec.payload.get("band_index", 0)], cmap=spec.options.get("cmap", "gray"))
        ax.axis("off")
        return True


def _stretch(rgb):
    """Percentile stretch to [0,1] for display (numpy)."""
    import numpy as np  # type: ignore
    lo, hi = np.nanpercentile(rgb, 2), np.nanpercentile(rgb, 98)
    if hi - lo < 1e-9:
        return np.clip(rgb, 0, 1)
    return np.clip((rgb - lo) / (hi - lo), 0, 1)


def get_backend(name: str = "auto") -> PlotBackend:
    """Return a plotting backend.

    Args:
        name: ``"auto"`` (matplotlib if available, else null), ``"matplotlib"``, or ``"null"``.
    """
    if name == "null":
        return NullBackend()
    if name == "matplotlib":
        return MatplotlibBackend()
    return MatplotlibBackend() if matplotlib_available() else NullBackend()
