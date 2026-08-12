"""Evaluation serialization helpers (Milestone 8).

Thin save/load wrappers over the records' own JSON serialisation. Deterministic; no tensors. Kept separate
so callers have a single import for persisting/loading evaluation artifacts.
"""

from __future__ import annotations

from pathlib import Path

from app.evaluation.records import EvaluationResult, EvaluationRun


def save_evaluation_run(run: EvaluationRun, path: Path) -> Path:
    """Persist an :class:`EvaluationRun` to JSON."""
    return run.save_json(Path(path))


def load_evaluation_run(path: Path) -> EvaluationRun:
    """Load an :class:`EvaluationRun` from JSON."""
    return EvaluationRun.load_json(Path(path))


def result_to_dict(result: EvaluationResult) -> dict:
    """Serialise an :class:`EvaluationResult` to a plain dict."""
    return result.to_dict()


def result_from_dict(data: dict) -> EvaluationResult:
    """Reconstruct an :class:`EvaluationResult` from a dict."""
    return EvaluationResult.from_dict(data)
