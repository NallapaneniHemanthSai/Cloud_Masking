"""Deterministic synthetic fixtures for the acceptance harness (Milestone 16 / D5).

Every fixture is fixed, synthetic, and labelled SYNTHETIC — no randomness, no network, no torch. Each NT
has a **pass** fixture (healthy — must NOT trigger the guardrail) and a **fail** fixture (the bad condition
— must trigger it). Confusion matrices are ``rows=true, cols=pred`` in the canonical CloudSEN12 class order.
"""

from __future__ import annotations

from typing import Any

from app.evaluation.confusion import ConfusionMatrix

CLASS_NAMES = ["clear", "thick_cloud", "thin_cloud", "cloud_shadow"]   # canonical order (indices 0..3)


def cm(matrix: list[list[int]]) -> ConfusionMatrix:
    """Build a 4-class CloudSEN12 confusion matrix (rows=true, cols=pred)."""
    return ConfusionMatrix(4, [row[:] for row in matrix], list(CLASS_NAMES))


# --- NT-1: aggregate hides a failing subgroup (evaluation summaries) -------------------------------
NT1_PASS_SUMMARY: dict[str, Any] = {
    "pixel_accuracy": 0.80, "macro_iou": 0.62, "thin_cloud_iou": 0.58,
    "per_class_iou": {"clear": 0.70, "thick_cloud": 0.66, "thin_cloud": 0.58, "cloud_shadow": 0.55},
}
NT1_FAIL_SUMMARY: dict[str, Any] = {
    "pixel_accuracy": 0.92, "macro_iou": 0.55, "thin_cloud_iou": 0.03,
    "per_class_iou": {"clear": 0.90, "thick_cloud": 0.85, "thin_cloud": 0.03, "cloud_shadow": 0.02},
}

# --- NT-2: snow (true 'clear') masked as cloud (confusion; clear row = index 0) --------------------
#   pass: only 5% of clear predicted as cloud;   fail: 65% of clear predicted as cloud.
NT2_PASS = cm([[90, 3, 2, 5], [4, 92, 2, 2], [3, 2, 93, 2], [5, 2, 3, 90]])
NT2_FAIL = cm([[30, 50, 15, 5], [4, 92, 2, 2], [3, 2, 93, 2], [5, 2, 3, 90]])

# --- NT-3: thin cloud leaking into analysis (predicted 'clear'; thin row = index 2) ---------------
#   pass: 5% of thin leaks to clear;   fail: 60% of thin leaks to clear.
NT3_PASS = cm([[90, 3, 2, 5], [4, 92, 2, 2], [5, 2, 90, 3], [5, 2, 3, 90]])
NT3_FAIL = cm([[90, 3, 2, 5], [4, 92, 2, 2], [60, 5, 30, 5], [5, 2, 3, 90]])

# --- NT-4: a map hides uncertainty / coverage / resolution ----------------------------------------
#   pass: a clearly-labelled DEMO base map (does not claim a real overlay) — honest (matches M14 MapViewer).
NT4_PASS_MAP: dict[str, Any] = {
    "data_regime": "DEMO", "claims_real_overlay": False,
    "has_uncertainty": False, "has_coverage": False, "has_resolution": False,
}
#   fail: a map presented as REAL that omits uncertainty + coverage.
NT4_FAIL_MAP: dict[str, Any] = {
    "data_regime": "REAL", "claims_real_overlay": True,
    "has_uncertainty": False, "has_coverage": False, "has_resolution": True,
}

# --- NT-5: field/authoritative observations do not support the inference (records) ----------------
#   pass: a valid lineage record;   fail: an invalid record (must be rejected BEFORE commit).
NT5_VALID_RECORD: dict[str, Any] = {"artifact_type": "evaluation", "content_hash": "ev-valid-001"}
NT5_INVALID_RECORD: dict[str, Any] = {"artifact_type": "", "content_hash": "ev-invalid"}  # missing type
