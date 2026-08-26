"""Negative-test guardrails (Milestone 16 / D5).

Detection logic for NT-1..NT-4. **Reuses** the M8 confusion matrix and the M15 aggregate-hides-subgroup
guardrail — no duplicated metric math and no second degraded-mode system. Each check returns a
:class:`Detection` (did the guardrail fire, what was observed, evidence). NT-5 is enforced in the harness
via the M15 lineage service (detect-before-commit / idempotent / lineage). Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import CloudClass
from app.evaluation.confusion import ConfusionMatrix

_CLEAR = int(CloudClass.CLEAR)          # snow / bright surfaces are labelled clear
_THICK = int(CloudClass.THICK_CLOUD)
_THIN = int(CloudClass.THIN_CLOUD)


@dataclass
class Detection:
    """Outcome of one guardrail check on one fixture."""

    triggered: bool
    observed: str
    evidence: dict[str, Any] = field(default_factory=dict)


# --- NT-1: aggregate hides a failing subgroup (reuse M15) -----------------------------------------
def detect_aggregate_hides_subgroup(summary: dict[str, Any]) -> Detection:
    from app.services.integration_service import check_aggregate_hides_subgroup
    report = check_aggregate_hides_subgroup(summary)
    return Detection(
        triggered=not report.passed,
        observed="; ".join(report.reasons) if report.reasons else "aggregate does not hide any subgroup",
        evidence={"guardrail": report.to_dict()})


# --- NT-2: snow (true 'clear') masked as cloud ----------------------------------------------------
def detect_snow_as_cloud(cm: ConfusionMatrix, *, threshold: float = 0.30) -> Detection:
    support = cm.support(_CLEAR)
    predicted_as_cloud = cm.matrix[_CLEAR][_THICK] + cm.matrix[_CLEAR][_THIN]
    rate = (predicted_as_cloud / support) if support > 0 else 0.0
    return Detection(
        triggered=rate >= threshold,
        observed=f"{rate:.1%} of true clear pixels (incl. snow) predicted as cloud",
        evidence={"clear_support": support, "predicted_as_cloud": predicted_as_cloud,
                  "rate": round(rate, 6), "threshold": threshold})


# --- NT-3: thin cloud leaking into analysis (predicted 'clear') -----------------------------------
def detect_thin_cloud_leak(cm: ConfusionMatrix, *, threshold: float = 0.30) -> Detection:
    support = cm.support(_THIN)
    leaked_to_clear = cm.matrix[_THIN][_CLEAR]
    rate = (leaked_to_clear / support) if support > 0 else 0.0
    return Detection(
        triggered=rate >= threshold,
        observed=f"{rate:.1%} of true thin-cloud pixels predicted as clear (leaks into analysis)",
        evidence={"thin_cloud_support": support, "leaked_to_clear": leaked_to_clear,
                  "rate": round(rate, 6), "threshold": threshold})


# --- NT-4: a map hides uncertainty / coverage / resolution ----------------------------------------
def detect_misleading_map(map_meta: dict[str, Any]) -> Detection:
    regime = str(map_meta.get("data_regime", "")).upper()
    claims_real = bool(map_meta.get("claims_real_overlay")) or regime == "REAL"
    surfaces = {k: bool(map_meta.get(k)) for k in ("has_uncertainty", "has_coverage", "has_resolution")}
    missing = [k for k, present in surfaces.items() if not present]
    # A map presented as REAL must surface uncertainty AND coverage AND resolution; otherwise it misleads.
    misleading = claims_real and bool(missing)
    return Detection(
        triggered=misleading,
        observed=(f"map claims a REAL overlay but omits {missing}" if misleading
                  else "map surfaces uncertainty/coverage/resolution or is clearly DEMO/SYNTHETIC"),
        evidence={"data_regime": regime, "claims_real_overlay": claims_real, **surfaces,
                  "missing": missing})
