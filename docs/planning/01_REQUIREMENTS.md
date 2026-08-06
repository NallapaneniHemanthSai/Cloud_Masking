# Requirements & Traceability — Cloud Masking

> **Deliverable ID:** D1 (partial) · **Milestone:** M1 · **Status:** DRAFT for approval

This document lists every mandatory requirement from the specification and maps it to the milestone,
component, and acceptance evidence that will satisfy it. **No requirement is dropped.**

---

## 1. Functional Requirements (FR)

| ID | Requirement (verbatim intent) | Realised by (component) | Milestone | Acceptance evidence |
|----|-------------------------------|-------------------------|-----------|---------------------|
| **FR-1** | Ingest/acquire multi-spectral satellite imagery with cloud annotations (**primary: CloudSEN12; reference benchmark: On Cloud N** — both retained, see Charter §3.1); validate version, provenance, schema, units, quality gates **before use**. | `backend/datasets`, `scripts/download_*`, `scripts/validate_dataset` | M3–M4 | Dataset manifest + validation report; schema/CRS/units checks pass. |
| **FR-2** | Reproduce the reference ("stratify by thin cloud, haze, snow") via a **one-command** path with an **independent expected-result oracle**. | `scripts/run_reference.sh`, `backend/evaluation/oracle.py` | M6–M9 | One-command run rebuilds baseline; oracle re-derives expected metrics independently. |
| **FR-3** | Implement cloud-vs-bright-surface discrimination as a **separately testable** subsystem with versioned config + evidence. | `backend/models` (Attention U-Net / DeepLabV3+), `backend/preprocessing/indices.py` (NDSI, cirrus) | M10 | Standalone module + unit tests + versioned config; comparison vs O2. |
| **FR-4** | Implement & verify downstream change-detection impact with input/output/error/config/telemetry contracts. | `backend/change_detection` | M12 | Contract tests; masking-error → change-error measurement. |
| **FR-5** | Implement & verify multi-spectral segmentation with full I/O/error/config/telemetry contracts. | `backend/models`, `backend/services/prediction` | M6–M7, M13 | Contract tests; API `/predict` telemetry. |
| **FR-6** | Deliver the **complete demonstrable system** — no isolated notebook/model/dashboard counts as completion. | Whole system: API + web app + Docker | M13–M17 | End-to-end demo; integration + system tests. |
| **FR-7** | Detect NT-1 condition (overall accuracy dominated by easy pixels), invoke documented safe/degraded response, retain recovery evidence. | `backend/evaluation/guardrails.py`, degraded-mode flag | M8–M9, M15 | NT-1 fixture triggers abstain/degraded + labelled result + recovery log. |

## 2. Non-Functional Requirements (NFR)

| ID | Requirement | Realised by | Milestone | Acceptance evidence |
|----|-------------|-------------|-----------|---------------------|
| **NFR-1** Performance | Meet every accepted KPI target under AC-1 & AC-4, incl. tail values and resource cost. | Training + eval harness; frozen resource envelope | M7–M11 | KPI table populated; resource profile recorded. |
| **NFR-2** Reliability/recovery | Pass every mandatory negative test; a critical failure cannot be hidden by an average. | Guardrails + subgroup reporting | M9, M16 | NT-1..5 all pass; per-subgroup metrics reported. |
| **NFR-3** Domain assurance | CRS, registration, resolution, temporal alignment, missing coverage made explicit. | `backend/preprocessing`, geo-metadata checks | M4 | Every scene carries CRS/registration/resolution/nodata metadata. |
| **NFR-4** Evidence quality | Independent **spatial** validation prevents leakage across neighbouring dev/test areas. | Spatial-block splitter | M4, M8 | Split report proves no spatial overlap between train/val/test. |
| **NFR-5** Maintainability | Version control, automated tests, documented interfaces, config validation, clean-env build. | pytest, Pydantic config, Docker | M16–M17 | CI config; clean-env rebuild succeeds. |
| **NFR-6** Operability | Logs, measurements, health/quality indicators, operator guidance, degraded mode, verified recovery. | Structured logging, `/metrics`, `/version`, health endpoint | M13, M15 | Logs + health + degraded-mode + recovery procedure demonstrated. |

## 3. Machine-Learning Requirements

| Requirement | Plan |
|-------------|------|
| Models | Baseline **U-Net** (M6) → **Attention U-Net**, **DeepLabV3+** (M10); **SegFormer** *(OPTIONAL, time-permitting)*. |
| Losses | **Dice Loss** + **Cross-Entropy** (and combined Dice+CE); documented in `backend/training/losses.py`. |
| Metrics | **IoU, Dice, Precision, Recall, F1, Pixel Accuracy** via TorchMetrics; plus stratified/per-class variants. |
| Comparison | All models compared under the **same** evidence + frozen resource envelope (AC-4). Milestone 11. |
| Experiment tracking | **MLflow** — parameters, metrics, artifacts, models. |

## 4. Interface / Endpoint Requirements (Backend — FastAPI)

`/train` · `/predict` · `/evaluate` · `/models` · `/history` · `/upload` · `/metrics` · `/version` · `/docs` (Swagger).

## 5. Frontend Requirements (React + TypeScript + Vite)

Dashboard · Image Upload · Prediction · Comparison · Statistics · Map Viewer (Leaflet/MapLibre) ·
Prediction History · Metrics Dashboard.

## 6. Database Requirements (SQLite in dev)

Persist: model versions · metrics · predictions · training history.

## 7. Reproducibility Requirements

A clean environment must rebuild: O2 reference, O3 contribution, integrated system, and acceptance evidence,
using a **version-pinned toolchain**, fixed **seeds/config**, and a scripted runbook. Full path:
`git clone → install → download → train → evaluate → predict`.

## 8. Validation Requirements

Evaluate on: **Thin Clouds · Snow · Bright Surfaces · Cross-Region · Cross-Season**, using
**spatially disjoint** holdout areas and verified CRS (AC-3).

**Haze:** CloudSEN12 has no haze label. Haze is **approximated as thin cloud** and reported **qualitatively
within the thin-cloud stratum**; it is **not a separately measured objective** and has **no standalone KPI**
(consistent with Charter §3.1, `06_KPI_ACCEPTANCE.md`, and `08_ASSUMPTIONS.md` AS-02).

## 9. Consolidated Traceability Matrix

Every Objective (O), Functional Requirement (FR), Non-Functional Requirement (NFR), Acceptance Condition (AC),
and Negative Test (NT) maps to an **architecture component**, a **milestone**, **planned evidence**, and a
**validation method**. (FR/NFR component + milestone + evidence detail is in §1–§2; this matrix adds the
validation method and extends the trace to O/AC/NT.)

### 9.1 Objectives

| ID | Architecture component | Milestone | Planned evidence | Validation method |
|----|------------------------|-----------|------------------|-------------------|
| **O1** | `models` (U-Net), `services/prediction` | M6 | Baseline overall-accuracy result | Spatial-holdout eval on CloudSEN12; MLflow run. |
| **O2** | `evaluation/stratified_evaluator`, `scripts/run_reference` | M7–M9 | Stratified reference results + resource profile | Stratified metrics + 95% CI per subgroup; oracle re-derivation (FR-2). |
| **O3** | `models` (Attention U-Net/DeepLabV3+), `preprocessing/indices` | M10–M11 | Baseline-vs-candidate comparison | Same-evidence, same-envelope (AC-4) comparison + ablation. |
| **O4** | `change_detection` | M12 | Masking-error → change-error measurement | Controlled change-detection task; KPI-3 rubric (two raters). |
| **O5** | acceptance harness (D5), `evaluation` | M18–M20 | Cross-region/season validation report | Independent-reviewer acceptance; AC-1..4 + NT-1..5 executed. |

### 9.2 Functional & Non-Functional Requirements — validation method

| ID | Validation method |
|----|-------------------|
| **FR-1** | Manifest schema/CRS/unit/nodata checks; `pytest` dataset-validation tests. |
| **FR-2** | One-command reference run reproduces baseline; independent oracle recomputes expected metrics. |
| **FR-3** | Standalone module unit tests; versioned-config diff; O3-vs-O2 comparison. |
| **FR-4** | Contract tests (input/output/error/config/telemetry) + downstream-impact measurement. |
| **FR-5** | Contract + API tests on `/predict`; telemetry assertions. |
| **FR-6** | End-to-end system test; demo video (D7). |
| **FR-7** | NT-1 fixture triggers guardrail → degraded mode + recovery log. |
| **NFR-1** | KPI table populated from measured runs under AC-4 envelope. |
| **NFR-2** | NT-1..5 pass; per-subgroup metrics prove no aggregate masking. |
| **NFR-3** | Every scene asserts CRS/registration/resolution/nodata metadata present. |
| **NFR-4** | Automated spatial-leakage check on train/val/test split. |
| **NFR-5** | Clean-environment rebuild + `pytest` green in CI. |
| **NFR-6** | Health/`/metrics`/`/version` endpoints; degraded-mode + recovery demonstrated. |

### 9.3 Acceptance Conditions & Negative Tests

| ID | Architecture component | Milestone | Planned evidence | Validation method |
|----|------------------------|-----------|------------------|-------------------|
| **AC-1** | `evaluation/stratified_evaluator` | M8–M9, M18 | Region/season stratified results | Cross-region/season eval on spatial holdout. |
| **AC-2** | `evaluation/guardrails` | M9 | Boundary-case results | NT-1/2/3 fixtures exercised. |
| **AC-3** | spatial-block splitter | M4, M8 | Leakage report; reserved acceptance set | Spatially-disjoint holdout reserved before O3 tuning. |
| **AC-4** | `configs/full` profile | M7–M11 | Frozen resource profile | Identical versions/workload/hardware for O2 & O3. |
| **NT-1** | `evaluation/guardrails` | M9 | Easy-pixel-dominance fixture + recovery log | Guardrail fails run if subgroup hidden; degraded mode + recovery. |
| **NT-2** | `evaluation/guardrails` | M9 | Snow-as-cloud fixture | Detect/abstain/label + recovery. |
| **NT-3** | `evaluation/guardrails` | M9 | Thin-cloud-leak fixture | Detect/abstain/label + recovery. |
| **NT-4** | `frontend/map viewer`, `evaluation` | M12/M14 | Map-hides-uncertainty fixture | Surface uncertainty/coverage/resolution; no misleading map. |
| **NT-5** | `db`, `services` lineage | M15 | Invalid-record fixture | Detect before commit; idempotent replay; complete lineage. |

The reverse trace (claim → acceptance result) is maintained by the acceptance harness (D5) in Milestones 8–9 and 16.
