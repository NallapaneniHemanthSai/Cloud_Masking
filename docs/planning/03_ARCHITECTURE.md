# System Architecture (Planned)

> **Deliverable ID:** D1 (partial) · **Milestone:** M1 · **Status:** DRAFT for approval
> Detailed module code arrives in later milestones; this is the **planned** clean-architecture layout and
> the data/evidence flow it must implement.

---

## 1. Clean-Architecture Principle

Dependencies point **inward**. Domain logic (models, metrics, masking rules) must not depend on delivery
mechanisms (FastAPI, React, SQLite). Concretely:

```
core/  (entities, config, contracts)  ← depended on by everything, depends on nothing
  ▲
services/  (use-cases: train, predict, evaluate, change-detect)
  ▲
api/  (FastAPI routers)     datasets/ preprocessing/ models/ training/ evaluation/ change_detection/  (adapters)
  ▲
frontend/  (React) · docker/ · scripts/   (delivery / orchestration)
```

## 1a. System Component Diagram

```mermaid
flowchart TD
    subgraph Client
        FE["React Frontend<br/>(TS + Vite: dashboard, upload,<br/>predict, compare, map, history, metrics)"]
    end

    subgraph Server["FastAPI Backend"]
        API["API Routers<br/>/train /predict /evaluate /models<br/>/history /upload /metrics /version /docs"]
        SVC["Services<br/>(use-cases: train / predict /<br/>evaluate / change-detect)"]
        MS["Model Service<br/>(U-Net, Attention U-Net,<br/>DeepLabV3+, [SegFormer opt])"]
        PP["Preprocessing Pipeline<br/>(bands, normalize, NDSI + cirrus<br/>indices, tiling, augmentation)"]
        OUT["Output Generation<br/>(masks, overlays, stratified<br/>reports, change-detection maps)"]
    end

    subgraph Data["Dataset Layer"]
        C12["CloudSEN12<br/>(primary, 13-band, multi-class)"]
        OCN["On Cloud N<br/>(reference benchmark, binary)"]
    end

    subgraph CrossCutting["Cross-Cutting"]
        CFG["Configuration<br/>(Pydantic, seeds, no hardcoded paths)"]
        LOG["Logging<br/>(structured, telemetry)"]
        EXP["Experiment Tracking<br/>(MLflow: params/metrics/artifacts)"]
        STORE["Model Storage<br/>(checkpoints + SQLite:<br/>versions, metrics, predictions, history)"]
    end

    FE <-->|REST / JSON| API
    API --> SVC
    SVC --> MS
    SVC --> PP
    SVC --> OUT
    PP --> C12
    PP --> OCN
    MS --> STORE
    MS --> EXP
    OUT --> STORE
    OUT -->|rendered results| FE

    CFG -.-> API
    CFG -.-> SVC
    CFG -.-> MS
    CFG -.-> PP
    LOG -.-> API
    LOG -.-> SVC
    LOG -.-> MS
    EXP -.-> MS
```

## 2. Planned Repository Layout (built in Milestone 2, not now)

```
Cloud_Masking/
├── backend/
│   ├── api/                # FastAPI routers: train, predict, evaluate, models, history, upload, metrics, version
│   ├── core/               # config (Pydantic), constants, logging setup, contracts/interfaces, exceptions
│   ├── services/           # use-case orchestration (training_service, prediction_service, ...)
│   ├── datasets/           # CloudSEN12 loader, dataset registry, manifest, splits
│   ├── preprocessing/      # band handling, normalization, spectral indices (NDSI, cirrus), augmentation
│   ├── models/             # unet, attention_unet, deeplabv3plus, (segformer optional), registry
│   ├── training/           # trainer, losses (Dice, CE), schedulers, MLflow integration
│   ├── evaluation/         # metrics (TorchMetrics), stratified evaluator, oracle, guardrails
│   ├── change_detection/   # change-detection task + masking-impact measurement
│   ├── db/                 # SQLite models + migrations (model versions, metrics, predictions, history)
│   ├── utils/              # geo utils (CRS/registration), io, seeding, reproducibility
│   └── tests/              # unit / integration / api / model tests (pytest)
├── frontend/
│   └── src/{components,pages,hooks,api,assets}/
├── docker/                 # Dockerfiles + docker-compose.yml
├── docs/                   # planning, architecture, dataset guide, install, user & dev guides, deployment
├── paper/                  # literature review, references, comparison tables, ablation template
├── presentation/           # poster + slides
├── reports/                # generated evaluation & validation reports (evidence)
├── scripts/                # download, validate, preprocess, split, stats, train, evaluate, predict, run_reference
├── .github/workflows/      # CI YAML (created, never auto-run)
├── configs/                # version-pinned experiment configs + seeds
├── pyproject.toml / requirements.txt
└── README.md
```

## 3. Data & Evidence Flow (implements Architecture A + B)

1. **Ingest** CloudSEN12 → validate provenance, CRS, bands, units, no-data (FR-1, NFR-3).
2. **Preprocess** → band selection, per-band normalization, spectral indices (NDSI for snow, cirrus B10 for
   thin cloud), patch tiling, augmentation (Albumentations).
3. **Spatial-block split** → train/val/test with **no spatial leakage** (NFR-4); reserve AC-3 acceptance set
   **before** any O3 tuning.
4. **Train** models (MLflow-tracked) with fixed seeds under the frozen resource envelope (AC-4).
5. **Evaluate** → overall + **stratified** (thin cloud / haze / snow / bright surface) + cross-region /
   cross-season; guardrails prevent aggregate hiding subgroup failure.
6. **Change detection** → feed masks into a bi-temporal change task; measure how masking errors change the
   detected-change score (O4).
7. **Serve** → FastAPI endpoints; React app for upload/predict/compare/map/history/metrics.
8. **Assure** → acceptance harness runs AC-1..4 + NT-1..5; independent review (O5).

## 4. Key Architecture Decision Records (see `docs/adr/`)

- **ADR-0001** — Dataset selection: **CloudSEN12** primary + **On Cloud N** reference benchmark (both retained). *(ACCEPTED)*
- **ADR-0002** — Compute environment: **Mac MPS/CPU** with config-driven device auto-detection + smoke profile. *(ACCEPTED)*
- **ADR-0003** — Change-detection evaluation source (candidate OSCD). *(DEFERRED to M12)*
- **ADR-0004** — Python runtime: pin **Python 3.11.x** (host 3.14 wheel-availability risk R-01). *(ACCEPTED)*

## 5. Cross-Cutting Concerns

- **Runtime:** **Python 3.11.x** (pinned; see ADR-0004), PyTorch stable with Apple-Silicon (MPS) support.
- **Config:** Pydantic-validated, no hardcoded paths (env/CLI/config file); seeds recorded.
- **Logging:** structured logging in every module; request/telemetry logging in API.
- **Errors:** typed exceptions in `core/exceptions.py`; no bare excepts.
- **Reproducibility:** deterministic seeding, pinned versions, scripted runbook.
- **Testing:** pytest with unit/integration/api/model layers; fixtures for negative tests.
