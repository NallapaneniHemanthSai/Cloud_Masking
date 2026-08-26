"""Integration: degraded mode, recovery & end-to-end wiring (Milestone 15).

Wires the long-declared :class:`GuardrailViolation` to a **degraded mode** and adds an explicit **recovery**
action with retained evidence (FR-7 / NFR-6), plus an end-to-end pipeline that ties evaluation → guardrail →
lineage (reusing M8 + the M15 lineage service). Degraded/recovery events are persisted (the recovery log)
and idempotent. Standard-library + SQLAlchemy; torch only for the optional prediction step.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.db.base import Database
from app.db.models import SystemEventRow
from app.services import evaluation_service
from app.services.lineage_service import idempotent_get_or_create, record_lineage
from app.utils.hashing import stable_hash

logger = logging.getLogger(__name__)

DEGRADED = "DEGRADED"
RECOVERY = "RECOVERY"


@dataclass
class GuardrailReport:
    """Outcome of the 'aggregate hides a failing subgroup' guardrail (FR-7 / NT-1 family)."""

    passed: bool
    reasons: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "reasons": self.reasons, "evidence": self.evidence}


def check_aggregate_hides_subgroup(summary: dict[str, Any], *, min_thin_iou: float = 0.15,
                                   worst_floor: float = 0.05, macro_ok: float = 0.5) -> GuardrailReport:
    """Detect a strong aggregate concealing a failing critical subgroup (esp. thin cloud).

    Purely a *detection* over an evaluation summary — it never fabricates metrics; it only inspects the
    ones already computed by M8. Triggering it is the signal to enter degraded mode.
    """
    reasons: list[str] = []
    pa = summary.get("pixel_accuracy")
    thin = summary.get("thin_cloud_iou")
    macro = summary.get("macro_iou")
    per = summary.get("per_class_iou") or {}

    if pa is not None and pa >= 0.75 and (thin is None or thin < min_thin_iou):
        reasons.append(f"pixel_accuracy {pa:.3f} is high but thin_cloud IoU ({thin}) < {min_thin_iou} "
                       "— aggregate hides the primary (thin-cloud) subgroup.")
    defined = {k: v for k, v in per.items() if v is not None}
    if defined:
        worst_name = min(defined, key=lambda k: defined[k])
        if defined[worst_name] < worst_floor and (macro or 0) >= macro_ok:
            reasons.append(f"macro IoU ({macro}) acceptable but worst class '{worst_name}' IoU "
                           f"{defined[worst_name]:.3f} < {worst_floor}.")
    return GuardrailReport(passed=not reasons, reasons=reasons, evidence=summary)


def enter_degraded(db: Database, *, reason: str, subject: str,
                   evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Record (idempotently) a DEGRADED event — labelled evidence, retained; prevents silent use."""
    event_id = "evt-" + stable_hash({"kind": DEGRADED, "subject": subject, "reason": reason})[:12]
    row, created = idempotent_get_or_create(
        db, model=SystemEventRow, key_field="event_id", key_value=event_id,
        build=lambda: SystemEventRow(event_id=event_id, kind=DEGRADED, reason=reason, subject=subject,
                                     evidence=json.dumps(evidence or {}), resolved=False))
    if created:
        logger.warning("DEGRADED MODE entered [%s] subject=%s reason=%s", event_id, subject, reason)
    return row


def recover(db: Database, degraded_event_id: str, *, note: str = "") -> dict[str, Any]:
    """Resolve a degraded event and append a RECOVERY event (the recovery log). Idempotent."""
    from app.core.exceptions import CloudMaskingError
    with db.session() as s:
        deg = s.query(SystemEventRow).filter(
            SystemEventRow.event_id == degraded_event_id, SystemEventRow.kind == DEGRADED).one_or_none()
        if deg is None:
            raise CloudMaskingError(f"No degraded event {degraded_event_id} to recover.")
        deg.resolved = True
    rec_id = "evt-" + stable_hash({"kind": RECOVERY, "resolves": degraded_event_id})[:12]
    row, created = idempotent_get_or_create(
        db, model=SystemEventRow, key_field="event_id", key_value=rec_id,
        build=lambda: SystemEventRow(event_id=rec_id, kind=RECOVERY,
                                     reason=note or f"recovered {degraded_event_id}",
                                     subject=degraded_event_id, resolved=True,
                                     resolves_event_id=degraded_event_id,
                                     evidence=json.dumps({"restored": "accepted versions", "note": note})))
    if created:
        logger.info("RECOVERY [%s] resolved degraded event %s", rec_id, degraded_event_id)
    return row


def system_status(db: Database) -> dict[str, Any]:
    """Operational unless any DEGRADED event is unresolved. Includes active events + lineage count."""
    from app.db.models import LineageRow
    with db.session() as s:
        active = s.query(SystemEventRow).filter(
            SystemEventRow.kind == DEGRADED, SystemEventRow.resolved.is_(False)).all()
        active_events = [e.to_dict() for e in active]
        total_events = s.query(SystemEventRow).count()
        lineage_count = s.query(LineageRow).count()
    degraded = len(active_events) > 0
    return {"status": "degraded" if degraded else "operational", "degraded": degraded,
            "active_degraded_events": active_events, "event_count": total_events,
            "lineage_count": lineage_count}


# --- crafted DEMO summary that deliberately trips the guardrail (clearly labelled) -----------------
_DEMO_HIDING_SUMMARY: dict[str, Any] = {
    "pixel_accuracy": 0.92, "macro_iou": 0.55, "thin_cloud_iou": 0.03,
    "per_class_iou": {"clear": 0.90, "thick_cloud": 0.85, "thin_cloud": 0.03, "cloud_shadow": 0.02},
    "data_regime": "DEMO",
}


def run_masking_pipeline(db: Database, *, seed: int = 0, with_prediction: bool = True,
                         inject_guardrail_failure: bool = False) -> dict[str, Any]:
    """End-to-end demonstration: (optional) predict → evaluate → guardrail → lineage → status.

    All quantities are **SYNTHETIC / VALIDATION ONLY** (or a labelled **DEMO** injection when
    ``inject_guardrail_failure`` is set to exercise degraded mode). No real-data metric is produced.
    """
    from app.core import constants as C

    versions = {"evaluation_version": C.EVALUATION_VERSION, "model_version": C.MODEL_VERSION,
                "api_version": C.API_VERSION}
    lineage: list[dict[str, Any]] = []
    parent: str | None = None
    prediction: dict[str, Any] | None = None

    # 1) optional prediction (torch-guarded)
    if with_prediction:
        from app.models._torch import torch_available
        if torch_available():
            from app.services import prediction_service
            prediction = prediction_service.run_prediction(db, synthetic=True, patch_size=32, device="cpu")
            lin = record_lineage(db, artifact_type="prediction", content_hash=prediction["prediction_id"],
                                 artifact_ref=prediction["prediction_id"], inputs=versions,
                                 notes="SYNTHETIC prediction")
            parent = lin["lineage_id"]
            lineage.append(lin)

    # 2) evaluation (M8, synthetic) + lineage (child of the prediction)
    ev = evaluation_service.run_evaluation(db, mode="multiclass", split="test", seed=seed, synthetic=True)
    lin_eval = record_lineage(db, artifact_type="evaluation", content_hash=ev["evaluation_id"],
                              artifact_ref=ev["evaluation_id"], parent_lineage_id=parent, inputs=versions,
                              notes="SYNTHETIC evaluation")
    lineage.append(lin_eval)

    # 3) guardrail → degraded mode if a strong aggregate hides a failing subgroup
    checked = dict(_DEMO_HIDING_SUMMARY) if inject_guardrail_failure else ev
    report = check_aggregate_hides_subgroup(checked)
    degraded_event: dict[str, Any] | None = None
    if not report.passed:
        degraded_event = enter_degraded(
            db, reason="; ".join(report.reasons), subject=f"evaluation:{ev['evaluation_id']}",
            evidence={"guardrail": report.to_dict(), "demo_injected": inject_guardrail_failure})

    status = system_status(db)
    return {
        "data_regime": "DEMO" if inject_guardrail_failure else "SYNTHETIC",
        "prediction": prediction, "evaluation": ev, "lineage": lineage,
        "guardrail_passed": report.passed, "guardrail_reasons": report.reasons,
        "degraded_event": degraded_event, "status": status,
        "note": ("A DEMO summary was injected to exercise degraded mode — not a real result."
                 if inject_guardrail_failure else "Healthy synthetic end-to-end run."),
    }
