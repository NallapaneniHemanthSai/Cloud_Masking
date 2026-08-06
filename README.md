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

**Current status:** Milestone 2 (Project Scaffold) complete and under review — scaffold only, no
application logic, no installed dependencies, no datasets. Milestone 3 not yet started.

```
✅ Milestone 1  – Planning
✅ Milestone 2  – Project Scaffold
⬜ Milestone 3  – Dataset Management
⬜ Milestone 4  – Data Preprocessing
⬜ Milestone 5  – Visualization
⬜ Milestone 6  – Baseline Model
⬜ Milestone 7  – Training
⬜ Milestone 8  – Evaluation
⬜ Milestone 9  – Confusing-Case Evaluation
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
