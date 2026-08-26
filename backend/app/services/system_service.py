"""System services: version, health, metrics (Milestone 13).

Reads component versions from the single source of truth (`app.core.constants`), reports health/device, and
exposes the in-process telemetry snapshot. Standard-library only (torch probed via the guarded accessor).
"""

from __future__ import annotations

import sys
from typing import Any

from app.core import constants as C
from app.core.telemetry import get_registry


def _torch_version() -> str | None:
    try:
        from app.models._torch import torch  # guarded accessor
        return torch.__version__ if torch is not None else None
    except Exception:  # noqa: BLE001
        return None


def version_info() -> dict[str, Any]:
    """All component versions + runtime info."""
    return {
        "app_version": C.API_VERSION,
        "model_version": C.MODEL_VERSION,
        "improved_model_version": C.IMPROVED_MODEL_VERSION,
        "preprocessing_version": C.PREPROCESSING_VERSION,
        "visualization_version": C.VISUALIZATION_VERSION,
        "training_version": C.TRAINING_VERSION,
        "evaluation_version": C.EVALUATION_VERSION,
        "failure_analysis_version": C.FAILURE_ANALYSIS_VERSION,
        "comparison_version": C.COMPARISON_VERSION,
        "dataset_manifest_version": C.DATASET_MANIFEST_VERSION,
        "python": sys.version.split()[0],
        "torch": _torch_version(),
    }


def health_info(database_url: str) -> dict[str, Any]:
    """Liveness + device/database snapshot."""
    from app.models._torch import torch_available
    from app.training.seed import resolve_device
    return {"status": "ok", "torch_available": torch_available(),
            "device": resolve_device("auto"), "database": database_url}


def metrics_snapshot() -> dict[str, Any]:
    """Telemetry snapshot for ``/metrics``."""
    return get_registry().snapshot()
