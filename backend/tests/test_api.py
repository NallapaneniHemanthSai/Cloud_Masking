"""Milestone 13 verification: backend API (framework-free; no httpx / TestClient).

Runs under pytest **and** standalone (``python backend/tests/test_api.py``). It exercises the **services**
(the real logic behind each endpoint), a temp-SQLite database, telemetry, and asserts the FastAPI app
exposes every required route + Swagger — without needing ``httpx`` (which the project venv does not install,
so ``TestClient`` is unavailable). torch-dependent tests self-skip when torch is absent. All results here are
**SYNTHETIC / VALIDATION ONLY**.
"""

from __future__ import annotations

import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.telemetry import TelemetryRegistry  # noqa: E402
from app.db.base import Database  # noqa: E402
from app.db.models import EvaluationRunRow, ModelVersionRow, TrainingRunRow, UploadRow  # noqa: E402
from app.models._torch import torch_available  # noqa: E402
from app.models.config import ModelConfig  # noqa: E402
from app.schemas.api import PredictRequest, TrainRequest, VersionResponse  # noqa: E402
from app.services import (  # noqa: E402
    evaluation_service,
    history_service,
    model_service,
    system_service,
    upload_service,
)


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
    d = tempfile.mkdtemp(prefix="m13_")
    db = Database(f"sqlite:///{d}/test.db").create_all()
    try:
        yield db, Path(d)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------------------------------
# 1. System: version / health / metrics
# --------------------------------------------------------------------------------------------------
def test_version_info_has_all_versions() -> None:
    info = system_service.version_info()
    resp = VersionResponse(**info)                    # validates the schema contract
    assert resp.app_version == "0.13.0"
    assert resp.model_version and resp.comparison_version and resp.dataset_manifest_version


def test_health_info() -> None:
    h = system_service.health_info("sqlite:///./outputs/x.db")
    assert h["status"] == "ok" and "device" in h and isinstance(h["torch_available"], bool)


def test_telemetry_registry() -> None:
    reg = TelemetryRegistry()
    reg.record("/train", 0.5, error=False)
    reg.record("/train", 1.5, error=True)
    snap = reg.snapshot()
    assert snap["total_requests"] == 2 and snap["total_errors"] == 1
    route = next(r for r in snap["routes"] if r["route"] == "/train")
    assert route["count"] == 2 and abs(route["avg_seconds"] - 1.0) < 1e-6


# --------------------------------------------------------------------------------------------------
# 2. DB + model/upload/evaluation/history services
# --------------------------------------------------------------------------------------------------
def test_db_tables_created() -> None:
    with _tmp_db() as (db, _):
        with db.session() as s:
            assert s.query(TrainingRunRow).count() == 0
            assert s.query(UploadRow).count() == 0


def test_list_architectures_includes_baseline_and_improved() -> None:
    archs = {a["architecture"] for a in model_service.list_architectures()}
    assert "unet" in archs and "attention_unet" in archs


def test_register_and_list_model_version() -> None:
    with _tmp_db() as (db, _):
        row = model_service.register_version(db, ModelConfig(name="unet"))
        assert row["architecture"] == "unet" and row["config_hash"]
        listed = model_service.list_registered(db)
        assert len(listed) == 1 and listed[0]["model_id"].startswith("unet-")


def test_upload_service_persists_file_and_row() -> None:
    with _tmp_db() as (db, d):
        out = upload_service.store_upload(db, filename="scene.tif", content=b"RASTERBYTES",
                                          content_type="image/tiff", uploads_dir=d / "uploads")
        assert out["size_bytes"] == 11 and out["content_hash"]
        assert Path(out["path"]).is_file()
        with db.session() as s:
            assert s.query(UploadRow).count() == 1


def test_evaluation_service_surfaces_thin_cloud() -> None:
    with _tmp_db() as (db, _):
        out = evaluation_service.run_evaluation(db, mode="multiclass", split="test", seed=0)
        assert out["data_regime"] == "SYNTHETIC"
        assert "thin_cloud" in out["per_class_iou"]           # thin cloud always surfaced
        with db.session() as s:
            assert s.query(EvaluationRunRow).count() == 1


def test_evaluation_service_rejects_non_synthetic() -> None:
    from app.core.exceptions import EvaluationError
    with _tmp_db() as (db, _):
        with assert_raises(EvaluationError):
            evaluation_service.run_evaluation(db, synthetic=False)


def test_history_service_aggregates() -> None:
    with _tmp_db() as (db, d):
        upload_service.store_upload(db, filename="a.tif", content=b"x", uploads_dir=d / "u")
        evaluation_service.run_evaluation(db, seed=1)
        hist = history_service.history(db, limit=10)
        assert len(hist["uploads"]) == 1 and len(hist["evaluations"]) == 1


# --------------------------------------------------------------------------------------------------
# 3. torch-dependent services (training / prediction)
# --------------------------------------------------------------------------------------------------
def test_training_service_synthetic() -> None:
    if not torch_available():
        print("SKIP test_training_service_synthetic (torch unavailable)"); return
    from app.services import training_service
    with _tmp_db() as (db, _):
        out = training_service.run_training(db, architecture="unet", encoder_depth=2, base_channels=8,
                                            epochs=1, batch_size=2, synthetic_patch=16, device="cpu")
        assert out["status"] == "completed" and out["data_regime"] == "SYNTHETIC"
        assert out["run_id"].startswith("run-") and out["parameter_count"] > 0
        with db.session() as s:
            assert s.query(TrainingRunRow).count() == 1


def test_prediction_service_synthetic() -> None:
    if not torch_available():
        print("SKIP test_prediction_service_synthetic (torch unavailable)"); return
    from app.services import prediction_service
    with _tmp_db() as (db, _):
        out = prediction_service.run_prediction(db, architecture="attention_unet", in_channels=13,
                                                num_classes=4, encoder_depth=2, base_channels=8,
                                                patch_size=32, device="cpu")
        assert out["output_shape"] == [32, 32] and out["prediction_id"].startswith("pred-")
        assert sum(out["class_pixel_counts"].values()) == 32 * 32


def test_training_service_requires_synthetic_flag() -> None:
    if not torch_available():
        print("SKIP test_training_service_requires_synthetic_flag (torch unavailable)"); return
    from app.core.exceptions import TrainingError
    from app.services import training_service
    with _tmp_db() as (db, _):
        with assert_raises(TrainingError):
            training_service.run_training(db, synthetic=False)


# --------------------------------------------------------------------------------------------------
# 4. App factory: all required routes + Swagger present
# --------------------------------------------------------------------------------------------------
def test_app_exposes_all_routes() -> None:
    from app.main import create_app
    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}
    for p in ("/version", "/health", "/metrics", "/models", "/train", "/predict", "/evaluate",
              "/history", "/upload", "/docs", "/openapi.json"):
        assert p in paths, f"missing route {p}"


def test_schema_defaults() -> None:
    assert TrainRequest().architecture == "unet" and TrainRequest().synthetic is True
    assert PredictRequest().num_classes == 4


# --------------------------------------------------------------------------------------------------
# Manual harness
# --------------------------------------------------------------------------------------------------
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
