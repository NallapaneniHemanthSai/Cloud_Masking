# ADR-0012 — Experimental Dataset & Reproducible Data Pipeline

- **Status:** ACCEPTED (2026-08-17)
- **Milestone:** M12 (Real Dataset Integration & Reproducible Experimental Data Pipeline)
- **Related:** ADR-0001 (dataset selection), ADR-0002 (compute/MPS envelope), ADR-0004 (Python 3.11),
  ADR-0008 (evaluation), ADR-0011 (controlled comparison); Objectives O2/O3; KPIs; Risks R-01, R-03,
  R-13, R-14, R-15, R-16, R-17

## Context

M3 delivered dataset **provenance/integrity/download** infrastructure and M4 the **preprocessing** pipeline,
but **no real data has ever been downloaded** (`data/raw/*` and `data/processed/*` contain only READMEs /
`.gitkeep`). M12 moves the project from *"dataset infrastructure exists"* to *"a verified, reproducible,
legally usable, locally available experimental dataset exists"* — or, if the data is not present, a
**readiness pipeline + gate** that says so honestly and refuses to hand an invalid dataset to M11.

**Observed local state at M12 start (verified):** CloudSEN12 = **NOT PRESENT**, CloudSEN12+ = **NOT
PRESENT**, On Cloud N = **NOT PRESENT**, processed samples = **NOT PRESENT**; metadata/manifest = **PRESENT**;
recorded checksums = **NONE** (placeholders). Runtime: numpy/torch/matplotlib/PyYAML present; **rasterio
NOT installed** and **tacoreader NOT installed** — so real CloudSEN12 cannot be read here even if downloaded.

## Decisions

### Which dataset for the first real experiment
**CloudSEN12+** (multiclass: `clear` / `thick_cloud` / `thin_cloud` / `cloud_shadow`). It is the primary
dataset (ADR-0001) and the only one that supports the project's thin-cloud objective (O2/O3). On Cloud N is
binary and cannot support thin-cloud stratification, so it can **never** be the primary.

### CloudSEN12 vs CloudSEN12+
Use **CloudSEN12+ v1.1.2** (Hugging Face `tacofoundation/cloudsen12`, Cloud-Optimized GeoTIFF via
`tacoreader ≥ 0.5.3`) — it is the expert-labeled superset and the current maintained release. If tacoreader
is unavailable, the **original CloudSEN12 (2022)** high-quality subset is the fallback. Both share the same
4-class schema and `app.core.constants.CloudClass`, so the pipeline is identical.

### Role of On Cloud N
**Reference / reproduction benchmark only** (binary cloud/no-cloud; cross-dataset domain-shift check, R-13).
Redistribution is **PROHIBITED** (competition terms). It is **never auto-downloaded**, never merged into the
experimental manifest, and never silently promoted to primary.

### Subset strategy
A **deterministic curated subset** (seeded) for the first experiment: prefer the expert-labeled / high-quality
tier; **guarantee thin-cloud and cloud-shadow presence**; diversify by scene/ROI where metadata allows; cap
the patch count to the MPS/CPU envelope (ADR-0002, R-03). Selection is reproducible from `(dataset_version,
seed, subset_size, strategy)` and recorded as a `SubsetSelection` with a hash. Labels are used only to
*guarantee class presence in the pool*; the train/val/test **split** is group-aware and label-agnostic, so
no test labels leak into training-set construction.

### Licensing / access constraints
CloudSEN12/CloudSEN12+ = **CC0-1.0** (public domain; redistribution permitted, citation requested). Raw
rasters are nonetheless kept **git-ignored** to bound repo size (R-03); only small JSON manifests/artifacts
are trackable. Access is programmatic (tacoreader/Hugging Face) and requires the dependency + network — a
**documented manual workflow**, never bypassed, no credentials committed. On Cloud N requires DrivenData
registration + rules acceptance and **prohibits redistribution**.

### Storage strategy
Raw under `data/raw/<dataset>/` (git-ignored); the processed experimental subset + manifests + normalization
stats + artifact under `data/processed/<dataset>/` (git-ignored). Nothing large or license-restricted is ever
committed.

### Download / access mechanism
**Reuse M3** (`app.datasets.download` / `manifest` / `integrity`) — no second downloader. Direct URLs (none
exist for these datasets) would use the resumable downloader; tacoreader/HF and DrivenData are
manual/authenticated, so `download_dataset` returns `manual_access_required` with the documented steps. No
access-control bypass, no scraping, no fabricated URLs.

### Checksum policy
**SHA-256** per file (M3 `compute_checksum`), recorded in a `checksums.sha256` sidecar + the dataset artifact,
and **verified** during validation. Missing checksums read as **NOT VERIFIED**, never as "corrupt".

### Provenance policy
`data/manifests/datasets.yaml` (M3) remains the single provenance source and is **not rewritten**. The
experimental record adds *observed* values (observed files, counts, dimensions) alongside the provenance;
anything unknown stays explicitly **UNKNOWN / NOT VERIFIED / NOT AVAILABLE** — nothing is invented.

### Dataset version policy
`dataset_version` = the release id (e.g. `cloudsen12plus-1.1.2`) combined with the deterministic subset hash,
recorded in the artifact and the M11 handoff so every experiment is traceable to an exact dataset state.

### Train / validation / test split policy
**Deterministic, reproducible, disjoint, group-aware** (M4 `split_samples`). Persisted as
`data/processed/<dataset>/split_manifest.json` with per-sample `sample_id`, `group_id`, `split`,
`dataset_version`, `preprocessing_version`, `seed`, timestamp, and a split-config hash.

### Leakage prevention
Split **by scene/ROI group** so patches from one source scene never straddle splits (NFR-4). Normalization
statistics are fit on **train only**. Explicit assertions verify `train ∩ val = ∅`, `train ∩ test = ∅`,
`val ∩ test = ∅`.

### Patch selection
**Reuse M4** patching / `PatchManifest`. Each patch records patch size, overlap, source scene, source
coordinates, geotransform (where available), band info, label path, and preprocessing version.

### Class-balance handling
Report the **real** per-class distribution (pixel + sample counts, per split) with **thin cloud surfaced
explicitly** — imbalance is never hidden behind a total. The data distribution is **not** silently altered;
class imbalance is handled at *training* time (M7 class weighting / Dice, R-16), and any data-level
intervention would be recorded as an explicit provenance note.

### Reproducibility strategy
Deterministic hashes everywhere: `ExperimentalDatasetConfig.config_hash`, `SubsetSelection` hash, split-config
hash, normalization-statistics hash, and a `DatasetArtifact.content_hash` (ignoring timestamps/notes). Same
inputs + seed ⇒ identical dataset state.

### Data validation gates
A structured `DatasetValidationReport` covering manifest / file existence / checksum / metadata / label /
dimension / band-count / completeness, with overall status ∈ {`READY`, `READY_WITH_WARNINGS`, `INCOMPLETE`,
`INVALID`, `NOT_PRESENT`}.

### What constitutes a valid "experimental dataset"
The `is_experiment_ready()` gate: required files exist, checksums pass, metadata + labels + dimensions valid,
splits disjoint, **required classes (incl. thin cloud) present**, normalization statistics + patch manifest
exist, dataset + preprocessing versions recorded, provenance complete, licensing/access acceptable. If any
**critical** gate fails, `READY = false` and M11 real training must not run against it.

## Honesty (critical)

M12 is a **dataset / experiment-readiness** milestone. It claims **no** model performance — no U-Net or
Attention U-Net superiority, no real IoU/Dice/F1. Real model quality remains **NOT YET MEASURED**. When real
CloudSEN12 is absent, a clearly-labelled **SYNTHETIC / PIPELINE-VALIDATION-ONLY / NOT REAL DATA / NOT A
BENCHMARK** fixture exercises the pipeline; synthetic records are never mixed into the real manifest, and a
synthetic fixture is never called a real dataset.

## Consequences

`app.datasets` gains M12 modules (experimental config, availability check, typed records, validation gates,
subset selection, group-aware split manifest, class distribution + train-only normalization fit, dataset
artifact, readiness gate + M11 handoff, orchestration pipeline, synthetic fixture), two CLIs
(`prepare_dataset.py`, `validate_dataset.py`), tests + a framework-free manual harness, and
`DATASET_MANIFEST_VERSION`. M3/M4/M5/M11 code is **reused, not modified**; the M11 handoff is a small,
isolated adapter. Real dataset status today: **NOT PRESENT**.

## Alternatives rejected

- **On Cloud N as primary** — binary, cannot support thin-cloud stratification (O2/O3); rejected.
- **A second downloader / manifest / validator** — would diverge from M3/M4; rejected in favour of reuse.
- **Auto-downloading On Cloud N or scraping around access controls** — prohibited by its terms; rejected.
- **Random patch-level splits** — risk scene leakage (NFR-4); rejected for group-aware splits.

## Future work

Install `tacoreader`/`rasterio` in the Python 3.11 environment, fetch the curated CloudSEN12+ subset, run the
readiness gate to `READY`, and hand off to M11 for the first **real** controlled comparison (populates
KPI-1/2 for O3). Optional On Cloud N reproduction under its terms for the R-13 domain-shift check.

## Addendum (2026-08-20) — real-data execution

The above future work was carried out. The tacoreader-0.6.5 access route was verified against the installed
library (each L1C sample is a `TORTILLA` of two `GTiff` assets — `s2l1c` 13-band uint16 512×512 + `target`
uint8 label 0–3 — read via rasterio from `/vsisubfile/…/vsicurl/…`); a bounded 32-sample CC0 subset was
acquired (`app.datasets.cloudsen12_access`, reusing M3 integrity) and passed `is_experiment_ready()`. Two
small, tested, backward-compatible adapters were added and are recorded here:

1. **`build_split_manifest(stratify=True)`** — a class-stratified, still-ROI-grouped (leakage-free) split.
   Rationale: a purely random ROI split left the small test set with **no thin-cloud pixels**, making the
   primary metric undefined. Stratification guarantees thin-cloud/cloud-shadow are evaluable in val/test
   without ever splitting an ROI. Default remains off (synthetic path unchanged).
2. **`ComparisonRunner(data_provider=…)`** — a small isolated M12→M11 hook feeding real (x,y) patch batches
   to the *unchanged* M11 comparison/decision logic (all M11 tests still pass). No M8/M9/decision change.

Result (bounded, MEASURED, not AC-4): thin-cloud consistently improved for Attention U-Net across 3 seeds
with a cloud-shadow trade-off → **MIXED**. See `docs/comparison/real_experiment_cloudsen12.md`.
