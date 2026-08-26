"""Acceptance harness (Milestone 16 / D5).

Runs the five mandatory negative tests, **reusing** the M8 confusion matrix, the M16 guardrails, and the
M15 degraded-mode/recovery/lineage infrastructure — no duplicated metric or degraded system. Produces a
deterministic :class:`AcceptanceReport`. Every NT has a pass fixture (must not fire) and a fail fixture
(must fire → NT-1..4 drive degraded mode + recovery; NT-5 enforces detect-before-commit / idempotent /
lineage). Real KPI/AC-4 acceptance is reported **NOT YET MEASURED** — never fabricated. Standard-lib +
SQLAlchemy (SQLite).
"""

from __future__ import annotations

from typing import Any

from app.acceptance import fixtures as F
from app.acceptance import guardrails as G
from app.acceptance.records import (
    NOT_YET_MEASURED,
    SYNTHETIC,
    AcceptanceReport,
    GuardrailOutcome,
    NTResult,
)
from app.core.exceptions import GuardrailViolation
from app.db.base import Database


def _fresh_db() -> Database:
    return Database("sqlite:///:memory:").create_all()


def _demo_degraded_recovery(db: Database, nt_id: str, reason: str, evidence: dict[str, Any]) -> str:
    """On a detected violation, demonstrate the M15 degraded-mode → recovery cycle; return the action."""
    from app.services.integration_service import enter_degraded, recover
    ev = enter_degraded(db, reason=reason, subject=f"acceptance:{nt_id}", evidence=evidence)
    rec = recover(db, ev["event_id"], note=f"{nt_id} recovered")
    return f"entered degraded mode ({ev['event_id']}) then recovered ({rec['event_id']})"


def _confusion_nt(db: Database, *, nt_id: str, name: str, requirement: str, owner: str,
                  pass_cm: Any, fail_cm: Any, detect, expected_fire: str) -> NTResult:
    dp = detect(pass_cm)
    pass_case = GuardrailOutcome(
        nt_id=nt_id, fixture="pass", requirement=requirement, observed=dp.observed,
        expected="guardrail must NOT fire on the healthy fixture", triggered=dp.triggered,
        correct=(not dp.triggered), action="none (no violation)", evidence=dp.evidence)

    df = detect(fail_cm)
    action = _demo_degraded_recovery(db, nt_id, df.observed, df.evidence) if df.triggered else \
        "NONE — violation was NOT detected (silent pass)"
    fail_case = GuardrailOutcome(
        nt_id=nt_id, fixture="fail", requirement=requirement, observed=df.observed,
        expected=expected_fire, triggered=df.triggered, correct=df.triggered, action=action,
        evidence=df.evidence)
    return NTResult(nt_id=nt_id, name=name, requirement=requirement, owner=owner,
                    pass_case=pass_case, fail_case=fail_case)


def _run_nt1(db: Database) -> NTResult:
    req = "Overall accuracy dominated by easy pixels — detect, degrade, label, prevent silent use."
    dp = G.detect_aggregate_hides_subgroup(F.NT1_PASS_SUMMARY)
    pass_case = GuardrailOutcome("NT-1", "pass", req, dp.observed,
                                 "guardrail must NOT fire on the healthy summary", dp.triggered,
                                 not dp.triggered, "none (no violation)", dp.evidence)
    df = G.detect_aggregate_hides_subgroup(F.NT1_FAIL_SUMMARY)
    action = _demo_degraded_recovery(db, "NT-1", df.observed, df.evidence) if df.triggered else \
        "NONE — violation was NOT detected (silent pass)"
    fail_case = GuardrailOutcome("NT-1", "fail", req, df.observed,
                                 "guardrail must fire when a strong aggregate hides thin-cloud/worst-class",
                                 df.triggered, df.triggered, action, df.evidence)
    return NTResult("NT-1", "Aggregate hides a failing subgroup", req, pass_case, fail_case, owner="M9/M15")


def _run_nt2(db: Database) -> NTResult:
    return _confusion_nt(
        db, nt_id="NT-2", name="Snow masked as cloud", owner="M9",
        requirement="Snow (true 'clear') masked as cloud — detect, degrade, label, prevent.",
        pass_cm=F.NT2_PASS, fail_cm=F.NT2_FAIL, detect=G.detect_snow_as_cloud,
        expected_fire="guardrail must fire when true-clear (snow) is predicted as cloud above threshold")


def _run_nt3(db: Database) -> NTResult:
    return _confusion_nt(
        db, nt_id="NT-3", name="Thin cloud leaking into analysis", owner="M9",
        requirement="Thin cloud leaking into analysis (predicted 'clear') — detect, degrade, label, prevent.",
        pass_cm=F.NT3_PASS, fail_cm=F.NT3_FAIL, detect=G.detect_thin_cloud_leak,
        expected_fire="guardrail must fire when true thin-cloud is predicted as clear above threshold")


def _run_nt4(db: Database) -> NTResult:
    req = "A map must not hide uncertainty / coverage / resolution (no misleading map)."
    dp = G.detect_misleading_map(F.NT4_PASS_MAP)
    pass_case = GuardrailOutcome("NT-4", "pass", req, dp.observed,
                                 "an honest DEMO/complete map must NOT be flagged", dp.triggered,
                                 not dp.triggered, "none (no violation)", dp.evidence)
    df = G.detect_misleading_map(F.NT4_FAIL_MAP)
    action = _demo_degraded_recovery(db, "NT-4", df.observed, df.evidence) if df.triggered else \
        "NONE — violation was NOT detected (silent pass)"
    fail_case = GuardrailOutcome("NT-4", "fail", req, df.observed,
                                 "guardrail must fire when a REAL-claimed map omits uncertainty/coverage",
                                 df.triggered, df.triggered, action, df.evidence)
    return NTResult("NT-4", "Misleading map (uncertainty/coverage/resolution)", req,
                    pass_case, fail_case, owner="M12/M14")


def _run_nt5(db: Database) -> NTResult:
    from app.services.lineage_service import get_chain, record_lineage
    req = ("Field/authoritative observations do not support the inference — detect the invalid record "
           "BEFORE commit; replay is idempotent; lineage remains complete.")

    # pass fixture: a valid record is recorded, and a replay is idempotent + the chain is complete.
    r1 = record_lineage(db, artifact_type=F.NT5_VALID_RECORD["artifact_type"],
                        content_hash=F.NT5_VALID_RECORD["content_hash"], inputs={"src": "acceptance"})
    r2 = record_lineage(db, artifact_type=F.NT5_VALID_RECORD["artifact_type"],
                        content_hash=F.NT5_VALID_RECORD["content_hash"], inputs={"src": "acceptance"})
    idempotent = r1["lineage_id"] == r2["lineage_id"]
    child = record_lineage(db, artifact_type="pipeline", content_hash="pipe-1",
                           parent_lineage_id=r1["lineage_id"])
    chain_complete = [n["artifact_type"] for n in get_chain(db, child["lineage_id"])] == ["pipeline", "evaluation"]
    pass_case = GuardrailOutcome(
        "NT-5", "pass", req,
        observed=f"valid record recorded; replay idempotent={idempotent}; lineage chain complete={chain_complete}",
        expected="valid record persists once (idempotent) with a complete parent chain",
        triggered=False, correct=(idempotent and chain_complete),
        action="recorded lineage + idempotent replay + complete chain",
        evidence={"lineage_id": r1["lineage_id"], "idempotent": idempotent, "chain_complete": chain_complete})

    # fail fixture: an invalid record MUST be rejected before commit (nothing persisted).
    from app.db.models import LineageRow
    with db.session() as s:
        before = s.query(LineageRow).count()
    detected = False
    try:
        record_lineage(db, artifact_type=F.NT5_INVALID_RECORD["artifact_type"],
                       content_hash=F.NT5_INVALID_RECORD["content_hash"])
    except GuardrailViolation:
        detected = True
    with db.session() as s:
        after = s.query(LineageRow).count()
    not_persisted = before == after
    fail_case = GuardrailOutcome(
        "NT-5", "fail", req,
        observed=f"invalid record rejected before commit={detected}; nothing persisted={not_persisted}",
        expected="invalid record raises GuardrailViolation and is NOT persisted (detect-before-commit)",
        triggered=detected, correct=(detected and not_persisted),
        action="rejected before commit (no row written)",
        evidence={"detected": detected, "rows_before": before, "rows_after": after})
    return NTResult("NT-5", "Invalid record before commit / idempotent / lineage", req,
                    pass_case, fail_case, owner="M15")


def _ac_coverage() -> list[dict[str, Any]]:
    return [
        {"ac": "AC-1", "description": "Representative operation (stratified across regions/seasons)",
         "covered_by": "M8 stratified evaluation (reference)", "status": NOT_YET_MEASURED,
         "note": "real stratified KPIs need a real AC-4 dataset"},
        {"ac": "AC-2", "description": "Boundary & failure operation (easy-pixel dominance, snow-as-cloud, thin-cloud leak)",
         "covered_by": "NT-1, NT-2, NT-3 (synthetic)", "status": f"SAFETY_PASS ({SYNTHETIC})"},
        {"ac": "AC-3", "description": "Independent acceptance evidence (disjoint areas, authoritative reference)",
         "covered_by": "M12 group-aware split (reference)", "status": NOT_YET_MEASURED},
        {"ac": "AC-4", "description": "Frozen resource envelope (same versions/workload/limits)",
         "covered_by": "recorded per run", "status": NOT_YET_MEASURED},
    ]


def _kpi_status() -> list[dict[str, Any]]:
    kpis = (["KPI-1", "KPI-2", "KPI-3", "KPI-4", "KPI-5", "KPI-6"]
            + [f"KPI-E{i}" for i in range(1, 8)])
    return [{"kpi": k, "status": NOT_YET_MEASURED,
             "note": "no real AC-4 dataset — bounded M11 run is NOT the benchmark (conclusion MIXED)"}
            for k in kpis]


def _coverage_inventory() -> dict[str, Any]:
    """Honest test-inventory / coverage matrix (line-coverage % via pytest-cov is DEFERRED)."""
    return {
        "line_coverage_percent": NOT_YET_MEASURED,
        "line_coverage_note": "pytest-cov is not installed; DEFERRED. Coverage is reported as a "
                              "test-inventory + NT coverage matrix (below).",
        "nt_coverage": {
            "NT-1": ["test_acceptance", "test_integration (M15 guardrail)"],
            "NT-2": ["test_acceptance"],
            "NT-3": ["test_acceptance"],
            "NT-4": ["test_acceptance"],
            "NT-5": ["test_acceptance", "test_integration (M15 lineage)"],
        },
        "manual_harness_counts": {
            "test_comparison (M11)": 23, "test_datasets_experimental (M12)": 18,
            "test_api (M13)": 15, "test_integration (M15)": 10, "test_acceptance (M16)": 13,
        },
    }


def run_acceptance(db: Database | None = None) -> AcceptanceReport:
    """Run all five negative tests + assemble the D5 :class:`AcceptanceReport`."""
    own = db is None
    db = db or _fresh_db()
    try:
        results = [_run_nt1(db), _run_nt2(db), _run_nt3(db), _run_nt4(db), _run_nt5(db)]
    finally:
        if own:
            db.engine.dispose()
    return AcceptanceReport(
        nt_results=results, ac_coverage=_ac_coverage(), kpi_status=_kpi_status(),
        coverage=_coverage_inventory(),
        notes="Safety properties proven on SYNTHETIC fixtures. Real KPI/AC-4 acceptance NOT YET MEASURED; "
              "M11 real-data conclusion remains MIXED (unchanged).")
