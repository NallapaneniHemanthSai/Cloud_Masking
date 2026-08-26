"""Milestone 15 verification: integration — degraded mode, recovery & NT-5 (lineage / idempotent replay).

Runs under pytest AND standalone (``python backend/tests/test_integration.py``). Framework-free (no httpx).
All results here are SYNTHETIC / DEMO — no real-data metric is produced.
"""

from __future__ import annotations

import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.exceptions import CloudMaskingError, GuardrailViolation  # noqa: E402
from app.db.base import Database  # noqa: E402
from app.db.models import LineageRow, SystemEventRow  # noqa: E402
from app.services import integration_service as I  # noqa: E402
from app.services import lineage_service as L  # noqa: E402


@contextmanager
def assert_raises(exc_type):
    try:
        yield
    except exc_type:
        return
    except Exception as other:  # noqa: BLE001
        raise AssertionError(f"expected {exc_type.__name__}, got {type(other).__name__}: {other}")
    raise AssertionError(f"expected {exc_type.__name__}, but no exception was raised")


@contextmanager
def _tmp_db():
    d = tempfile.mkdtemp(prefix="m15_")
    db = Database(f"sqlite:///{d}/t.db").create_all()
    try:
        yield db
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def _count(db, model) -> int:
    with db.session() as s:
        return s.query(model).count()


# --------------------------------------------------------------------------------------------------
# NT-5 (a): detect an invalid record BEFORE commit — nothing is persisted.
# --------------------------------------------------------------------------------------------------
def test_nt5_invalid_record_detected_before_commit() -> None:
    with _tmp_db() as db:
        with assert_raises(GuardrailViolation):
            L.record_lineage(db, artifact_type="", content_hash="abc")   # missing type
        with assert_raises(GuardrailViolation):
            L.record_lineage(db, artifact_type="evaluation", content_hash="")  # missing hash
        with assert_raises(GuardrailViolation):
            L.record_lineage(db, artifact_type="evaluation", content_hash="h", parent_lineage_id="lin-nope")
        assert _count(db, LineageRow) == 0            # detect-before-commit: no partial rows


def test_idempotent_get_or_create_validate_runs_before_write() -> None:
    with _tmp_db() as db:
        def bad_validate() -> None:
            raise GuardrailViolation("nope")
        with assert_raises(GuardrailViolation):
            L.idempotent_get_or_create(
                db, model=SystemEventRow, key_field="event_id", key_value="evt-x",
                validate=bad_validate, build=lambda: SystemEventRow(event_id="evt-x", kind="DEGRADED"))
        assert _count(db, SystemEventRow) == 0


# --------------------------------------------------------------------------------------------------
# NT-5 (b): replay is idempotent — same operation -> one row, same id.
# --------------------------------------------------------------------------------------------------
def test_nt5_idempotent_replay() -> None:
    with _tmp_db() as db:
        a = L.record_lineage(db, artifact_type="evaluation", content_hash="hash-1", inputs={"v": 1})
        b = L.record_lineage(db, artifact_type="evaluation", content_hash="hash-1", inputs={"v": 1})
        c = L.record_lineage(db, artifact_type="evaluation", content_hash="hash-1", inputs={"v": 1})
        assert a["lineage_id"] == b["lineage_id"] == c["lineage_id"]
        assert _count(db, LineageRow) == 1            # three replays, one row


# --------------------------------------------------------------------------------------------------
# NT-5 (c): lineage is complete — a queryable parent chain.
# --------------------------------------------------------------------------------------------------
def test_nt5_complete_lineage_chain() -> None:
    with _tmp_db() as db:
        root = L.record_lineage(db, artifact_type="dataset", content_hash="ds-1")
        pred = L.record_lineage(db, artifact_type="prediction", content_hash="pr-1",
                                parent_lineage_id=root["lineage_id"])
        ev = L.record_lineage(db, artifact_type="evaluation", content_hash="ev-1",
                              parent_lineage_id=pred["lineage_id"])
        chain = L.get_chain(db, ev["lineage_id"])
        assert [n["artifact_type"] for n in chain] == ["evaluation", "prediction", "dataset"]


# --------------------------------------------------------------------------------------------------
# Guardrail detection (aggregate hides a failing subgroup).
# --------------------------------------------------------------------------------------------------
def test_guardrail_passes_on_healthy_summary() -> None:
    healthy = {"pixel_accuracy": 0.80, "macro_iou": 0.62, "thin_cloud_iou": 0.58,
               "per_class_iou": {"clear": 0.7, "thick_cloud": 0.66, "thin_cloud": 0.58, "cloud_shadow": 0.55}}
    assert I.check_aggregate_hides_subgroup(healthy).passed is True


def test_guardrail_trips_when_aggregate_hides_thin_cloud() -> None:
    rep = I.check_aggregate_hides_subgroup(I._DEMO_HIDING_SUMMARY)
    assert rep.passed is False and rep.reasons


# --------------------------------------------------------------------------------------------------
# Degraded mode + recovery (with retained evidence).
# --------------------------------------------------------------------------------------------------
def test_degraded_mode_and_recovery() -> None:
    with _tmp_db() as db:
        assert I.system_status(db)["degraded"] is False
        ev = I.enter_degraded(db, reason="thin-cloud hidden", subject="evaluation:e1",
                              evidence={"guardrail": "tripped"})
        # idempotent: re-entering the same degraded condition does not duplicate.
        ev2 = I.enter_degraded(db, reason="thin-cloud hidden", subject="evaluation:e1", evidence={})
        assert ev["event_id"] == ev2["event_id"]
        st = I.system_status(db)
        assert st["degraded"] is True and len(st["active_degraded_events"]) == 1

        rec = I.recover(db, ev["event_id"], note="restored accepted versions")
        assert rec["kind"] == "RECOVERY" and rec["resolves_event_id"] == ev["event_id"]
        st2 = I.system_status(db)
        assert st2["degraded"] is False and st2["status"] == "operational"

        with assert_raises(CloudMaskingError):
            I.recover(db, "evt-does-not-exist")


# --------------------------------------------------------------------------------------------------
# End-to-end pipeline (SYNTHETIC healthy + DEMO degraded).
# --------------------------------------------------------------------------------------------------
def test_pipeline_healthy_is_operational() -> None:
    with _tmp_db() as db:
        out = I.run_masking_pipeline(db, seed=0, with_prediction=False)
        assert out["data_regime"] == "SYNTHETIC"
        assert out["guardrail_passed"] is True
        assert out["status"]["degraded"] is False
        assert len(out["lineage"]) >= 1 and out["evaluation"]["data_regime"] == "SYNTHETIC"


def test_pipeline_injected_failure_enters_degraded() -> None:
    with _tmp_db() as db:
        out = I.run_masking_pipeline(db, seed=0, with_prediction=False, inject_guardrail_failure=True)
        assert out["data_regime"] == "DEMO"
        assert out["guardrail_passed"] is False
        assert out["degraded_event"] is not None
        assert out["status"]["degraded"] is True
        # recover clears it
        rec = I.recover(db, out["degraded_event"]["event_id"])
        assert I.system_status(db)["degraded"] is False and rec["kind"] == "RECOVERY"


# --------------------------------------------------------------------------------------------------
# App exposes the M15 routes.
# --------------------------------------------------------------------------------------------------
def test_app_exposes_integration_routes() -> None:
    from app.main import create_app
    paths = {getattr(r, "path", None) for r in create_app().routes}
    for p in ("/status", "/recover/{event_id}", "/lineage", "/pipeline"):
        assert p in paths, f"missing route {p}"


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
