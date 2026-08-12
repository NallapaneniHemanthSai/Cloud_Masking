"""Confusing-case visualization specs (Milestone 9).

Builds **backend-independent** :class:`FigureSpec`s for a confusing case (ground truth, prediction, error
overlay) reusing the M5 visualization abstraction (colormap + overlays). **matplotlib is never imported
here** — rendering stays behind the M5 backend. Specs carry the error category / severity / sample metadata
in their options, plus a class legend. Standard-library only.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from app.failure_analysis.config import FailureAnalysisConfig
from app.failure_analysis.records import SampleFailure
from app.visualization.colormap import get_colormap
from app.visualization.overlays import legend_for, mask_spec, overlay_spec
from app.visualization.records import FigureSpec


def _with_metadata(spec: FigureSpec, metadata: dict[str, Any]) -> FigureSpec:
    """Return a copy of ``spec`` with failure metadata merged into its options (spec is frozen)."""
    return replace(spec, options={**spec.options, **metadata})


def confusing_case_specs(
    failure: SampleFailure,
    config: FailureAnalysisConfig,
    *,
    image_source: Path | None = None,
    ground_truth_source: Path | None = None,
    prediction_source: Path | None = None,
) -> dict[str, Any]:
    """Build visualization specs + legend + metadata for one confusing case.

    Sources are optional path references (no pixel data); specs are produced only for provided sources.
    """
    colormap = get_colormap("on_cloud_n" if config.mode == "binary" else "cloudsen12")
    metadata: dict[str, Any] = {
        "sample_id": failure.sample_id,
        "severity": failure.severity,
        "error_rate": failure.error_rate,
        "error_count": failure.error_count,
        "dominant_true_class": failure.dominant_true_class,
        "dominant_predicted_class": failure.dominant_predicted_class,
        "categories": list(failure.categories),
    }

    specs: dict[str, FigureSpec] = {}
    if ground_truth_source is not None:
        specs["ground_truth"] = _with_metadata(
            mask_spec(ground_truth_source, colormap, title=f"Ground truth ({failure.sample_id})"), metadata)
    if prediction_source is not None:
        specs["prediction"] = _with_metadata(
            mask_spec(prediction_source, colormap, title=f"Prediction ({failure.sample_id})"), metadata)
    if image_source is not None and prediction_source is not None:
        specs["error_overlay"] = _with_metadata(
            overlay_spec(image_source, prediction_source, colormap, alpha=0.5,
                         title=f"Error overlay ({failure.sample_id})"), metadata)

    return {
        "sample_id": failure.sample_id,
        "specs": {name: spec.to_dict() for name, spec in specs.items()},
        "legend": legend_for(colormap).to_dict(),
        "metadata": metadata,
    }
