# ADR-0013 — Backend API (FastAPI + SQLite + Telemetry)

- **Status:** ACCEPTED (2026-08-20)
- **Milestone:** M13 (Backend API)
- **Related:** ADR-0002 (compute/MPS), ADR-0004 (Python 3.11), ADR-0006/0010 (models), ADR-0007
  (training), ADR-0008 (evaluation), ADR-0009 (failure analysis), ADR-0011 (comparison), ADR-0012
  (experimental dataset); Objective O4 (integrated operable system); milestone plan §M13.

## Objective

Deliver the **backend API layer** the milestone plan defines for M13: a FastAPI application exposing
`/train /predict /evaluate /models /history /upload /metrics /version` (plus FastAPI's built-in `/docs`
Swagger and a `/health`), backed by **SQLite** persistence and **logging/telemetry**. Acceptance: the
endpoints pass API tests and Swagger is live. The API is a thin **adapter over `app.services`**, which
orchestrate the existing M3–M12 domain components — **no domain logic lives in the API or duplicates
M3–M12**.

## Scope

- FastAPI app factory (`app.main.create_app`) with routers, request-timing **telemetry middleware**,
  structured logging bootstrap, and a lifespan that initialises the DB.
- **Pydantic v2 DTOs** (`app.schemas`) for every request/response.
- **SQLAlchemy 2.0 ORM** (`app.db`) over SQLite: model versions, training runs, predictions, evaluations,
  metric records, uploads. Schema written to allow a later Postgres swap (no domain-code change).
- **Services** (`app.services`) coordinating: version info, model registry listing, bounded training
  (reusing the M7 `Trainer`), inference (`app.inference` predictor reusing M6 models + M4 preprocessing +
  M7 checkpoints), evaluation (reusing M8), history queries, uploads, and in-process metrics.
- A thin `scripts/serve_api.py` uvicorn launcher.
- Framework-free tests (services + route handlers + a temp-SQLite DB), since `httpx` (needed by
  `TestClient`) is intentionally **not** installed.

## Non-scope (explicitly deferred)

- Frontend (M14), full integration/degraded-mode/recovery (M15), acceptance harness (M16), Docker (M17).
- Authentication/authorization, multi-user, async job queues/workers, WebSockets, rate limiting.
- Long-running / full-dataset training or the frozen **AC-4** benchmark via the API (compute-unsafe here).
- Change detection (later milestone). MLflow/Postgres wiring (SQLite only for dev).
- No new model architecture is introduced (M13 is API only).

## Relationship to M11/M12

- `/models` lists architectures from the M6 `ModelRegistry` and any DB-recorded model versions.
- `/train` reuses the **M7** `Trainer` (no second training engine); `/evaluate` reuses **M8**; `/predict`
  reuses **M6** models + **M4** preprocessing + **M7** checkpoint loading. The **M11** comparison and the
  **M12** dataset-readiness pipeline are **unchanged**; the API may *read* their artifacts (e.g. a dataset
  artifact / comparison report) but does not modify them.
- The bounded 32-sample real experiment and its **MIXED** M11 conclusion are **not** altered, re-run as a
  benchmark, or promoted; the cloud-shadow regression finding stands.

## Real-data assumptions

The API must run **without** any real dataset present (dev default). Real CloudSEN12 payloads stay
git-ignored and are never shipped through the API by default. `/predict` operates on an **uploaded** raster
or an in-memory array; `/train` and `/evaluate` default to **bounded synthetic** inputs (clearly labelled
`SYNTHETIC / VALIDATION ONLY`) unless a caller explicitly points them at a prepared local dataset. No
real-data metric is fabricated; anything not measured is `NOT MEASURED` / `NOT YET MEASURED`.

## Reproducibility requirements

- Every persisted training/prediction/evaluation row records the relevant **config hash**, **versions**
  (model/preprocessing/training/evaluation/comparison/dataset-manifest), **seed**, and **device**.
- DTOs and DB rows serialise deterministically; content/config hashes reuse `app.utils.hashing.stable_hash`.
- `/version` returns all component versions from `app.core.constants` (single source of truth).

## Compute budget & MPS constraints

- API request handling is lightweight; any training triggered via `/train` is **bounded** (small epochs /
  synthetic or tiny data) and never a full run. Device is auto-detected (`resolve_device`: cuda>mps>cpu);
  **CUDA stays false** on this host, MPS is used only when a caller requests training/inference and it is
  available, and the **actual device is recorded** — never assumed. Default endpoint behaviour requires no
  GPU and no torch (torch stays a guarded optional dependency; endpoints degrade to a clear error when a
  torch-only action is requested without torch).

## Artifact requirements

- A canonical, deterministically-hashed **run record** per training (`TrainingRun`) and per prediction
  (`Prediction`) persisted in SQLite, plus reuse of the existing typed artifacts (`TrainingArtifact`,
  `EvaluationRun`, `ModelArtifact`) where produced. Uploaded files are stored under a git-ignored
  `outputs/uploads/` with a content hash. The SQLite DB lives under `outputs/` (git-ignored).

## Failure / rollback conditions

- If torch is unavailable, torch-dependent endpoints (`/train`, `/predict` on a model) return a structured
  `503`/`422` with a clear message — they do not crash the app.
- DB writes are transactional (per-request session, rollback on error). A failed request never leaves a
  partial row. The app builds and serves even with an empty DB (lifespan creates tables idempotently).
- Rollback: the API is additive; disabling it is deleting the SQLite file and not serving. No M1–M12
  behaviour changes, so reverting M13 cannot break earlier milestones.

## Acceptance criteria

1. `create_app()` returns a FastAPI app exposing all required routes (`/train /predict /evaluate /models
   /history /upload /metrics /version /docs /health`).
2. Each endpoint has a Pydantic request/response schema and delegates to a service (no domain logic in the
   router).
3. SQLite persistence works: training/prediction/evaluation/upload rows are written and queryable via
   `/history` and `/models`.
4. Telemetry: a middleware records per-request latency/count exposed at `/metrics`; logging is structured.
5. Tests (framework-free, temp SQLite) pass; existing **M11 (23) and M12 (18)** regression tests still pass.
6. Swagger is live when served (`/docs`, `/openapi.json`).

All results produced via the API in verification are **SYNTHETIC / VALIDATION ONLY**; no real-data metric
is claimed, and the M11 MIXED conclusion is untouched.

## What remains deferred

Async training workers/queues, auth, Postgres, WebSockets, the frontend, real-data serving by default,
multi-seed aggregation in the comparison artifact (a known M11 reporting gap — tracked as remaining work,
**not** M13), and the AC-4 benchmark.
