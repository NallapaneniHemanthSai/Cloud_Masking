# Real CloudSEN12+ Experiment — U-Net vs Attention U-Net (first measured run)

**Status: MEASURED — REAL DATA.** This is the project's **first real controlled comparison** on actual
CloudSEN12+ Sentinel-2 data, executed on Apple **MPS**. It is a **bounded first experiment** (32 samples,
one small U-Net configuration, 12 epochs, 3 seeds) — **not** the frozen AC-4 acceptance benchmark. All
numbers below are measured on this subset; they must not be read as the project's final KPI values.

> Honesty: nothing here is synthetic. Synthetic pipeline-validation results (M11/M12) remain separately
> labelled SYNTHETIC and are not promoted. Real model quality beyond this bounded run remains
> **NOT YET MEASURED** (full-dataset / AC-4 evaluation is future work).

## Environment (verified)

- Interpreter: `backend/.venv/bin/python` — Python 3.11.2; numpy 1.26.4, rasterio 1.4.4, tacoreader 0.6.5,
  torch 2.13.0, aiohttp 3.14.3.
- Device: **MPS = True, CUDA = False**. Both arms trained on **mps** (recorded in each artifact).

## Data acquisition & provenance

- Source: `tacofoundation/cloudsen12` (Hugging Face), variant `cloudsen12-l1c`, via **tacoreader 0.6.5**.
  License **CC0-1.0**. Access is public; no controls bypassed, no credentials used.
- Verified from the data itself: S2 image = **13-band uint16 512×512** (nodata 65535); label = uint8 512×512
  with encoding **0=clear, 1=thick, 2=thin, 3=cloud_shadow**; CRS + geotransform present.
- **Bounded subset:** 32 `label_type=high` (expert-labelled) samples from L1C part 0, selected
  deterministically (seed 1) with metadata class fractions guaranteeing thin-cloud & cloud-shadow presence.
  Raw payloads (~53 MB) are git-ignored under `data/raw/cloudsen12/`; **never committed**.
- `dataset_version = cloudsen12plus-1.1.2-l1c-p0-9045d5c3`; per-file SHA-256 recorded.

## Dataset readiness (M12 gate) — REAL DATASET STATUS = READY

- Validation: **READY** (files/checksums/labels/dimensions/completeness all pass).
- Split (class-stratified, ROI/scene-grouped): **train 22 / val 5 / test 5 samples**, `leakage_ok = True`
  (no sample **or** ROI shared across splits). 512 patches @ 128 px.
- Normalization: min-max, **fit on TRAIN ONLY**, applied identically to val/test (`normalization_hash`
  recorded).
- Class distribution (pixels) — thin cloud present in **every** split (test 26.5% thin, 12.4% shadow):
  overall clear 40.1% / thick 32.1% / **thin 16.7%** / shadow 11.1%.
- `is_experiment_ready() == TRUE` (all critical gates pass).

## Controlled comparison (fairness)

Both arms share identical dataset, split, preprocessing, normalization, seed, patch size (128), batch size
(8), epochs (12), optimizer (AdamW), scheduler (cosine), loss (cross-entropy), checkpoint policy, and device
(mps). **Only the architecture differs.** U-Net = **484,228** params; Attention U-Net = **490,005** params
(×1.012). Attention training time ≈ **×1.2–1.3**.

## Results — per class, 3 seeds (IoU delta = improved − baseline)

| Class | Seed 1 ΔIoU | Seed 2 ΔIoU | Seed 3 ΔIoU |
|-------|:---:|:---:|:---:|
| clear | −0.024 | −0.014 | +0.039 |
| thick_cloud | −0.057 | +0.028 | +0.122 |
| **thin_cloud (PRIMARY)** | **+0.047** | **+0.076** | **+0.028** |
| cloud_shadow | −0.003 | −0.029 | −0.022 |
| macro IoU | −0.009 | +0.015 | +0.042 |

### Thin-cloud (primary research target) — MEASURED

| Seed | IoU base→impr (Δ) | Dice Δ | Recall base→impr | False-negatives base→impr |
|---|---|---|---|---|
| 1 | 0.4605 → 0.5073 (+0.047) | +0.043 | 0.666 → 0.745 | 115,948 → 88,554 |
| 2 | 0.4402 → 0.5158 (+0.076) | +0.069 | 0.556 → 0.705 | 154,221 → 102,652 |
| 3 | 0.5244 → 0.5520 (+0.028) | +0.023 | 0.736 → 0.847 | 91,693 → 53,215 |

**Thin-cloud IoU improves in all 3 seeds: mean +0.050 (± 0.020).** Recall and false-negatives improve in
every seed (attention recovers thin cloud the baseline misses).

### Cloud-shadow (hardest class) — MEASURED

IoU Δ = [−0.003, −0.029, −0.022] — cloud shadow (baseline IoU ≈ 0.08–0.10) **consistently regresses
slightly** under Attention U-Net.

## Failure analysis (M9, real predictions)

Run on real test predictions each seed. Thin-cloud failures (false-negative pixels) **fall every seed**
(e.g. seed 1: 115,948 → 88,554). Confidence-based categories: **NOT MEASURABLE** (no predicted probabilities
persisted). Edge / small-object categories: **DEFERRED** (no spatial connected-component analysis). These
are never fabricated.

## Decision — MIXED

The M11 framework verdict **flips across seeds**: seed 1 **IMPROVED**, seeds 2 & 3 **REGRESSION** (the
framework penalizes worst-class regression, i.e. the cloud-shadow drop). Taking the seeds together:

- **The primary thin-cloud metric consistently and meaningfully improves** (mean IoU +0.050; recall +0.08…
  +0.15; FN reduced 24k–52k) — real evidence supporting the ADR-0010 hypothesis that attention gates aid
  thin-cloud discrimination.
- **This comes with a consistent small cost to cloud shadow** (the hardest class) and a mixed effect on
  thick/clear; macro IoU is roughly flat-to-slightly-positive (mean +0.016).
- Compute cost is modest (×1.01 params, ×1.2–1.3 train time).

**Overall conclusion: MIXED.** On this bounded subset, Attention U-Net is **not a uniform winner** — it
trades cloud-shadow/thick stability for a reliable thin-cloud gain. With only 3 seeds and no formal
significance test, and the overall verdict seed-dependent, we do **not** declare Attention U-Net superior
overall; we **do** report a measured, consistent thin-cloud improvement.

## Reproducibility

Deterministic `config_hash`, dataset `content_hash`, `subset_selection_hash`, `split_config_hash`,
`normalization_hash` recorded in `data/processed/cloudsen12/dataset_artifact.json`. Per-seed comparison
artifacts under `data/processed/cloudsen12/m11*/comparison_artifact.json` (git-ignored). The bounded subset
is reproducible from `(seed=1, subset_size=32)` against L1C part 0.

## Methodological notes (changes recorded honestly)

1. **M11 real-data hook:** a small, isolated `data_provider` parameter was added to `ComparisonRunner`
   (backward-compatible; synthetic path unchanged, all M11 tests still pass) so the existing comparison
   runs on real loaders. No comparison/decision logic changed.
2. **Class-stratified group split:** `build_split_manifest(stratify=True)` was added (opt-in; default off)
   so thin-cloud/cloud-shadow are present in val/test — without it the small 5-sample test split contained
   **no** thin cloud and the primary metric was undefined (INCONCLUSIVE). Whole ROIs are still never split,
   so leakage-freeness is preserved.

## Limitations

- Bounded subset (32 samples, 1 L1C part), one small U-Net config, 12 epochs, 3 seeds — **not** AC-4.
- n=3 seeds, no formal significance test; overall verdict is seed-dependent.
- Cloud-shadow IoU is low (~0.08–0.10) for both models on this subset — a hard, under-represented class.
- Confidence-based and spatial failure categories remain NOT MEASURABLE / DEFERRED.
- These numbers do **not** populate the formal project KPIs (which stay NOT YET MEASURED pending the full
  frozen-envelope evaluation).
