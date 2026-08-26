"""Acceptance harness (Milestone 16 / Deliverable D5).

Proves the project's safety/acceptance properties: the five mandatory negative tests (NT-1..NT-5), each with
a deterministic **pass** fixture (must not fire) and **fail** fixture (must fire). It **reuses** M8
evaluation (confusion), M9 failure categories, and the M15 degraded-mode/recovery/lineage infrastructure —
no duplicated metric or degraded-mode system. NT-1..4 detections drive M15 degraded mode + recovery; NT-5
enforces detect-before-commit / idempotent replay / complete lineage. Fixtures are **SYNTHETIC**; real
KPI/AC-4 acceptance is reported **NOT YET MEASURED** (never fabricated), and the M11 MIXED conclusion is
untouched.

Public surface: :class:`AcceptanceReport`, :class:`NTResult`, :class:`GuardrailOutcome`,
:func:`run_acceptance`, :func:`build_acceptance_report`, :func:`export_acceptance_report`; the NT guardrails
and fixtures.
"""

from app.acceptance.guardrails import (
    Detection,
    detect_aggregate_hides_subgroup,
    detect_misleading_map,
    detect_snow_as_cloud,
    detect_thin_cloud_leak,
)
from app.acceptance.harness import run_acceptance
from app.acceptance.records import (
    AcceptanceReport,
    GuardrailOutcome,
    NTResult,
)
from app.acceptance.report import build_acceptance_report, export_acceptance_report

__all__ = [
    "AcceptanceReport",
    "NTResult",
    "GuardrailOutcome",
    "run_acceptance",
    "build_acceptance_report",
    "export_acceptance_report",
    "Detection",
    "detect_aggregate_hides_subgroup",
    "detect_snow_as_cloud",
    "detect_thin_cloud_leak",
    "detect_misleading_map",
]
