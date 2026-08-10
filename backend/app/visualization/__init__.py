"""Visualization & exploratory data analysis (Milestone 5).

Reusable, ML-independent visualization and EDA — no models/training/inference/evaluation code. Plotting is
backend-independent: callers exchange serialisable :class:`FigureSpec` / :class:`RenderResult` objects and
never touch plotting-library classes. matplotlib is a guarded optional dependency; when it is absent, the
package still produces reports, statistics, and figure metadata (graceful degradation).

Modules:

* :mod:`app.visualization.records` — FigureSpec, RenderResult, Legend.
* :mod:`app.visualization.backends` — PlotBackend abstraction (NullBackend, MatplotlibBackend, get_backend).
* :mod:`app.visualization.colormap` — class colour mapping + legends.
* :mod:`app.visualization.statistics` — deterministic dataset/patch/split statistics.
* :mod:`app.visualization.inspection` — dataset inspection report.
* :mod:`app.visualization.bands` / :mod:`.overlays` / :mod:`.patches` — figure spec builders.
* :mod:`app.visualization.plotting` — chart spec builders.
* :mod:`app.visualization.reports` — Report model + JSON/CSV/Markdown export + builders.
* :mod:`app.visualization.qc` — quality-control report.
* :mod:`app.visualization.manifest` — :class:`FigureManifest` (per-figure metadata) + ``stable_hash``.
* :mod:`app.visualization.session` — :class:`VisualizationSession` (primary workflow object).
* :mod:`app.visualization.exporters` — render + report export entry points.
"""

from app.visualization.manifest import FigureManifest, stable_hash
from app.visualization.records import FigureSpec, Legend, RenderResult
from app.visualization.reports import Report, ReportSection
from app.visualization.session import VisualizationSession, build_session

__all__ = [
    "FigureSpec",
    "RenderResult",
    "Legend",
    "Report",
    "ReportSection",
    "FigureManifest",
    "stable_hash",
    "VisualizationSession",
    "build_session",
]
