"""Typed acceptance-harness records (Milestone 16 / D5).

Strongly-typed, deterministically-serialisable records for the negative-test acceptance harness. Every
guardrail outcome is fully explainable (requirement / observed / expected / evidence / action). Content
hashing is deterministic (ignores timestamps). Standard-library only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import ACCEPTANCE_VERSION
from app.utils.hashing import stable_hash

# Honest status labels (mirrors the rest of the project).
SYNTHETIC = "SYNTHETIC"
NOT_YET_MEASURED = "NOT_YET_MEASURED"
DEFERRED = "DEFERRED"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class GuardrailOutcome:
    """The outcome of running one guardrail against one (synthetic) fixture."""

    nt_id: str
    fixture: str                 # "pass" | "fail"
    requirement: str
    observed: str
    expected: str
    triggered: bool              # did the guardrail fire?
    correct: bool                # did it behave correctly for this fixture?
    action: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    data_regime: str = SYNTHETIC

    def to_dict(self) -> dict[str, Any]:
        return {
            "nt_id": self.nt_id, "fixture": self.fixture, "requirement": self.requirement,
            "observed": self.observed, "expected": self.expected, "triggered": self.triggered,
            "correct": self.correct, "action": self.action, "evidence": self.evidence,
            "data_regime": self.data_regime,
        }


@dataclass
class NTResult:
    """One negative test = its pass fixture (must not fire) + fail fixture (must fire)."""

    nt_id: str
    name: str
    requirement: str
    pass_case: GuardrailOutcome
    fail_case: GuardrailOutcome
    owner: str = ""

    @property
    def passed(self) -> bool:
        return self.pass_case.correct and self.fail_case.correct

    def to_dict(self) -> dict[str, Any]:
        return {
            "nt_id": self.nt_id, "name": self.name, "requirement": self.requirement, "owner": self.owner,
            "passed": self.passed, "pass_case": self.pass_case.to_dict(),
            "fail_case": self.fail_case.to_dict(),
        }


@dataclass
class AcceptanceReport:
    """The D5 acceptance report — NT results + AC/KPI status + coverage inventory."""

    nt_results: list[NTResult] = field(default_factory=list)
    ac_coverage: list[dict[str, Any]] = field(default_factory=list)
    kpi_status: list[dict[str, Any]] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    acceptance_version: str = ACCEPTANCE_VERSION
    created_at: str = field(default_factory=_now)
    notes: str = ""

    @property
    def safety_passed(self) -> bool:
        """True only when every NT passes (both fixtures behave correctly)."""
        return bool(self.nt_results) and all(r.passed for r in self.nt_results)

    @property
    def kpi_overall(self) -> str:
        """Real KPI acceptance status (honest — never fabricated)."""
        return NOT_YET_MEASURED

    @property
    def overall(self) -> str:
        if not self.safety_passed:
            return "SAFETY_FAIL"
        return "SAFETY_PASS_KPI_NOT_YET_MEASURED"

    def failed_nts(self) -> list[str]:
        return [r.nt_id for r in self.nt_results if not r.passed]

    def _identity(self) -> dict[str, Any]:
        """Deterministic content (ignores created_at/notes)."""
        return {
            "acceptance_version": self.acceptance_version,
            "nt_results": [r.to_dict() for r in self.nt_results],
            "ac_coverage": self.ac_coverage, "kpi_status": self.kpi_status,
            "overall": self.overall,
        }

    def content_hash(self) -> str:
        return stable_hash(self._identity())

    def to_dict(self) -> dict[str, Any]:
        return {
            "acceptance_version": self.acceptance_version,
            "overall": self.overall, "safety_passed": self.safety_passed, "kpi_overall": self.kpi_overall,
            "failed_nts": self.failed_nts(),
            "nt_results": [r.to_dict() for r in self.nt_results],
            "ac_coverage": self.ac_coverage, "kpi_status": self.kpi_status, "coverage": self.coverage,
            "created_at": self.created_at, "notes": self.notes, "content_hash": self.content_hash(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AcceptanceReport":
        def _outcome(o: dict[str, Any]) -> GuardrailOutcome:
            return GuardrailOutcome(
                nt_id=o["nt_id"], fixture=o["fixture"], requirement=o["requirement"],
                observed=o["observed"], expected=o["expected"], triggered=bool(o["triggered"]),
                correct=bool(o["correct"]), action=o.get("action", ""),
                evidence=dict(o.get("evidence", {}) or {}), data_regime=o.get("data_regime", SYNTHETIC))
        results = [NTResult(nt_id=r["nt_id"], name=r["name"], requirement=r["requirement"],
                            owner=r.get("owner", ""), pass_case=_outcome(r["pass_case"]),
                            fail_case=_outcome(r["fail_case"])) for r in d.get("nt_results", [])]
        return cls(nt_results=results, ac_coverage=list(d.get("ac_coverage", []) or []),
                   kpi_status=list(d.get("kpi_status", []) or []), coverage=dict(d.get("coverage", {}) or {}),
                   acceptance_version=d.get("acceptance_version", ACCEPTANCE_VERSION),
                   created_at=d.get("created_at", ""), notes=d.get("notes", ""))
