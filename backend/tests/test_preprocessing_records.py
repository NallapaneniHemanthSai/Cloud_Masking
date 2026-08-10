"""Milestone 4 (revised) verification: typed records, patch manifest, normalization statistics,
validation summaries, and the backend-agnostic augmentation abstraction. Synthetic data only.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from app.core.exceptions import PreprocessingError
from app.preprocessing import augmentation as aug
from app.preprocessing.normalization import BandStats, NormalizationStatistics
from app.preprocessing.patch_manifest import PatchManifest, build_patch_records
from app.preprocessing.records import (
    PatchRecord,
    SampleRecord,
    SplitRecord,
    ValidationRecord,
)
from app.preprocessing.validation import (
    CORRUPTED_METADATA,
    DUPLICATE_ID,
    MISSING_LABEL,
    ValidationReport,
    ValidationSummary,
)

try:
    import albumentations  # noqa: F401
    HAS_ALB = True
except ImportError:
    HAS_ALB = False


# ---------------------------------------------------------------------------------------------------
# Typed records
# ---------------------------------------------------------------------------------------------------

def test_sample_record_to_dict() -> None:
    rec = SampleRecord("s1", "demo", [Path("a.tif"), Path("b.tif")], Path("l.tif"), group="g1")
    d = rec.to_dict()
    assert d["sample_id"] == "s1" and d["image_paths"] == ["a.tif", "b.tif"]
    assert d["label_path"] == "l.tif" and d["group"] == "g1"


def test_split_and_validation_records() -> None:
    assert SplitRecord("s1", "train").to_dict()["split"] == "train"
    vr = ValidationRecord("s1", "missing_file", "x")
    assert vr.severity == "ERROR" and vr.to_dict()["category"] == "missing_file"


def test_patch_record_columns_and_dict() -> None:
    rec = PatchRecord("s1", "demo", "train", 0, 0, 0, 64, 64, 0, 64, "img.tif", None,
                      "2026-01-01T00:00:00+00:00", "0.4.0")
    d = rec.to_dict()
    assert list(d.keys()) == list(PatchRecord.COLUMNS)
    assert d["patch_index"] == 0 and d["preprocessing_version"] == "0.4.0"


# ---------------------------------------------------------------------------------------------------
# Patch manifest serialization
# ---------------------------------------------------------------------------------------------------

def _sample() -> SampleRecord:
    return SampleRecord("chip1", "on_cloud_n", [Path("chip1/B02.tif")], Path("labels/chip1.tif"))


def test_build_patch_records_deterministic() -> None:
    ts = "2026-01-01T00:00:00+00:00"
    a = build_patch_records(_sample(), "train", 64, 0, (128, 128), created_utc=ts)
    b = build_patch_records(_sample(), "train", 64, 0, (128, 128), created_utc=ts)
    assert len(a) == 4 and a == b                       # 128/64 -> 2x2, deterministic
    assert [r.patch_index for r in a] == [0, 1, 2, 3]
    assert a[0].split == "train" and a[0].dataset == "on_cloud_n"


def test_patch_manifest_jsonl_roundtrip(tmp_path: Path) -> None:
    records = build_patch_records(_sample(), "val", 64, 0, (128, 128),
                                  created_utc="2026-01-01T00:00:00+00:00")
    manifest = PatchManifest(records)
    out = manifest.save_jsonl(tmp_path / "patches.jsonl")
    lines = [ln for ln in out.read_text().splitlines() if ln]
    assert len(lines) == 4
    first = json.loads(lines[0])
    assert first["sample_id"] == "chip1" and first["split"] == "val"


def test_patch_manifest_csv_has_header_and_rows(tmp_path: Path) -> None:
    records = build_patch_records(_sample(), "test", 64, 0, (128, 128),
                                  created_utc="2026-01-01T00:00:00+00:00")
    out = PatchManifest(records).save_csv(tmp_path / "patches.csv")
    reader = list(csv.DictReader(io.StringIO(out.read_text())))
    assert len(reader) == 4
    assert set(reader[0].keys()) == set(PatchRecord.COLUMNS)
    assert reader[0]["split"] == "test"


# ---------------------------------------------------------------------------------------------------
# Normalization statistics serialization
# ---------------------------------------------------------------------------------------------------

def test_normalization_statistics_roundtrip(tmp_path: Path) -> None:
    band_stats = BandStats(minimum=[0.0, 1.0], maximum=[10.0, 20.0], mean=[5.0, 10.0],
                           std=[2.0, 4.0], p_low=[0.5, 1.5], p_high=[9.5, 19.5])
    stats = NormalizationStatistics.from_band_stats(band_stats, "minmax", clip_low=0.0, clip_high=1.0)
    assert stats.num_bands == 2 and stats.preprocessing_version

    # dict roundtrip
    restored = NormalizationStatistics.from_dict(stats.to_dict())
    assert restored.means == stats.means and restored.normalization_mode == "minmax"

    # json file roundtrip
    path = stats.save_json(tmp_path / "norm.json")
    loaded = NormalizationStatistics.load_json(path)
    assert loaded.maximums == [10.0, 20.0] and loaded.clip_high == 1.0


# ---------------------------------------------------------------------------------------------------
# Validation summaries
# ---------------------------------------------------------------------------------------------------

def test_validation_summary_counts_and_table() -> None:
    report = ValidationReport(samples_checked=3)
    report.add("s1", DUPLICATE_ID, "dup")
    report.add("s2", CORRUPTED_METADATA, "boom")
    report.add("s3", MISSING_LABEL, "no label", severity="WARNING")
    summary = report.summary()
    assert isinstance(summary, ValidationSummary)
    assert summary.total_samples == 3
    assert summary.duplicate_ids == 1 and summary.corrupted_files == 1
    assert summary.missing_labels == 1
    # s1 and s2 have ERROR issues -> 2 invalid, 1 valid
    assert summary.invalid_samples == 2 and summary.valid_samples == 1
    table = report.render_table()
    for label in ("total samples", "valid samples", "corrupted files", "missing labels"):
        assert label in table


# ---------------------------------------------------------------------------------------------------
# Augmentation abstraction (generic ops; Albumentations only via adapter)
# ---------------------------------------------------------------------------------------------------

def test_build_pipeline_returns_generic_operations() -> None:
    specs = [aug.AugmentationSpec("flip"), aug.AugmentationSpec("rotate", {"limit": 45})]
    pipeline = aug.build_pipeline(specs)
    assert isinstance(pipeline, aug.AugmentationPipeline)
    assert pipeline.names() == ["flip", "rotate"]
    assert isinstance(pipeline.operations[0], aug.Flip)
    assert isinstance(pipeline.operations[1], aug.Rotate)
    assert pipeline.operations[1].limit == 45
    # No Albumentations classes leak into the generic pipeline representation.
    d = pipeline.to_dict()
    assert d["operations"][0]["name"] == "flip"


def test_generic_operation_to_dict() -> None:
    op = aug.Crop(height=128, width=128)
    assert op.to_dict()["name"] == "crop"
    assert op.to_dict()["params"]["height"] == 128


def test_adapter_translation_is_isolated() -> None:
    """The adapter is the only Albumentations touchpoint; without it, it raises clearly."""
    pipeline = aug.build_pipeline([aug.AugmentationSpec("flip")])
    adapter = aug.AlbumentationsAdapter()
    if HAS_ALB:
        compose = adapter.to_compose(pipeline)
        assert compose is not None
    else:
        with pytest.raises(PreprocessingError):
            adapter.to_compose(pipeline)
