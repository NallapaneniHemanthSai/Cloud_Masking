"""Comparison serialization helpers (Milestone 11).

Thin save/load wrappers over :class:`ModelComparisonArtifact`'s own JSON serialisation, so callers have a
single import for persisting/loading comparison artifacts. Deterministic; no tensors.
"""

from __future__ import annotations

from pathlib import Path

from app.comparison.records import ModelComparisonArtifact


def save_comparison_artifact(artifact: ModelComparisonArtifact, path: Path) -> Path:
    """Persist a :class:`ModelComparisonArtifact` to JSON."""
    return artifact.save_json(Path(path))


def load_comparison_artifact(path: Path) -> ModelComparisonArtifact:
    """Load a :class:`ModelComparisonArtifact` from JSON."""
    return ModelComparisonArtifact.load_json(Path(path))


def artifact_to_dict(artifact: ModelComparisonArtifact) -> dict:
    """Serialise a :class:`ModelComparisonArtifact` to a plain dict."""
    return artifact.to_dict()


def artifact_from_dict(data: dict) -> ModelComparisonArtifact:
    """Reconstruct a :class:`ModelComparisonArtifact` from a dict."""
    return ModelComparisonArtifact.from_dict(data)
