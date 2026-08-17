"""Milestone 12 verification: experimental-dataset readiness pipeline (synthetic data only).

Runs under pytest **and** standalone (``python backend/tests/test_datasets_experimental.py``) so it doubles
as the manual harness when pytest is absent — it imports no third-party test framework. numpy is guarded
(tests needing it are skipped/reported when absent). **No real data is ever downloaded** and no real-data
results are asserted.

Covers: config validation + hash, availability, checksum verification, missing/invalid files, dimension +
class validation, deterministic subset selection, deterministic + leakage-checked splitting, patch manifest,
train-only normalization statistics, class distribution (thin cloud surfaced), dataset-artifact hashing,
readiness gate, synthetic end-to-end, and the M11 handoff.
"""

from __future__ import annotations

import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.exceptions import ConfigurationError, PreprocessingError  # noqa: E402
from app.datasets.artifact import DatasetArtifact  # noqa: E402
from app.datasets.availability import NOT_PRESENT, check_availability  # noqa: E402
from app.datasets.experimental_config import ExperimentalDatasetConfig  # noqa: E402
from app.datasets.pipeline import prepare_experimental_dataset  # noqa: E402
from app.datasets.readiness import is_experiment_ready  # noqa: E402
from app.datasets.records import (  # noqa: E402
    INVALID,
    READY,
    READY_WITH_WARNINGS,
    ExperimentalSplitManifest,
    SplitEntry,
    SubsetSelection,
)
from app.datasets.sampling import build_split_manifest, select_subset  # noqa: E402
from app.datasets.synthetic import generate_synthetic_dataset, read_npy_array  # noqa: E402
from app.datasets.validation_gates import validate_experimental_dataset  # noqa: E402
from app.preprocessing.records import SampleRecord  # noqa: E402

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:  # pragma: no cover
    HAS_NUMPY = False


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
def _tmp():
    d = tempfile.mkdtemp(prefix="m12_")
    try:
        yield Path(d)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def _prepare(tmp: Path):
    cfg = ExperimentalDatasetConfig(subset_size=24, seed=1, patch_size=16)
    return cfg, prepare_experimental_dataset(cfg, synthetic=True, output_dir=tmp)


# --------------------------------------------------------------------------------------------------
# 1. Config validation + deterministic hash
# --------------------------------------------------------------------------------------------------
def test_config_validation_rejects_bad_overlap() -> None:
    with assert_raises(ConfigurationError):
        ExperimentalDatasetConfig(patch_size=16, overlap=16)


def test_config_validation_requires_thin_cloud() -> None:
    with assert_raises(ConfigurationError):
        ExperimentalDatasetConfig(thin_cloud_required=True, required_classes=("clear", "thick_cloud"))


def test_config_hash_deterministic() -> None:
    a = ExperimentalDatasetConfig(subset_size=24, seed=1)
    assert a.config_hash() == ExperimentalDatasetConfig.from_dict(a.to_dict()).config_hash()
    assert a.config_hash() != ExperimentalDatasetConfig(subset_size=24, seed=2).config_hash()


# --------------------------------------------------------------------------------------------------
# 2. Availability (no real data present)
# --------------------------------------------------------------------------------------------------
def test_availability_reports_not_present_for_absent_data() -> None:
    from app.datasets.manifest import DatasetRecord
    rec = DatasetRecord(
        dataset_id="cloudsen12", name="x", version="v", homepage="", source="", official_paper="",
        citation="", license="CC0-1.0", redistribution="", download_required=True, manual_steps=[],
        expected_directory="raw/cloudsen12", expected_size="", checksum_algorithm="sha256",
        checksum="TBD", download_date="", bands={}, label_schema={}, intended_use="", notes="")
    with _tmp() as tmp:
        report = check_availability({"cloudsen12": rec}, tmp)
    assert report.status_for("cloudsen12") == NOT_PRESENT
    assert report.checksums_present is False


# --------------------------------------------------------------------------------------------------
# 3. Validation gates: checksums, missing files, invalid labels, class presence
# --------------------------------------------------------------------------------------------------
def _synthetic(tmp: Path):
    return generate_synthetic_dataset(tmp / "raw", num_scenes=8, patches_per_scene=3, size=16,
                                      band_count=13, num_classes=4, seed=1)


def test_validation_ready_and_checksums_pass() -> None:
    if not HAS_NUMPY:
        print("SKIP test_validation_ready_and_checksums_pass (numpy unavailable)")
        return
    with _tmp() as tmp:
        ds = _synthetic(tmp)
        report = validate_experimental_dataset(
            "cloudsen12", ds.samples, num_classes=4,
            required_classes=("clear", "thick_cloud", "thin_cloud", "cloud_shadow"),
            class_mapping={0: "clear", 1: "thick_cloud", 2: "thin_cloud", 3: "cloud_shadow"},
            label_reader=read_npy_array, checksums=ds.checksums, data_regime="SYNTHETIC")
    assert report.overall_status in (READY, READY_WITH_WARNINGS)
    assert report.checksum_status == "PASS"
    assert report.label_status == "PASS"


def test_validation_detects_missing_file() -> None:
    if not HAS_NUMPY:
        print("SKIP test_validation_detects_missing_file (numpy unavailable)")
        return
    sample = SampleRecord(sample_id="x", dataset="d",
                          image_paths=[Path("/nonexistent/x.npy")], label_path=Path("/nonexistent/x_lbl.npy"))
    report = validate_experimental_dataset(
        "cloudsen12", [sample], num_classes=4,
        required_classes=("clear",), class_mapping={0: "clear"}, label_reader=read_npy_array)
    assert report.file_status == "FAIL"
    assert report.overall_status == "INCOMPLETE"


def test_validation_detects_out_of_range_labels() -> None:
    if not HAS_NUMPY:
        print("SKIP test_validation_detects_out_of_range_labels (numpy unavailable)")
        return
    with _tmp() as tmp:
        (tmp / "images").mkdir(parents=True)
        (tmp / "labels").mkdir(parents=True)
        img, lab = tmp / "images/x.npy", tmp / "labels/x.npy"
        np.save(img, np.zeros((13, 8, 8), dtype="float32"))
        np.save(lab, np.full((8, 8), 9, dtype="int64"))     # label 9 is out of [0,3]
        sample = SampleRecord(sample_id="x", dataset="d", image_paths=[img], label_path=lab)
        report = validate_experimental_dataset(
            "cloudsen12", [sample], num_classes=4,
            required_classes=("clear",), class_mapping={0: "clear"}, label_reader=read_npy_array,
            checksums=None)
    assert report.label_status == "FAIL"
    assert report.overall_status == INVALID


def test_validation_detects_missing_required_class() -> None:
    if not HAS_NUMPY:
        print("SKIP test_validation_detects_missing_required_class (numpy unavailable)")
        return
    with _tmp() as tmp:
        (tmp / "images").mkdir(parents=True)
        (tmp / "labels").mkdir(parents=True)
        img, lab = tmp / "images/x.npy", tmp / "labels/x.npy"
        np.save(img, np.zeros((13, 8, 8), dtype="float32"))
        np.save(lab, np.zeros((8, 8), dtype="int64"))       # only class 0 present
        sample = SampleRecord(sample_id="x", dataset="d", image_paths=[img], label_path=lab)
        report = validate_experimental_dataset(
            "cloudsen12", [sample], num_classes=4,
            required_classes=("clear", "thin_cloud"),
            class_mapping={0: "clear", 2: "thin_cloud"}, label_reader=read_npy_array)
    assert report.label_status == "FAIL"          # thin_cloud absent -> label gate fails


# --------------------------------------------------------------------------------------------------
# 4. Deterministic subset selection (guarantees thin cloud) + leakage-checked splitting
# --------------------------------------------------------------------------------------------------
def test_subset_selection_deterministic_and_guarantees_classes() -> None:
    cfg = ExperimentalDatasetConfig(subset_size=6, seed=3)
    ids = [f"s{i}" for i in range(20)]
    groups = {sid: f"scene_{i % 5}" for i, sid in enumerate(ids)}
    classes = {sid: {"clear"} for sid in ids}
    classes["s0"] = {"clear", "thin_cloud"}
    classes["s1"] = {"clear", "cloud_shadow", "thick_cloud"}
    sel1 = select_subset(ids, config=cfg, groups=groups, sample_classes=classes)
    sel2 = select_subset(ids, config=cfg, groups=groups, sample_classes=classes)
    assert sel1.selection_hash() == sel2.selection_hash()
    assert "s0" in sel1.selected_ids and "s1" in sel1.selected_ids   # forced for class coverage
    assert sel1.class_presence.get("thin_cloud") is True


def test_split_manifest_deterministic_and_leakage_free() -> None:
    cfg = ExperimentalDatasetConfig(subset_size=12, seed=7)
    ids = [f"s{i}" for i in range(12)]
    groups = {sid: f"scene_{i // 3}" for i, sid in enumerate(ids)}   # 4 scenes of 3
    sel = SubsetSelection(strategy="s", seed=7, requested_size=12, selected_ids=ids, group_ids=groups)
    m1 = build_split_manifest(sel, config=cfg, dataset_version="v1")
    m2 = build_split_manifest(sel, config=cfg, dataset_version="v1")
    assert m1.split_config_hash() == m2.split_config_hash()
    assert m1.leakage_ok() is True
    # A whole scene stays in one split (group-aware).
    for scene in {groups[s] for s in ids}:
        splits = {e.split for e in m1.entries if e.group_id == scene}
        assert len(splits) == 1, f"scene {scene} leaked across {splits}"


def test_split_leakage_detected() -> None:
    m = ExperimentalSplitManifest(entries=[
        SplitEntry("a", "sc1", "train"), SplitEntry("a", "sc1", "test")], grouped=True)
    assert m.leakage_ok() is False


# --------------------------------------------------------------------------------------------------
# 5. Class distribution + normalization statistics (train only)
# --------------------------------------------------------------------------------------------------
def test_class_distribution_surfaces_thin_cloud() -> None:
    if not HAS_NUMPY:
        print("SKIP test_class_distribution_surfaces_thin_cloud (numpy unavailable)")
        return
    with _tmp() as tmp:
        _, prepared = _prepare(tmp)
    cd = prepared.class_distribution
    assert "thin_cloud" in cd.class_names
    assert cd.pixel_counts["thin_cloud"] > 0
    assert cd.thin_cloud_fraction() is not None and cd.thin_cloud_fraction() < cd.percentages()["clear"]
    assert cd.imbalance_severe() is True          # thin cloud is a rare stripe


def test_normalization_hash_deterministic() -> None:
    if not HAS_NUMPY:
        print("SKIP test_normalization_hash_deterministic (numpy unavailable)")
        return
    with _tmp() as t1, _tmp() as t2:
        _, p1 = _prepare(t1)
        _, p2 = _prepare(t2)
    assert p1.normalization_hash and p1.normalization_hash == p2.normalization_hash


# --------------------------------------------------------------------------------------------------
# 6. Dataset artifact hashing
# --------------------------------------------------------------------------------------------------
def test_artifact_hash_deterministic_and_ignores_timestamp_notes() -> None:
    import dataclasses
    a = DatasetArtifact.create(dataset_id="cloudsen12", dataset_version="v1", config_hash="c",
                               subset_selection_hash="s", split_manifest_hash="sp",
                               normalization_statistics_hash="n", sample_count=10, patch_count=40)
    b = dataclasses.replace(a, created_at="2000-01-01T00:00:00+00:00", notes="different")
    assert a.content_hash() == b.content_hash()
    assert a.artifact_id == f"ds-cloudsen12-{a.content_hash()[:12]}"
    c = DatasetArtifact.from_dict(a.to_dict())
    assert c.content_hash() == a.content_hash()


# --------------------------------------------------------------------------------------------------
# 7. Readiness gate + synthetic end-to-end + M11 handoff
# --------------------------------------------------------------------------------------------------
def test_synthetic_end_to_end_is_ready() -> None:
    if not HAS_NUMPY:
        print("SKIP test_synthetic_end_to_end_is_ready (numpy unavailable)")
        return
    with _tmp() as tmp:
        cfg, prepared = _prepare(tmp)
    assert prepared.data_regime == "SYNTHETIC"
    assert prepared.validation.overall_status in (READY, READY_WITH_WARNINGS)
    assert prepared.readiness.ready is True
    assert prepared.split_manifest.leakage_ok() is True
    assert prepared.patch_count > 0
    # Deterministic artifact identity.
    assert prepared.artifact.artifact_id.startswith("ds-cloudsen12-")


def test_readiness_gate_blocks_incomplete_dataset() -> None:
    cfg = ExperimentalDatasetConfig(subset_size=6, seed=1)
    # An artifact with no normalization/patches and an INVALID validation must not be ready.
    artifact = DatasetArtifact.create(
        dataset_id="cloudsen12", dataset_version="", config_hash="c",
        validation_report={"overall_status": "INVALID", "file_status": "FAIL"},
        class_distribution={"pixel_counts": {}, "percentages": {}}, data_regime="REAL")
    readiness = is_experiment_ready(artifact, split_manifest=ExperimentalSplitManifest(), config=cfg)
    assert readiness.ready is False
    assert "thin_cloud_exists" in readiness.critical_failures


def test_m11_handoff_carries_channels_classes_and_regime() -> None:
    if not HAS_NUMPY:
        print("SKIP test_m11_handoff_carries_channels_classes_and_regime (numpy unavailable)")
        return
    with _tmp() as tmp:
        cfg, prepared = _prepare(tmp)
    h = prepared.handoff
    assert h.expected_input_channels == 13 and h.expected_classes == 4
    assert h.data_regime == "SYNTHETIC" and h.ready is True
    # The handoff carries a consumable M11 ComparisonConfig pinned to this dataset.
    cc = h.comparison_config
    assert cc.get("dataset") == "cloudsen12"
    assert cc.get("dataset_version") == prepared.artifact.dataset_version


def test_real_regime_reports_not_present_without_download() -> None:
    cfg = ExperimentalDatasetConfig(dataset_id="cloudsen12", subset_size=24, seed=1)
    with _tmp() as tmp:
        prepared = prepare_experimental_dataset(cfg, synthetic=False, data_root=tmp)
    assert prepared.data_regime == "REAL"
    assert prepared.validation.overall_status == NOT_PRESENT
    assert prepared.readiness.ready is False
    assert prepared.handoff.ready is False


# --------------------------------------------------------------------------------------------------
# Manual harness (used when pytest is unavailable).
# --------------------------------------------------------------------------------------------------
def _run_all() -> int:
    tests = [(n, o) for n, o in sorted(globals().items()) if n.startswith("test_") and callable(o)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
