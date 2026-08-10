"""Milestone 4 verification: preprocessing pipeline (no large datasets, synthetic data only).

Covers dataset loader, validation, patch generation, normalization, deterministic splitting, and
augmentation registration. numpy-dependent tests are skipped when numpy is unavailable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import ConfigurationError, PreprocessingError
from app.preprocessing import augmentation as aug
from app.preprocessing.config import PreprocessingConfig, SplitRatios
from app.preprocessing.loader import (
    DEFAULT_LAYOUTS,
    MODE_PAIRED_FILES,
    DatasetLayout,
    discover_samples,
)
from app.preprocessing.patching import PatchWindow, generate_patch_grid, window_transform
from app.preprocessing.raster_io import RasterMeta
from app.preprocessing.splitting import split_samples
from app.preprocessing.validation import (
    DUPLICATE_ID,
    MISSING_FILE,
    UNSUPPORTED_TYPE,
    validate_samples,
)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:  # pragma: no cover
    HAS_NUMPY = False


# ---------------------------------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------------------------------

def test_config_defaults_and_stride() -> None:
    cfg = PreprocessingConfig()
    assert cfg.patch_size > 0 and cfg.overlap == 0
    assert cfg.stride == cfg.patch_size


def test_config_rejects_bad_overlap() -> None:
    with pytest.raises(ConfigurationError):
        PreprocessingConfig(patch_size=128, overlap=128)


def test_config_rejects_bad_ratios() -> None:
    with pytest.raises(ConfigurationError):
        PreprocessingConfig(split_ratios=SplitRatios(train=0.5, val=0.3, test=0.3))


def test_config_from_dict_roundtrip() -> None:
    cfg = PreprocessingConfig.from_dict({
        "patch_size": 256, "overlap": 32, "normalization_mode": "zscore",
        "split_ratios": {"train": 0.8, "val": 0.1, "test": 0.1},
    })
    assert cfg.patch_size == 256 and cfg.overlap == 32
    assert cfg.normalization_mode == "zscore"
    assert cfg.to_dict()["split_ratios"]["train"] == 0.8


# ---------------------------------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------------------------------

def _make_paired_files_dataset(root: Path, ids: list[str]) -> DatasetLayout:
    layout = DatasetLayout(dataset_id="demo", mode=MODE_PAIRED_FILES,
                           images_subdir="images", labels_subdir="labels")
    (root / "images").mkdir(parents=True)
    (root / "labels").mkdir(parents=True)
    for sid in ids:
        (root / "images" / f"{sid}.tif").write_bytes(b"\x00")
        (root / "labels" / f"{sid}.tif").write_bytes(b"\x00")
    return layout


def test_loader_discovers_paired_files(tmp_path: Path) -> None:
    layout = _make_paired_files_dataset(tmp_path, ["a", "b", "c"])
    result = discover_samples(tmp_path, layout)
    assert result.count == 3 and not result.missing
    assert [s.sample_id for s in result.samples] == ["a", "b", "c"]
    assert result.samples[0].label_path is not None


def test_loader_reports_missing_dataset(tmp_path: Path) -> None:
    layout = DEFAULT_LAYOUTS["on_cloud_n"]
    result = discover_samples(tmp_path / "nope", layout)
    assert result.missing is True and result.count == 0 and result.messages


# ---------------------------------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------------------------------

def test_validation_detects_missing_and_unsupported(tmp_path: Path) -> None:
    from app.preprocessing.loader import Sample
    good = tmp_path / "a.tif"; good.write_bytes(b"\x00")
    samples = [
        Sample("s1", "demo", [good], None),                       # ok image, no label -> warning
        Sample("s2", "demo", [tmp_path / "missing.tif"], None),   # missing file
        Sample("s3", "demo", [tmp_path / "b.png"], None),         # unsupported type (also missing)
        Sample("s1", "demo", [good], None),                       # duplicate id
    ]
    report = validate_samples(samples)
    cats = report.counts_by_category()
    assert cats.get(DUPLICATE_ID, 0) >= 1
    assert cats.get(MISSING_FILE, 0) >= 1
    assert report.ok is False


def test_validation_dimension_check_with_fake_reader() -> None:
    from app.preprocessing.loader import Sample
    sample = Sample("s1", "demo", [Path("b02.tif"), Path("b03.tif")], Path("lbl.tif"))

    sizes = {"b02.tif": (512, 512), "b03.tif": (256, 256), "lbl.tif": (512, 512)}

    def fake_reader(path: Path) -> RasterMeta:
        h, w = sizes[Path(path).name]
        return RasterMeta(height=h, width=w, count=1, dtype="uint16", crs=None, transform=None, nodata=None)

    report = validate_samples([sample], check_dimensions=True, meta_reader=fake_reader)
    assert any(i.category == "inconsistent_dimensions" for i in report.records)


# ---------------------------------------------------------------------------------------------------
# Patch generation (deterministic, stdlib)
# ---------------------------------------------------------------------------------------------------

def test_patch_grid_deterministic_and_covers_edges() -> None:
    g1 = generate_patch_grid(500, 500, 256, 0)
    g2 = generate_patch_grid(500, 500, 256, 0)
    assert g1 == g2                       # deterministic
    # offsets 0 and 244 (500-256) cover the edge -> 2x2 windows
    assert len(g1) == 4
    assert PatchWindow(row_off=244, col_off=244, height=256, width=256) in g1


def test_patch_grid_single_when_smaller_than_patch() -> None:
    assert generate_patch_grid(100, 100, 256, 0) == [PatchWindow(0, 0, 100, 100)]


def test_patch_grid_rejects_bad_overlap() -> None:
    with pytest.raises(PreprocessingError):
        generate_patch_grid(100, 100, 64, 64)


def test_window_transform_shifts_origin() -> None:
    # Affine (a,b,c,d,e,f): 10 m pixels, origin (500000, 4000000), north-up (e negative).
    parent = (10.0, 0.0, 500000.0, 0.0, -10.0, 4000000.0)
    win = PatchWindow(row_off=5, col_off=3, height=256, width=256)
    a, b, c, d, e, f = window_transform(parent, win)
    assert c == 500000.0 + 10.0 * 3     # x shifts by col_off * pixel width
    assert f == 4000000.0 + (-10.0) * 5  # y shifts by row_off * pixel height


# ---------------------------------------------------------------------------------------------------
# Deterministic splitting (stdlib)
# ---------------------------------------------------------------------------------------------------

def test_split_is_deterministic_and_disjoint() -> None:
    ids = [f"s{i:03d}" for i in range(100)]
    m1 = split_samples(ids, seed=42)
    m2 = split_samples(ids, seed=42)
    assert m1.train == m2.train and m1.val == m2.val and m1.test == m2.test
    all_ids = set(m1.train) | set(m1.val) | set(m1.test)
    assert all_ids == set(ids)
    assert not (set(m1.train) & set(m1.val)) and not (set(m1.val) & set(m1.test))


def test_split_ratio_counts() -> None:
    ids = [f"s{i}" for i in range(100)]
    m = split_samples(ids, ratios=SplitRatios(0.7, 0.2, 0.1), seed=1)
    assert (len(m.train), len(m.val), len(m.test)) == (70, 20, 10)


def test_split_different_seed_differs() -> None:
    ids = [f"s{i}" for i in range(100)]
    assert split_samples(ids, seed=1).train != split_samples(ids, seed=2).train


def test_group_split_keeps_groups_together() -> None:
    # 10 groups of 5 samples; no group may be split across partitions.
    ids, groups = [], {}
    for g in range(10):
        for j in range(5):
            sid = f"g{g}_s{j}"; ids.append(sid); groups[sid] = f"group{g}"
    m = split_samples(ids, ratios=SplitRatios(0.6, 0.2, 0.2), seed=7, groups=groups)
    for split in (m.train, m.val, m.test):
        split_groups = {groups[s] for s in split}
        # every member of each group present in this split appears fully here
        for grp in split_groups:
            members = {s for s in ids if groups[s] == grp}
            assert members <= set(split)


def test_split_rejects_duplicates() -> None:
    with pytest.raises(PreprocessingError):
        split_samples(["a", "a", "b"])


# ---------------------------------------------------------------------------------------------------
# Augmentation registry (stdlib; albumentations construction is lazy)
# ---------------------------------------------------------------------------------------------------

def test_augmentation_registry_lists_builtins() -> None:
    reg = aug.default_registry()
    for name in ("flip", "rotate", "crop", "brightness", "contrast"):
        assert name in reg.list_ops()


def test_augmentation_spec_parsing() -> None:
    assert aug.AugmentationSpec.from_any("flip").name == "flip"
    spec = aug.AugmentationSpec.from_any({"name": "rotate", "params": {"limit": 45}})
    assert spec.name == "rotate" and spec.params["limit"] == 45
    with pytest.raises(PreprocessingError):
        aug.AugmentationSpec.from_any(123)


def test_augmentation_unknown_op_raises() -> None:
    with pytest.raises(PreprocessingError):
        aug.default_registry().get("does_not_exist")


def test_augmentation_duplicate_registration_raises() -> None:
    reg = aug.default_registry()
    with pytest.raises(PreprocessingError):
        reg.register("flip", lambda p: None)


# ---------------------------------------------------------------------------------------------------
# Normalization + array processing (numpy required)
# ---------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_normalize_minmax_scales_unit_interval() -> None:
    from app.preprocessing.normalization import normalize
    arr = np.stack([np.arange(16).reshape(4, 4).astype(float),
                    (np.arange(16).reshape(4, 4) * 2).astype(float)])  # (2,4,4)
    out = normalize(arr, "minmax")
    assert out.shape == arr.shape
    assert abs(out.min()) < 1e-9 and abs(out.max() - 1.0) < 1e-9


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_normalize_zscore_zero_mean() -> None:
    from app.preprocessing.normalization import normalize
    arr = np.arange(25).reshape(1, 5, 5).astype(float)
    out = normalize(arr, "zscore")
    assert abs(float(out.mean())) < 1e-6


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_normalize_handles_nodata() -> None:
    from app.preprocessing.normalization import normalize
    arr = np.array([[[0.0, 1.0], [2.0, -9999.0]]])  # (1,2,2) with a nodata sentinel
    out = normalize(arr, "minmax", nodata=-9999.0, fill_value=0.0)
    assert out[0, 1, 1] == 0.0  # nodata filled
    assert 0.0 <= out.max() <= 1.0


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_pipeline_process_array_deterministic() -> None:
    from app.preprocessing.pipeline import PreprocessingPipeline
    layout = DEFAULT_LAYOUTS["cloudsen12"]
    cfg = PreprocessingConfig(patch_size=64, overlap=0, normalization_mode="minmax")
    pipe = PreprocessingPipeline(cfg, layout)
    img = np.random.RandomState(0).rand(3, 128, 128)
    a = pipe.process_array(img)
    b = pipe.process_array(img)
    assert len(a) == 4  # 128/64 -> 2x2 patches
    assert all(np.array_equal(x, y) for x, y in zip(a, b))  # deterministic
