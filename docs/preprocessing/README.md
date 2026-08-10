# Preprocessing

Milestone 4 delivers the **preprocessing pipeline** (dataset loading, validation, patching,
normalization, splitting, and an augmentation framework). No model/training/inference code is included.
All heavy dependencies (numpy, rasterio, albumentations) are **guarded imports** so the package loads on a
bare interpreter; the functions that need them raise a clear error when absent.

## Modules (`backend/app/preprocessing/`)

| Module | Responsibility |
|--------|----------------|
| `records.py` | **Typed records** exchanged between modules: `SampleRecord`, `PatchRecord`, `SplitRecord`, `ValidationRecord`. |
| `config.py` | `PreprocessingConfig` — validated patch size, overlap, normalization mode, augmentation toggle, seed, split ratios. |
| `loader.py` | Dataset layouts + sample discovery (CloudSEN12, On Cloud N) → `SampleRecord`; graceful missing-dataset reporting. |
| `validation.py` | Structured validation report + `ValidationSummary` (missing files/labels, unsupported types, duplicate ids, inconsistent dimensions, corrupted metadata). |
| `patching.py` | Deterministic patch grid + geotransform propagation; numpy-based extraction. |
| `patch_manifest.py` | `PatchManifest` — per-patch metadata with **JSONL/CSV** export. |
| `normalization.py` | Per-band normalization + `NormalizationStatistics` (serialisable stats). |
| `splitting.py` | Reproducible, group-aware train/val/test splits + split manifest + `SplitRecord`. |
| `augmentation.py` | Backend-agnostic augmentation framework + `AlbumentationsAdapter`. |
| `raster_io.py` | Guarded rasterio reader (`RasterMeta`, `read_raster`). |
| `pipeline.py` | Orchestration: dry `plan()` + numpy `process_array()` + `build_patch_manifest()`. |

## Preprocessing data flow

```
raw dataset
   │  loader.discover_samples ──▶ list[SampleRecord]
   ▼
validation.validate_samples ──▶ ValidationReport (list[ValidationRecord]) ──▶ ValidationSummary + table
   │
   ▼
splitting.split_samples ──▶ SplitManifest ──▶ list[SplitRecord] / split_lookup
   │
   ▼
patching.generate_patch_grid  +  patch_manifest.build_patch_records ──▶ PatchManifest ──▶ JSONL / CSV
   │
   ▼
normalization (per band; NormalizationStatistics fit on train, applied to val/test)
   │
   ▼
augmentation (generic AugmentationPipeline) ──▶ AlbumentationsAdapter (only when albumentations present)
```

Typed records are the **interfaces** between stages: `SampleRecord` (loader → validation/splitting),
`SplitRecord` (splitting → manifest), `PatchRecord` (patching → manifest), `ValidationRecord`
(validation report). None carry model information.

## Patch manifest

`patch_manifest.build_patch_records(sample, split, patch_size, overlap, image_size)` emits one
`PatchRecord` per grid window with: `sample_id`, `dataset`, `split`, `patch_index`, patch coordinates
(`row_off`, `col_off`), `height`/`width`, `overlap`, `patch_size`, `source_image`, `label_path`,
`created_utc`, and `preprocessing_version`. `PatchManifest` exports to **JSONL** (`to_jsonl` / `save_jsonl`)
and **CSV** (`to_csv` / `save_csv`) using the canonical `PatchRecord.COLUMNS` order. Deterministic when a
fixed `created_utc` is supplied.

## Normalization metadata

`NormalizationStatistics` records per-band `means`, `stds`, `minimums`, `maximums`, percentile values
(`p_low`/`p_high`), `clip_low`/`clip_high`, `percentile_range`, `normalization_mode`, `num_bands`,
`created_utc`, and `preprocessing_version`. It is standard-library (lists of floats) and serialises via
`to_dict`/`from_dict`/`to_json`/`save_json`/`load_json`, so stats fit on **train** can be persisted and
reapplied to val/test. **Milestone 4 provides the framework only — statistics are not computed over the
real dataset yet.**

## Preprocessing workflow

```
discover samples (loader) → validate (validation) → split (splitting) →
[per sample] read raster (raster_io) → generate patch grid (patching) →
extract patches → normalize per band (normalization) → (optional) augment (augmentation)
```

CLI (dry, no downloads):
```bash
python backend/scripts/preprocess.py --dataset on_cloud_n --patch-size 256 --overlap 32
python backend/scripts/split_dataset.py --dataset cloudsen12 --seed 42
```

## Patch strategy

- Fixed square patches of `patch_size`, stride `patch_size − overlap`.
- The grid is **deterministic** and **fully covers** the image: the trailing row/column offset is clamped
  to the edge (origin shifted back) so every patch is full-size — no padding, no partial tiles.
- Geospatial metadata is preserved: `window_transform` shifts the affine origin `(c, f)` for each patch
  (rasterio/GDAL `(a, b, c, d, e, f)` convention).

## Normalization strategy

Per-band, configurable via `normalization_mode`:

| Mode | Behaviour |
|------|-----------|
| `none` | Pass-through (only nodata/clip handling). |
| `minmax` | Scale each band to `[0, 1]` using per-band min/max. |
| `zscore` | `(x − mean) / std` per band. |
| `percentile` | Clip to `[p_low, p_high]` per band, then scale to `[0, 1]`. |

Missing values (`nodata_value`) are replaced with NaN, **excluded from statistics**, and filled with
`fill_value` after scaling. Compute stats on **train** patches and reuse them for val/test to avoid leakage.

## Split strategy

- Deterministic given `random_seed` (canonical sort → seeded shuffle → ratio partition).
- Configurable ratios (`train`/`val`/`test`, must sum to 1.0).
- **Group-aware**: with a `group_by` key, all samples of a group land in the same split — the mechanism
  used for leakage-resistant **spatial** holdouts (NFR-4 / AC-3).
- Splits are asserted **disjoint**; a `SplitManifest` (seed, ratios, counts, ids) is written to YAML.

## Validation reporting

`validate_samples` returns a `ValidationReport` of typed `ValidationRecord`s. `report.summary()` yields a
structured `ValidationSummary` — total / valid / invalid samples, duplicate ids, corrupted files, missing
labels, missing files, unsupported files, inconsistent dimensions — and `report.render_table()` prints a
human-readable summary table. Dimension/metadata checks accept an injectable `meta_reader`, so the logic is
unit-testable without rasterio.

## Augmentation strategy (backend-agnostic)

Infrastructure only — **augmentation is not applied during training in this milestone.** The framework is
**independent of Albumentations**:

- Generic operations (`Flip`, `Rotate`, `Crop`, `Brightness`, `Contrast`) are plain dataclasses.
- A registry maps names to factories that build these **generic** operations.
- `build_pipeline(specs, enabled)` returns a generic `AugmentationPipeline` — no third-party classes leak
  into the preprocessing API.
- `AlbumentationsAdapter` is the **only** Albumentations touchpoint: `to_transform(op)` / `to_compose(pipeline)`
  translate generic ops into Albumentations transforms *when the library is installed*, raising a clear
  error otherwise.

## Configuration

See the `preprocessing:` section of `backend/configs/config.template.yaml`, which maps 1:1 to
`PreprocessingConfig`. No constants are hardcoded in modules — defaults live in `app.core.constants`.
