"""Exporters (Milestone 5).

Single entry points for (a) rendering a :class:`FigureSpec` to an image via a plotting backend, and (b)
exporting a :class:`Report` to files. Keeps rendering/backend-selection logic in one place (no duplication)
and always degrades gracefully — a missing plotting backend yields a metadata sidecar, never a crash.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.visualization.backends import PlotBackend, get_backend
from app.visualization.manifest import FigureManifest
from app.visualization.records import FigureSpec, RenderResult
from app.visualization.reports import Report

logger = logging.getLogger(__name__)


def render_figure(spec: FigureSpec, path: Path, *, backend: PlotBackend | None = None,
                  backend_name: str = "auto") -> RenderResult:
    """Render a single figure spec to ``path`` using a plotting backend.

    Args:
        spec: The figure to render.
        path: Output image path.
        backend: An explicit backend (overrides ``backend_name``).
        backend_name: ``"auto"`` | ``"matplotlib"`` | ``"null"``.

    Returns:
        A :class:`RenderResult` (``DEGRADED`` with a metadata sidecar when no plotting backend is usable).
    """
    backend = backend or get_backend(backend_name)
    result = backend.render(spec, Path(path))
    logger.info("render_figure: %s -> %s (%s)", spec.kind, result.status, result.backend)
    return result


def render_figure_manifested(
    spec: FigureSpec, path: Path, *, backend: PlotBackend | None = None, backend_name: str = "auto",
    created_at: str | None = None, figure_id: str | None = None, notes: str = "",
) -> tuple[RenderResult, FigureManifest]:
    """Render a figure and also produce its :class:`FigureManifest` (metadata; no plotting objects)."""
    result = render_figure(spec, path, backend=backend, backend_name=backend_name)
    manifest = FigureManifest.from_render(spec, result, figure_id=figure_id, created_at=created_at,
                                          notes=notes)
    return result, manifest


def render_all(specs: dict[str, FigureSpec], out_dir: Path, *, suffix: str = ".png",
               backend: PlotBackend | None = None, backend_name: str = "auto") -> dict[str, RenderResult]:
    """Render a mapping of ``name -> FigureSpec`` into ``out_dir`` (one backend instance reused)."""
    out_dir = Path(out_dir)
    backend = backend or get_backend(backend_name)
    return {
        name: render_figure(spec, out_dir / f"{name}{suffix}", backend=backend)
        for name, spec in specs.items()
    }


def render_all_manifested(
    specs: dict[str, FigureSpec], out_dir: Path, *, suffix: str = ".png",
    backend: PlotBackend | None = None, backend_name: str = "auto", created_at: str | None = None,
) -> dict[str, tuple[RenderResult, FigureManifest]]:
    """Render many figures, returning ``name -> (RenderResult, FigureManifest)``."""
    out_dir = Path(out_dir)
    backend = backend or get_backend(backend_name)
    return {
        name: render_figure_manifested(spec, out_dir / f"{name}{suffix}", backend=backend,
                                       created_at=created_at)
        for name, spec in specs.items()
    }


def export_report(report: Report, path_stem: Path,
                  formats: tuple[str, ...] = ("json", "md", "csv")) -> dict[str, Path]:
    """Export a report in the requested formats (thin wrapper over :meth:`Report.save`)."""
    return report.save(Path(path_stem), formats=formats)
