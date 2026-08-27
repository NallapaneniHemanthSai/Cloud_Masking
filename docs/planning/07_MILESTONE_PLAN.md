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
- **First REAL experiment: EXECUTED** (2026-08-20) — bounded CloudSEN12+ subset (32 expert-labelled L1C
  samples, CC0) acquired via **tacoreader 0.6.5** (raw git-ignored), passed the M12 readiness gate (READY;
  ROI-grouped leakage-free stratified split; thin cloud in every split; train-only normalization), and drove
  the **real M11** U-Net vs Attention U-Net comparison on **MPS** (reused M7/M8/M9; only architecture
  differs). Real, MEASURED, 3-seed result: **thin-cloud IoU consistently improves (mean +0.050)** with a
  small cloud-shadow trade-off → **overall MIXED** (no forced winner). Bounded first run, **not** AC-4;
  formal KPIs remain NOT YET MEASURED. Adapters added: M11 `data_provider` hook + M12 stratified group split
  (both small, tested, backward-compatible). See `docs/comparison/real_experiment_cloudsen12.md`.
- **M13: COMPLETE** (awaiting approval) — Backend API: ADR-0013, FastAPI app factory (`app.main.create_app`,
  import-clean/lazy) with `/train /predict /evaluate /models /history /upload /metrics /version /health` +
  Swagger `/docs`, **SQLite** persistence (SQLAlchemy 2.0: model versions / training runs / predictions /
  evaluations / uploads), request **telemetry** middleware, and structured logging. Thin routers → typed
  Pydantic v2 DTOs → **services** that reuse M6 models, M4 preprocessing, M7 training, M8 evaluation, M9 —
  no domain logic or duplicated infrastructure in the API. `serve_api.py` launcher; framework-free tests
  (no httpx). All API-produced results are **SYNTHETIC / VALIDATION ONLY**; the M11 MIXED conclusion and the
  cloud-shadow regression are untouched. Verified: 15 API tests + live uvicorn smoke (Swagger live);
  M11 (23) / M12 (18) / import (100) / structure regressions still green.
- **M14: COMPLETE** (awaiting approval) — Frontend: ADR-0014, React 18 + TypeScript 5 (strict) + Vite 6 SPA
  under `frontend/src` (services/apiClient+api+types, hooks, SystemContext, components, 10 pages: Dashboard,
  Models, Predict, Evaluate, Comparison, Upload, History, Metrics, MapViewer, SystemHealth). A **centralized
  typed axios client** consumes the M13 API via a **Vite same-origin proxy** (no backend/CORS change; backend
  untouched in M14). Reuses the **M5 CloudSEN12 palette** verbatim; explicit loading/error/empty states;
  every `/train`+`/evaluate` result badged **SYNTHETIC**; the Comparison page shows the **REAL bounded**
  result with the **MIXED** conclusion preserved (cited from the report, not reinterpreted); mask
  rendering/geo-overlay **DEFERRED** (no fabricated masks). Verified: `npm install` + `tsc --noEmit` + `vite
  build` clean; live backend+Vite integration smoke (proxy → all endpoints 200); **real browser render** of
  Dashboard/Models/Comparison/Evaluate with live data + a live `POST /evaluate` round-trip. M11 (23) / M12
  (18) / M13 (15) regressions still green.
- **M15: COMPLETE** (awaiting approval) — Integration: ADR-0015, degraded mode + recovery + **NT-5**
  (lineage / idempotent replay) in `db`/`services`, **reusing** M8 + M13 (no new engine/dependency). New:
  `LineageRow`+`SystemEventRow` tables; `lineage_service` (`idempotent_get_or_create` = **detect-before-commit**
  + get-or-create; `record_lineage`/`get_chain`); `integration_service` (aggregate-hides-subgroup guardrail
  wiring `GuardrailViolation` → degraded mode, `enter_degraded`/`recover`/`system_status`/`run_masking_pipeline`);
  `status` router (`GET /status`, `POST /recover/{id}`, `GET /lineage`, `POST /pipeline`); an additive
  frontend **Status** page. Existing API contracts unchanged; results **SYNTHETIC/DEMO** only; M11 **MIXED**
  conclusion untouched. Verified: 10 M15 tests + a **live degraded→recovery→operational smoke** through the
  Vite proxy + a **browser** recover-in-UI check; M11 (23) / M12 (18) / M13 (15) green; frontend build/typecheck
  clean; imports 100/100. `docs/integration/`.
- **M16: COMPLETE** (awaiting approval) — Testing / acceptance harness (**D5**): ADR-0016, `app.acceptance`
  package (deterministic SYNTHETIC fixtures + guardrails + `run_acceptance` harness + `AcceptanceReport`
  JSON/MD), proving **NT-1..NT-5** each with a pass fixture (must not fire) + fail fixture (must fire).
  **Reuses** M8 confusion (NT-2/NT-3), M15 `check_aggregate_hides_subgroup` (NT-1) + degraded/recovery +
  lineage (NT-5) — no duplicated metric/degraded system. New NT-2/NT-3/NT-4 detections. `run_acceptance.py`
  CLI (exits non-zero on failure); `GET /acceptance` + additive frontend **Acceptance** page. **Safety
  properties PASS on synthetic fixtures; KPI/AC-4 acceptance NOT YET MEASURED** (never fabricated); M11
  **MIXED** untouched. Verified: 13 M16 tests + harness CLI + live `/api/acceptance` + browser render; M11
  (23) / M12 (18) / M13 (15) / M15 (10) green; frontend build/typecheck clean. `docs/acceptance/`.
- **M17: COMPLETE** (awaiting approval) — Docker / deployment: ADR-0017, functional **backend** image
  (`python:3.11-slim`, deps **pinned** in `docker/requirements-backend.txt` incl. **rasterio/GDAL** —
  Risk R-12; non-root; stdlib `/health` healthcheck) and a multi-stage **frontend** image
  (`node:20-alpine` build → `nginx:1.27-alpine` static serve + `/api`→`backend:8000` proxy mirroring the
  Vite rewrite, ADR-0014). `docker/docker-compose.yml` wires a private network, **health-gated** startup,
  and a **named volume** for the SQLite/app data (`sqlite:////data/cloud_masking.db`); the nginx site is
  an envsubst **template** with Docker-DNS **runtime re-resolution** (proxy survives a backend restart);
  repo-root `.dockerignore` for a source-only, reproducible clean-env rebuild. Configuration is env-driven
  with safe defaults and **no secrets**; no earlier-milestone semantics changed; NT-1..5 + M11 **MIXED**
  untouched. Backend bundles **CPU torch** (audited import set; MPS host-only) so **every** endpoint runs
  in-container; deployed results are **SYNTHETIC/DEMO** only, KPIs **NOT YET MEASURED**. New CLI
  `scripts/verify_deployment.py` (black-box stack probe, non-zero exit) + `tests/test_deployment.py`
  (34 static contract tests, no daemon needed). **R-12 confirmed in practice:** the first clean build
  failed with `ImportError: libexpat.so.1` — rasterio's wheel bundles GDAL but still links system libs
  absent from `slim`; fixed with an explicit `libexpat1` layer plus **build-time import assertions**
  (and a no-CUDA-payload assertion, torch coming from the CPU wheel index). **Verified live:**
  `build --no-cache` green; `compose up` health-gated; 9/9 deployment checks through both the API and
  the nginx `/api` proxy; `/train`+`/predict` answer 200 in-container on CPU; state survived
  restart **and** a full `down`/`up` (2→3 rows); proxy survived a backend **IP change** (172.20.0.2 →
  172.20.0.4) with the frontend untouched; env overrides (ports/`APP_ENV`/`LOG_LEVEL`) took effect;
  acceptance content hash identical host vs container (`53b906bbc38f`); non-root uid 10001; no secrets
  in either image. Regressions green: M11 23 / M12 18 / M13 15 / M15 10 / M16 13 / M17 34; imports
  100/100; structure 43 dirs + 203 files; frontend typecheck+build clean. `docs/deployment/`.
- **M18–M20: NOT STARTED.** *(This milestone brief scoped M12 as the dataset-readiness pipeline; the
  original plan's "Change detection" work follows in a later milestone.)*
