# Milestone Plan (20 Milestones → O1–O5 Gates)

> **Deliverable ID:** D1 (partial) · **Milestone:** M1 · **Status:** DRAFT for approval
> Rule: **never skip a milestone**; after each, STOP and wait for the project owner's approval.

---

## Mapping to Objectives & Gates

| Semester | Objective | Gate | Milestones |
|----------|-----------|------|------------|
| CP1 (VII) | O1 — validate problem, baseline | Gate 1 | M1, M2, M3, M4, M5, M6 |
| CP1 (VII) | O2 — reproducible reference + vertical slice | Gate 2 | M7, M8, M9 |
| CP2 (VIII) | O3 — differentiating contribution | Gate 3 | M10, M11 |
| CP2 (VIII) | O4 — integrated operable system | Gate 4 | M12, M13, M14, M15, M16, M17 |
| CP2 (VIII) | O5 — independent acceptance | Final Gate | M18, M19, M20 |

## Milestone Detail

| # | Milestone | Key outputs | Exit criteria |
|---|-----------|-------------|---------------|
| **M1** | Project planning | Charter, requirements+traceability, boundary, architecture, source-to-claim map, risk register, KPI/AC/NT plan, ADRs, assumptions log. | This document set approved. |
| **M2** | Folder structure | Full repo scaffold, pinned env (`pyproject`/`requirements`), config system, logging, base `core/`, empty tested modules, CI YAML stubs. | Clean install works; `pytest` collects; no hardcoded paths. |
| **M3** | Dataset download | `scripts/download` for CloudSEN12 subset (+ On Cloud N reference); manifest with provenance; licence recorded. | Data fetched & manifest validates. |
| **M4** | Dataset preprocessing | Band handling, normalization, spectral indices (NDSI, cirrus), tiling, augmentation, **spatial-block split** + leakage report, dataset statistics. | Splits reproducible; no spatial leakage; stats reported. |
| **M5** | Visualization | Scene/label/index viewers; overlay of mask vs image; uncertainty/coverage display (supports NT-4). | Visual QA of samples passes. |
| **M6** | Baseline model | **U-Net** implementation + training loop skeleton + Dice/CE losses + TorchMetrics. | Baseline trains on smoke subset; metrics logged to MLflow. |
| **M7** | Training | Full training pipeline, schedulers, checkpointing, MLflow params/metrics/artifacts, frozen resource envelope (AC-4). | Reproducible training run; checkpoints saved. |
| **M8** | Evaluation | Metric suite (IoU/Dice/Prec/Rec/F1/PixAcc), **stratified evaluator**, spatial-holdout eval, KPI-3 rubric frozen, 95% CIs. | O2 baseline KPI values measured & recorded (no longer "NOT YET MEASURED"). |
| **M9** | Confusing-case evaluation | Stratified results by thin cloud/haze/snow/bright surface; **NT-1, NT-2, NT-3** fixtures + guardrails + degraded mode + recovery. | O2 reference frozen; negative tests 1–3 pass. **CP1 Gate 2.** |
| **M10** | Improved model | **Attention U-Net**, **DeepLabV3+** (+ SegFormer *optional*); snow/bright-surface features; O3 contribution. | Candidate trains; measured vs O2 on same evidence. |
| **M11** | Comparison | Model comparison under AC-4; ablation & sensitivity; baseline-vs-candidate KPI table with CIs; defensible conclusion. | KPI-1/2 populated for O3; trade-offs documented. **CP2 Gate 3.** |
| **M12** | Change detection | Bi-temporal change task; measure masking-error → change-error (KPI-3); **NT-4**. | Downstream impact quantified. |
| **M13** | Backend API | FastAPI: `/train /predict /evaluate /models /history /upload /metrics /version /docs`; SQLite persistence; logging/telemetry. | Endpoints pass API tests; Swagger live. |
| **M14** | Frontend | React/TS/Vite: dashboard, upload, prediction, comparison, statistics, map viewer, history, metrics. | UI talks to API for core flows. |
| **M15** | Integration | End-to-end wiring; degraded mode + recovery; **NT-5** (lineage/idempotent replay). | Full flow works; degraded/recovery demonstrated. |
| **M16** | Testing | Unit + integration + API + model tests; acceptance harness (D5) covering AC-1..4, all KPIs, all NTs. | Test suite green; coverage reported. |
| **M17** | Docker | Dockerfiles + compose; GDAL/geo deps pinned; clean-env rebuild test. | `docker compose up` runs the system. |
| **M18** | Documentation | README, API docs, architecture, dataset guide, install, user manual, dev guide, deployment guide. | Docs complete & consistent. |
| **M19** | Research paper | Literature review, citations/references, comparison table, ablation template, results write-up. | Paper draft complete. |
| **M20** | Presentation | Poster + slides + demo video + individual contribution evidence. | Final acceptance package ready. **CP2 Final Gate.** |

## Deliverable → Milestone Map

| Deliverable | Milestones |
|-------------|-----------|
| **D1** charter/requirements/boundary/architecture/source-to-claim | M1 |
| **D2** reproducible reference + fixtures/oracle/tests/baseline/resource profile | M6–M9 |
| **D3** independently-testable contribution + comparative evidence | M10–M11 |
| **D4** complete system + config/interfaces/telemetry/degraded/recovery | M12–M17 |
| **D5** acceptance harness (AC-1..4, all KPIs, all NTs) | M16 |
| **D6** repo package, manifest, install/operating guide, API docs, reproducibility | M17–M18 |
| **D7** final report/paper, poster, demo video, viva/contribution evidence | M19–M20 |

## Current status

- **M1: COMPLETE** (approved) — planning deliverable set + review revisions.
- **M2: COMPLETE** (approved) — project scaffold (directories + import-clean placeholders, requirements
  sources on Python 3.11.x, config/logging/pytest/CI/Docker placeholders). No app logic, no installs.
- **M3: COMPLETE** (approved) — dataset management: provenance manifest (`datasets.yaml`, metadata verified),
  metadata + licence docs, and resumable download / verify scripts. **No data downloaded** (scripts
  document, never bypass). No preprocessing/ML.
- **M4: COMPLETE** (approved) — preprocessing pipeline: records, config, loader, validation, patching,
  patch manifest, normalization, splitting, augmentation framework, orchestration + synthetic-data tests.
- **M5: COMPLETE** (approved) — visualization & EDA: backend-independent plotting abstraction, statistics,
  inspection, JSON/CSV/Markdown reports, QC reports, colour mapping, figure specs, FigureManifest +
  VisualizationSession, `eda_report.py`, synthetic-data tests.
- **M6: COMPLETE** (approved) — baseline model: ADR-0006 (U-Net), `ModelConfig`, baseline U-Net, weight-init
  strategies, registry/factory, checkpoint/experiment/model/artifact metadata, parameter counting, tests.
- **M7: COMPLETE** (approved) — training engine: ADR-0007, config-driven optimizer/scheduler/loss,
  `TrainingEngine`/`Trainer`, callbacks (events+priorities), checkpoint manager, JSON/CSV logging,
  deterministic seeding, `ExperimentRun`, `TrainingArtifact`, `TrainerState` machine, synthetic tests.
- **M8: COMPLETE** (approved) — evaluation: ADR-0008, confusion matrix, per-class + macro/micro/weighted
  metrics, explicit undefined values, stratified, `EvaluationRunner`, JSON/CSV/MD reports, `evaluate.py`,
  synthetic tests (batch==global). numpy guarded; no ML/deploy/UI/benchmark.
- **M9: COMPLETE** (approved) — confusing-case / failure analysis: ADR-0009, taxonomy + measurability,
  pixel/sample error records (reuses M8), deterministic ranking + dedup + top-K, stratified summaries,
  backend-independent viz specs, reports, `analyze_failures.py`, synthetic tests.
- **M10: COMPLETE** (awaiting approval) — improved model: ADR-0010 (Attention U-Net selected), shared
  `blocks`, `attention_unet` registered alongside `unet` (U-Net regression verified: 29,706 params
  unchanged), improvement-mechanism metadata, `IMPROVED_MODEL_VERSION`, typed `ArchitectureProfile`/
  `ArchitectureComparison` (params/shapes MEASURED, memory NOT_MEASURED, FLOPs DEFERRED), `model_compare.py`,
  synthetic tests. No training/optimizer/loss/eval changes. **Performance NOT YET MEASURED.**
- **M11: COMPLETE** (awaiting approval) — controlled comparison: ADR-0011, `app.comparison` package
  (single-source `ComparisonConfig` + fairness guardrails, quality/compute records, thin-cloud-primary
  decision framework, `ModelComparisonArtifact` with deterministic content hash), **reuses** the M7
  trainer + M8 evaluation + M9 failure analysis (no second engine of any kind), `compare_models.py` CLI
  with `--synthetic-smoke`, tests + framework-free manual harness, `COMPARISON_VERSION`. Synthetic smoke
  runs both real architectures end-to-end (compute **MEASURED**; quality **SYNTHETIC / VALIDATION ONLY**).
  **Real-data quality NOT YET MEASURED → decision INCONCLUSIVE** (no winner fabricated).
- **M12: COMPLETE** (awaiting approval) — experimental-dataset readiness pipeline: ADR-0012, `app.datasets`
  M12 modules (experimental config, availability, typed records, validation gates, deterministic subset,
  group-aware split manifest, real class distribution + train-only normalization, `DatasetArtifact` with
  deterministic content hash, `is_experiment_ready()` gate + M11 handoff, orchestration, synthetic fixture),
  **reuses** M3 integrity + M4 splitting/patching/normalization + M5 statistics (no second downloader/
  validator/splitter), `prepare_dataset.py` / `validate_dataset.py` CLIs, tests + framework-free manual
  harness, `DATASET_MANIFEST_VERSION`. Synthetic fixture validates the whole pipeline (PIPELINE VALIDATION
  ONLY). **Real CloudSEN12 NOT PRESENT (rasterio/tacoreader absent; no download performed) → readiness gate
  = False; real model quality NOT YET MEASURED.** No M11 change.
- **M13–M20: NOT STARTED.** *(This milestone brief scoped M12 as the dataset-readiness pipeline; the
  original plan's "Change detection" work follows in a later milestone.)*
