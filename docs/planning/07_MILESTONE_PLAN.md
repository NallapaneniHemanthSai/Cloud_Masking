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
- **M3: COMPLETE** (awaiting approval) — dataset management: provenance manifest (`datasets.yaml`),
  metadata + licence docs, and resumable download / verify scripts. **No data downloaded** (access marked
  *requires verification*; scripts document, never bypass). No preprocessing/ML.
- **M4–M20: NOT STARTED.**
