"""Milestone 16 verification: guardrails & acceptance harness (D5).

Runs under pytest AND standalone. Framework-free. Proves each NT's pass fixture does NOT fire and its fail
fixture DOES fire, that failures cannot silently pass, that the harness is deterministic, and that real
KPI/AC-4 acceptance stays NOT YET MEASURED. All fixtures are SYNTHETIC.
"""

from __future__ import annotations

import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.acceptance import fixtures as F  # noqa: E402
from app.acceptance import guardrails as G  # noqa: E402
from app.acceptance import run_acceptance  # noqa: E402
from app.acceptance.records import AcceptanceReport, GuardrailOutcome, NTResult  # noqa: E402
from app.acceptance.report import export_acceptance_report  # noqa: E402
from app.db.base import Database  # noqa: E402


@contextmanager
def _tmp_db():
    d = tempfile.mkdtemp(prefix="m16_")
    db = Database(f"sqlite:///{d}/t.db").create_all()
    try:
        yield db, Path(d)
    finally:
        import shutil
        db.engine.dispose()
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------------------------------
# Per-NT guardrail behaviour: pass fixture must NOT fire; fail fixture MUST fire.
# --------------------------------------------------------------------------------------------------
def test_nt1_guardrail_detects_only_hiding_summary() -> None:
    assert G.detect_aggregate_hides_subgroup(F.NT1_PASS_SUMMARY).triggered is False
    assert G.detect_aggregate_hides_subgroup(F.NT1_FAIL_SUMMARY).triggered is True


def test_nt2_snow_as_cloud() -> None:
    assert G.detect_snow_as_cloud(F.NT2_PASS).triggered is False
    d = G.detect_snow_as_cloud(F.NT2_FAIL)
    assert d.triggered is True and d.evidence["rate"] >= 0.30


def test_nt3_thin_cloud_leak() -> None:
    assert G.detect_thin_cloud_leak(F.NT3_PASS).triggered is False
    d = G.detect_thin_cloud_leak(F.NT3_FAIL)
    assert d.triggered is True and d.evidence["leaked_to_clear"] == 60


def test_nt4_misleading_map() -> None:
    assert G.detect_misleading_map(F.NT4_PASS_MAP).triggered is False
    d = G.detect_misleading_map(F.NT4_FAIL_MAP)
    assert d.triggered is True and "has_uncertainty" in d.evidence["missing"]


def test_nt4_real_map_with_full_metadata_passes() -> None:
    honest_real = {"data_regime": "REAL", "claims_real_overlay": True,
                   "has_uncertainty": True, "has_coverage": True, "has_resolution": True}
    assert G.detect_misleading_map(honest_real).triggered is False   # a REAL map that surfaces everything is fine


def test_nt2_boundary_below_threshold_does_not_trigger() -> None:
    below = F.cm([[75, 15, 5, 5], [4, 92, 2, 2], [3, 2, 93, 2], [5, 2, 3, 90]])  # 20% < 30%
    assert G.detect_snow_as_cloud(below).triggered is False


# --------------------------------------------------------------------------------------------------
# NT-5 (reuses M15 lineage): detect-before-commit + idempotent + complete lineage.
# --------------------------------------------------------------------------------------------------
def test_nt5_via_harness() -> None:
    with _tmp_db() as (db, _):
        from app.acceptance.harness import _run_nt5
        nt = _run_nt5(db)
        assert nt.passed is True
        assert nt.pass_case.triggered is False and nt.fail_case.triggered is True
        assert "rejected before commit" in nt.fail_case.action


# --------------------------------------------------------------------------------------------------
# Full harness: all NTs pass; degraded/recovery cycle; honest KPI status.
# --------------------------------------------------------------------------------------------------
def test_run_acceptance_all_pass() -> None:
    report = run_acceptance()
    assert isinstance(report, AcceptanceReport)
    assert [r.nt_id for r in report.nt_results] == ["NT-1", "NT-2", "NT-3", "NT-4", "NT-5"]
    assert report.safety_passed is True
    assert report.overall == "SAFETY_PASS_KPI_NOT_YET_MEASURED"
    assert report.kpi_overall == "NOT_YET_MEASURED"
    assert all(k["status"] == "NOT_YET_MEASURED" for k in report.kpi_status)   # never fabricated


def test_harness_drives_degraded_and_recovery() -> None:
    from app.services.integration_service import system_status
    with _tmp_db() as (db, _):
        run_acceptance(db)
        st = system_status(db)
        # NT-1..4 each entered degraded then recovered -> all resolved -> operational.
        assert st["degraded"] is False
        assert st["event_count"] == 8            # 4 DEGRADED + 4 RECOVERY


def test_harness_is_deterministic() -> None:
    assert run_acceptance().content_hash() == run_acceptance().content_hash()


def test_failures_cannot_silently_pass() -> None:
    # A fail-fixture that did NOT fire must mark the NT failed and the report SAFETY_FAIL.
    ok = GuardrailOutcome("NT-X", "pass", "req", "obs", "exp", triggered=False, correct=True)
    silent = GuardrailOutcome("NT-X", "fail", "req", "obs", "exp", triggered=False, correct=False)
    nt = NTResult("NT-X", "n", "req", pass_case=ok, fail_case=silent)
    assert nt.passed is False
    rep = AcceptanceReport(nt_results=[nt])
    assert rep.safety_passed is False and rep.overall == "SAFETY_FAIL"


def test_report_roundtrip_and_export() -> None:
    with _tmp_db() as (_db, d):
        report = run_acceptance()
        back = AcceptanceReport.from_dict(report.to_dict())
        assert back.content_hash() == report.content_hash()
        written = export_acceptance_report(report, d / "acc_report")
        assert set(written) == {"json", "csv", "md"} and all(Path(p).is_file() for p in written.values())


def test_report_has_ac_and_kpi_coverage() -> None:
    report = run_acceptance()
    assert [a["ac"] for a in report.ac_coverage] == ["AC-1", "AC-2", "AC-3", "AC-4"]
    assert len(report.kpi_status) == 13            # KPI-1..6 + KPI-E1..E7
    assert report.coverage["line_coverage_percent"] == "NOT_YET_MEASURED"   # pytest-cov deferred, honest


def _run_all() -> int:
    tests = [(n, o) for n, o in sorted(globals().items()) if n.startswith("test_") and callable(o)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn(); passed += 1; print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1; print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
