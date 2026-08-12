# Cloud Masking Across Thin Cloud, Haze, Snow and Bright Surfaces

KL University two-semester engineering capstone (CP1 + CP2). An end-to-end system for multi-spectral
satellite **cloud masking**, with stratified evaluation on thin cloud, snow and bright surfaces, a
cloud-vs-bright-surface contribution, and quantified downstream impact on a change-detection task.

> **Status: Milestone 2 (Project Scaffold) complete.** This repository currently contains the planning
> documents (M1) and the project scaffold (M2) only — **no application logic, no installed dependencies,
> no datasets**. Functionality is delivered milestone-by-milestone per
> [`docs/planning/07_MILESTONE_PLAN.md`](docs/planning/07_MILESTONE_PLAN.md).

## Supported environment

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **Python** | **3.11.x only** | Geo/ML wheels + stable PyTorch Apple-Silicon (MPS) support; host 3.14 not used. See [ADR-0004](docs/adr/ADR-0004-python-runtime.md). |
| **Node** | **≥ 20** | Frontend (React + TS + Vite), scaffolded in M14. |
| **Compute** | Apple Silicon (MPS) / CPU | No CUDA; device auto-detect CUDA > MPS > CPU. See [ADR-0002](docs/adr/ADR-0002-compute-environment.md). |
| **Docker** | optional | Deployment images authored in M17. |

## Project structure

```
Cloud_Masking/
├── backend/            # FastAPI + PyTorch (Python 3.11)
│   ├── app/            # api · core · models · services · preprocessing · inference
│   │                   # training · evaluation · datasets · change_detection · db · schemas · utils
│   ├── tests/          # structure + import tests (M2); functional tests from M6
│   ├── configs/        # config.template.yaml · smoke.yaml · full.yaml · logging.yaml
│   ├── scripts/        # download/validate/preprocess/train/evaluate/predict (M3+)
│   ├── pyproject.toml · requirements.in · requirements-dev.in · .env.example
│   └── README.md
├── frontend/           # React + TypeScript + Vite (scaffolded M14)
│   └── src/            # components · pages · services · hooks · utils · assets
├── docker/             # Dockerfiles + compose (placeholders; M17)
├── docs/               # planning/ · adr/ (M1); user/dev/deploy guides (M18)
├── data/               # raw/ · processed/ · samples/  (git-ignored contents)
├── models/             # checkpoints/ trained weights (git-ignored)
├── experiments/        # curated experiment logs / ablations / metric summaries (M7+)
├── notebooks/          # supplementary only (never a deliverable)
├── outputs/            # logs · mlruns · sqlite · reports (git-ignored)
├── paper/ · presentation/ · reports/   # research (M19) · slides (M20) · evidence (M8+)
├── .github/workflows/  # CI placeholders (manual-only: workflow_dispatch)
├── .gitignore · .env.example
└── README.md
```

## Architecture summary

Clean architecture with dependencies pointing inward: `core` (config, constants, logging, exceptions)
depends on nothing outside the standard library; `services` (use-cases) depend on `core`; adapters
(`api`, `datasets`, `preprocessing`, `models`, `training`, `evaluation`, `change_detection`, `db`,
`inference`) sit at the edge; delivery is the React frontend + Docker. Cross-cutting concerns —
configuration, logging, experiment tracking (MLflow), and model storage (checkpoints + SQLite) — are
shared. Two datasets are retained: **CloudSEN12** (primary, multi-class) and **On Cloud N** (reference
benchmark, reproduced). Full detail and a component diagram are in
[`docs/planning/03_ARCHITECTURE.md`](docs/planning/03_ARCHITECTURE.md).

## Datasets

Two datasets with distinct roles (see [ADR-0001](docs/adr/ADR-0001-dataset-selection.md)) — **On Cloud N
is retained, not replaced**. Metadata below is **verified** against official sources
([details](docs/datasets/)):

| Role | Dataset | Bands / labels | Licence | Redistribution |
|------|---------|----------------|---------|----------------|
| **Primary** | **CloudSEN12 / CloudSEN12+** | 13-band S2 (L1C); multi-class 0=clear/1=thick/2=thin/3=shadow | **CC0-1.0** | Permitted |
| **Reference benchmark** | **On Cloud N** | 4-band S2 L2A (B02,B03,B04,B08); binary 0/1 | Competition terms | **Prohibited** |

**Folder layout:** `data/{raw/{cloudsen12,on_cloud_n}, external, manifests, metadata, samples}` — heavy
contents under `raw/`/`processed/`/`external/` are git-ignored; provenance (`manifests/datasets.yaml`),
metadata, and docs are tracked.

**Download & verify (nothing downloads automatically at Milestone 3):**
```bash
python backend/scripts/download_cloudsen12.py --dry-run    # primary
python backend/scripts/download_on_cloud_n.py --dry-run    # reference benchmark
python backend/scripts/verify_datasets.py                  # structured provenance + integrity table
```
Scripts read `data/manifests/datasets.yaml`. Both datasets need manual/authenticated access (CloudSEN12
via `tacoreader`/Hugging Face; On Cloud N via DrivenData registration + agreement), so the scripts
**print the documented manual steps instead of bypassing them**.

**Storage / expected size (verify at download):** CloudSEN12+ full is very large (hundreds of GB+); a
curated subset is used (Milestone 4). On Cloud N training data is ≈ tens of GB (22,728 chips). Confirm
disk before downloading (Risk R-03).

**Workflows:**
- *Provenance* — declare in `datasets.yaml` → verify access/licence in [`docs/datasets/`](docs/datasets/).
- *Verification* — `verify_datasets.py` validates the manifest and prints a per-dataset status table
  (manifest / directory / download / checksum / completeness / overall); not-yet-downloaded = `PENDING`
  (not a failure); `--require-present` enforces presence.
- *Checksum* — `checksum` is `TBD` until download; record `sha256` per artifact, then verification reports
  `VERIFIED`/`MISMATCH` (vs `UNAVAILABLE`).
- *Lifecycle* — `declare → verify access → download → record date+checksum → verify → preprocess (M4)`.

## Preprocessing (Milestone 4)

Modular pipeline under `backend/app/preprocessing/` — **no model/training code**. Full detail in
[`docs/preprocessing/`](docs/preprocessing/).

| Stage | Module | Notes |
|-------|--------|-------|
| Load / discover | `loader.py` | Layouts for CloudSEN12 + On Cloud N; graceful missing-dataset reporting. |
| Validate | `validation.py` | Structured report: missing files, unsupported types, duplicate ids, inconsistent dimensions, corrupted metadata. |
| Patch | `patching.py` | Deterministic grid + geotransform propagation. |
| Normalize | `normalization.py` | Per-band minmax/zscore/percentile; clipping; nodata handling. |
| Split | `splitting.py` | Reproducible, group-aware (leakage-resistant) train/val/test + manifest. |
| Augment | `augmentation.py` | Registry/framework only (not applied during training here). |

```bash
python backend/scripts/preprocess.py --dataset on_cloud_n --patch-size 256 --overlap 32   # dry plan
python backend/scripts/split_dataset.py --dataset cloudsen12 --seed 42                     # split manifest
```

## Visualization & EDA (Milestone 5)

Backend-independent visualization + exploratory analysis under `backend/app/visualization/` — **no ML
code**. Full detail in [`docs/visualization/`](docs/visualization/).

| Area | Module | Notes |
|------|--------|-------|
| Backends | `backends.py` | `PlotBackend` (Null / Matplotlib); `get_backend("auto")`; matplotlib guarded. |
| Statistics | `statistics.py` | Deterministic class/dataset/patch/split summaries from records. |
| Inspection | `inspection.py` | `DatasetInspectionReport` (samples, sizes, missing labels, duplicates, balance). |
| Reports | `reports.py` | `Report` → **JSON / CSV / Markdown**; dataset/patch/split/preprocessing builders. |
| QC | `qc.py` | Structured + Markdown quality-control report. |
| Colours | `colormap.py` | Class colour mapping + legends (hex only). |
| Figure specs | `bands.py` / `overlays.py` / `patches.py` | RGB/false-colour, ground-truth mask/overlay, patch grid. |
| Provenance | `manifest.py` / `session.py` | `FigureManifest` (per-figure metadata, deterministic `config_hash`) and `VisualizationSession` (primary workflow object) — full JSON export/import. |

```bash
python backend/scripts/eda_report.py --dataset on_cloud_n            # EDA (json/md/csv) + QC (md)
python backend/scripts/eda_report.py --dataset cloudsen12 --backend null   # force graceful degradation
```

`eda_report.py` produces a top-level `<dataset>_session.json` (a `VisualizationSession` aggregating the
dataset summary, report refs, and QC report) alongside the EDA/QC reports. When matplotlib is unavailable,
figure rendering **degrades** (writes a `*.spec.json` metadata sidecar) while all statistics/reports keep
working.

## Baseline model (Milestone 6)

Baseline **U-Net** + model infrastructure under `backend/app/models/` — **no training/inference code**.
Full detail in [`docs/models/`](docs/models/) and [ADR-0006](docs/adr/ADR-0006-baseline-model-selection.md).

| Area | Module | Notes |
|------|--------|-------|
| Config | `config.py` | `ModelConfig` (in/out channels, depth, base channels, activation, norm) + deterministic `config_hash`. |
| Architecture | `unet.py` / `base.py` | U-Net `Encoder`/`DecoderStage`/`SegmentationHead`; `BaseSegmentationModel` (torch-guarded). |
| Registry/factory | `registry.py` / `factory.py` | `ModelRegistry` (aliases/tags/version) + `ModelFactory` (config→model, summary, checkpoint metadata). |
| Init | `initialization.py` | Xavier / Kaiming / Constant / Identity + optional `InitializationReport`. |
| Metadata | `metadata.py` / `summary.py` / `artifact.py` | `ModelMetadata` (+ capability metadata), `CheckpointMetadata`, `ExperimentMetadata`, `ModelArtifact` (canonical saved-model metadata, deterministic `content_hash`), `ModelSummary` — all JSON serialisable. |

```bash
python backend/scripts/model_info.py --name unet --in-channels 13 --classes 4   # summary + checkpoint metadata
```

PyTorch is a guarded dependency: importing `app.models` never requires it; building a model does (clear
`ModelError` otherwise). No weights are saved and no metrics are recorded in this milestone.

## Training engine (Milestone 7)

Configuration-driven `Trainer` under `backend/app/training/` — **no evaluation/benchmark/deployment code**.
Full detail in [`docs/training/`](docs/training/) and [ADR-0007](docs/adr/ADR-0007-training-strategy.md).

| Area | Module | Notes |
|------|--------|-------|
| Config | `config.py` | `TrainingConfig` (+ optimizer/scheduler/loss/checkpoint/logging/early-stopping) + deterministic `config_hash`. |
| Engine/Trainer | `engine.py` / `trainer.py` | Epoch mechanics (forward/loss/backward/accumulation/AMP) + orchestration. |
| Optimizer/Scheduler | `optimizer.py` / `scheduler.py` | Adam/AdamW/SGD; Cosine/Step/Plateau — selected by config. |
| Loss | `loss.py` | cross-entropy / soft Dice / combined (the optimization objective). |
| Checkpointing | `checkpoint.py` | best/latest, save policy, resume metadata (weights optional). |
| Callbacks | `callbacks.py` | `CallbackEvent` enum dispatch + explicit `CallbackPriority` ordering; checkpoint/logging/early-stopping/progress — independent of the trainer. |
| Lifecycle | `lifecycle.py` | `TrainerState` state machine (CREATED→INITIALIZED→RUNNING↔CHECKPOINTING→COMPLETED/FAILED). |
| Artifact | `artifact.py` | `TrainingArtifact` — canonical completed-run metadata, deterministic `content_hash`. |
| Logging | `logging.py` | `MetricSink` → JSONL/CSV/console (TensorBoard isolated behind the interface). |
| Reproducibility | `seed.py` | seed + deterministic flags + environment capture + device resolution. |
| Experiment | `experiment.py` | `ExperimentRun` + directory layout. |

```bash
python backend/scripts/train_smoke.py --epochs 2 --device cpu   # synthetic run (no real dataset)
```

The trainer takes any iterable of `(inputs, targets)` batches, so it's independent of the dataset layer;
validation/eval metrics plug in at M8 via a callback without trainer changes.

## Evaluation (Milestone 8)

Confusion-matrix-based, **per-class-first** evaluation under `backend/app/evaluation/` — **no ML/training/
deployment code**. Full detail in [`docs/evaluation/`](docs/evaluation/) and
[ADR-0008](docs/adr/ADR-0008-evaluation-strategy.md).

| Area | Module | Notes |
|------|--------|-------|
| Config | `config.py` | Binary vs multiclass modes (never mixed); deterministic `config_hash`. |
| Confusion | `confusion.py` | Pixel-level matrix (rows=true, cols=pred); TP/FP/FN/TN; ignore label. |
| Metrics | `metrics.py` | Per-class IoU/Dice/Precision/Recall/F1 + pixel accuracy; **explicit undefined**. |
| Aggregation | `aggregation.py` | Macro (defined-only) / micro / weighted — accumulate stats, then compute. |
| Runner / Stratified | `runner.py` / `stratification.py` | Accumulate → compute; Overall + Clear/Thick/**Thin**/Shadow + groups. |
| Reports | `report.py` | JSON / CSV / Markdown (reuses the visualization Report model). |

```bash
python backend/scripts/evaluate.py --mode multiclass --split test   # SYNTHETIC demo (not real metrics)
```

**Quality guarantee:** per-class + stratified metrics are mandatory, and aggregation accumulates confusion
statistics before computing — so a high overall score cannot conceal weak thin-cloud detection.

## Failure analysis (Milestone 9)

Confusing-case / failure analysis under `backend/app/failure_analysis/` — **explains** failures, does not
repeat M8 metrics. Full detail in [`docs/failure_analysis/`](docs/failure_analysis/) and
[ADR-0009](docs/adr/ADR-0009-confusing-case-analysis.md).

| Area | Module | Notes |
|------|--------|-------|
| Taxonomy | `taxonomy.py` | 11 categories + **measurability** (MEASURABLE / DEFERRED / NOT MEASURABLE). |
| Pixel/sample | `pixel_analysis.py` / `sample_analysis.py` | Per-class FN/FP/confusion (reuses M8 confusion); per-sample failures. |
| Ranking | `ranking.py` | Deterministic order (severity→rate→count→id); dedup by sample; top-K. |
| Stratification | `stratification.py` | By class (thin cloud visible) / error type / group. |
| Reports / viz | `report.py` / `viz_specs.py` | JSON/CSV/MD; backend-independent confusing-case specs. |

```bash
python backend/scripts/analyze_failures.py --mode multiclass --split test   # SYNTHETIC demo
```

**Answers:** what failed, which class, FP vs FN vs class confusion, hardest samples, severity, whether
failures concentrate in thin/thick cloud/shadow/clear, and whether cases can be visualized later.

## Prerequisites (for later milestones — nothing is installed at M2)

- Python **3.11.x** (e.g. via `pyenv`, `conda`, or a system 3.11).
- Node **20+** (for the frontend, from M14).
- Optionally Docker (from M17).

## Setup (later milestones — do NOT run at M2)

```bash
# Backend (Python 3.11 virtual environment)
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
# Authoritative source is requirements.in; a pinned lock is generated later via pip-compile.
pip install -r requirements-dev.in
```

## Verify the scaffold (Milestone 2)

The structure/import tests are **standard-library only** and pass without installing any dependencies:

```bash
cd backend && python -m pytest -q
```

If `pytest` is unavailable, verify import-cleanliness directly:

```bash
cd backend && python -c "import importlib; [importlib.import_module(m) for m in ['app','app.main','app.core.config','app.core.constants','app.core.exceptions','app.core.logging_config']]; print('imports OK')"
```

## Documentation

- Planning & acceptance: [`docs/planning/`](docs/planning/) — charter, requirements/traceability,
  system boundary, architecture, source-to-claim map, risk register, KPIs/AC/NT, milestone plan,
  assumptions, consistency audit.
- Decisions: [`docs/adr/`](docs/adr/) — ADR-0001 (datasets), ADR-0002 (compute), ADR-0003 (change-detection
  source, deferred), ADR-0004 (Python runtime).

## Project progress

**Current status:** Milestone 9 (Confusing-Case Evaluation & Failure Analysis) complete and under review —
explains *what kind of case* caused each failure (typed taxonomy with measurability), pixel- + sample-level
error records, deterministic hard-example ranking, stratified failure summaries (thin cloud always visible),
reports + backend-independent visualization specs. Reuses M8 primitives (no metric recomputation);
confidence/edge/small-object categories honestly marked NOT MEASURABLE/DEFERRED. **No model/training/
inference/deployment/API/frontend changes.** All outputs synthetic — **real-data failures: NOT YET MEASURED.**

```
✅ Milestone 1  – Planning
✅ Milestone 2  – Project Scaffold
✅ Milestone 3  – Dataset Management
✅ Milestone 4  – Data Preprocessing
✅ Milestone 5  – Visualization & EDA
✅ Milestone 6  – Baseline Model
✅ Milestone 7  – Training Engine
✅ Milestone 8  – Evaluation
✅ Milestone 9  – Confusing-Case Evaluation
⬜ Milestone 10 – Improved Model
⬜ Milestone 11 – Comparison
⬜ Milestone 12 – Change Detection
⬜ Milestone 13 – Backend API
⬜ Milestone 14 – Frontend
⬜ Milestone 15 – Integration
⬜ Milestone 16 – Testing
⬜ Milestone 17 – Docker
⬜ Milestone 18 – Documentation
⬜ Milestone 19 – Research Paper
⬜ Milestone 20 – Final Delivery (Presentation)
```

## Git

The repository owner is the **sole Git author**. This scaffold performs **no** Git operations; suggested
commands are listed in the milestone completion report for the owner to run manually.
