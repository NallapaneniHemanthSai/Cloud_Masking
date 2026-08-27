# Repository Package Manifest (D6)

What this repository contains, what each part is for, and which milestone produced it. Together with the
[deployment guide](deployment/README.md) (M17) this closes **Deliverable D6** — *repo package, manifest,
install/operating guide, API docs, reproducibility*.

> **Scope of this document:** an inventory and a provenance record. It contains **no measurements**. For
> what has and has not been measured, see [Evidence status](#evidence-status) below.

---

## Package contents

| Area | Count | Contents |
|------|-------|----------|
| Backend Python modules | 152 | 18 packages under `backend/app/` |
| CLI scripts | 21 | `backend/scripts/` |
| Test / harness files | 20 | `backend/tests/` |
| Frontend sources | 27 | `frontend/src/` (TS/TSX) |
| Architecture decision records | 17 | `docs/adr/ADR-0001 … ADR-0018` |
| Documentation files | 48 | `docs/` |
| Container images | 2 | `cloud-masking-backend`, `cloud-masking-frontend` |

```
Cloud_Masking/
├── backend/            Python 3.11 · FastAPI + PyTorch
│   ├── app/            domain packages (see the developer guide for ownership)
│   ├── scripts/        one CLI per capability
│   ├── tests/          pytest-compatible AND standalone-runnable
│   └── configs/        config.template · smoke · full · logging
├── frontend/           React 18 + TypeScript 5 (strict) + Vite 6
├── docker/             Dockerfiles · compose · nginx template · pinned runtime deps
├── docs/               planning · adr · guides · per-milestone references
├── data/               manifests + metadata tracked; payloads git-ignored
├── models/             checkpoints (git-ignored)
├── outputs/            SQLite · uploads · mlruns · reports (git-ignored)
└── paper/ presentation/ reports/    M19 · M20 · evidence
```

---

## Provenance by milestone

| M | Delivered | ADR | Reference doc |
|---|-----------|-----|---------------|
| M1 | Charter, requirements, boundary, architecture, risks, KPIs, plan | 0001–0004 | [`planning/`](planning/) |
| M2 | Repo scaffold, config, logging, CI stubs | — | — |
| M3 | Dataset manifest, integrity, download scripts | 0001, 0012 | [`datasets/`](datasets/) |
| M4 | Preprocessing: bands, normalization, patching, spatial split | — | [`preprocessing/`](preprocessing/) |
| M5 | Visualization, statistics, QC reports | — | [`visualization/`](visualization/) |
| M6 | Baseline **U-Net**, registry, factory | 0006 | [`models/`](models/) |
| M7 | Training engine, callbacks, checkpoints, seeding | 0007 | [`training/`](training/) |
| M8 | Evaluation: confusion, per-class + stratified metrics | 0008 | [`evaluation/`](evaluation/) |
| M9 | Failure analysis; NT-1..NT-3 | 0009 | [`failure_analysis/`](failure_analysis/) |
| M10 | Improved **Attention U-Net** | 0010 | [`models/improved_model.md`](models/improved_model.md) |
| M11 | Controlled comparison + **the one real experiment** | 0011 | [`comparison/`](comparison/) |
| M12 | Experimental-dataset readiness pipeline | 0012 | [`datasets/experimental_pipeline.md`](datasets/experimental_pipeline.md) |
| M13 | Backend API + SQLite + telemetry | 0013 | [`api/`](api/) |
| M14 | React/TS frontend | 0014 | `frontend/README.md` |
| M15 | Integration, degraded mode, recovery, NT-5 | 0015 | [`integration/`](integration/) |
| M16 | **D5** acceptance harness (NT-1..NT-5) | 0016 | [`acceptance/`](acceptance/) |
| M17 | Docker images + Compose, clean-env build | 0017 | [`deployment/`](deployment/) |
| M18 | Documentation set + API reference + this manifest | 0018 | [`README.md`](README.md) |

*(ADR-0005 was never issued; numbering skips it.)*

---

## Third-party dependencies and licences

**Data.** CloudSEN12+ is **CC0-1.0** — redistribution permitted. On Cloud N is under **competition
terms — redistribution PROHIBITED**; it is reference-only and stays git-ignored. **No dataset payload
is committed to this repository or baked into any image.** Full detail:
[`datasets/licenses.md`](datasets/licenses.md).

**Software.** Runtime dependencies are exactly pinned in
[`docker/requirements-backend.txt`](../docker/requirements-backend.txt) (FastAPI, uvicorn, Pydantic,
SQLAlchemy, CPU PyTorch, NumPy, rasterio, PyYAML, requests, certifi) and
`frontend/package-lock.json` (React, React Router, axios, Leaflet, Vite, TypeScript). All are
permissively licensed (MIT / BSD / Apache-2.0). The project's own licence is **TBD — to be confirmed by
the repository owner** (`backend/pyproject.toml`); this is an open item, not an oversight.

---

## Reproducing the system

```bash
git clone <repository-url> Cloud_Masking && cd Cloud_Masking
docker compose -f docker/docker-compose.yml up -d --build
backend/.venv/bin/python backend/scripts/verify_deployment.py
```

Host path, configuration, and troubleshooting: [installation guide](install/README.md).
What is and is not reproducible: [developer guide](developer_guide/README.md#reproducibility-d6).

---

## Evidence status

The single table that says what this package does and does not prove.

| Class | Item | Status |
|-------|------|--------|
| **REAL** | Bounded CloudSEN12+ U-Net vs Attention U-Net comparison (32 expert-labelled L1C samples, 3 seeds, MPS) | **MEASURED** — thin-cloud IoU mean **+0.050** with a cloud-shadow regression → verdict **MIXED**. Bounded first experiment, **not** AC-4. |
| **SYNTHETIC** | All `/train`, `/predict`, `/evaluate` output; all acceptance fixtures; all pipeline-validation runs | Validation of code paths only. **Never** a performance claim. |
| **DEMO** | Degraded mode, recovery, lineage replay | Behaviour is real; the trigger is a fixture. |
| **DEFERRED** | Mask-pixel rendering, geo overlay, multi-arch images, transitive host lock, spatial (connected-component) NT-2/NT-3, `pytest-cov` line coverage | Deliberately not built. |
| **NOT BUILT** | FR-2 `scripts/run_reference.sh` + `app/evaluation/oracle.py` | Named in requirements, never implemented (M6–M9 scope). Recorded in [`planning/10_DOCUMENTATION_AUDIT.md`](planning/10_DOCUMENTATION_AUDIT.md). |
| **NOT YET MEASURED** | **KPI-1..KPI-6 and KPI-E1..KPI-E7**; AC-1, AC-3, AC-4 acceptance | Blocked on a real frozen-envelope AC-4 dataset. Never fabricated, never inferred from synthetic runs. |
| **PASS (synthetic)** | NT-1..NT-5 safety properties | Each proven with a pass fixture *and* a fail fixture (M16). |

**The project's own Pass Contract is therefore not yet satisfiable**, and the acceptance harness reports
exactly that: `SAFETY_PASS_KPI_NOT_YET_MEASURED`.

---

## Known open items

| Item | Owner | Needed by |
|------|-------|-----------|
| Project licence is **TBD** | Repository owner | Before public release |
| **A-01** KL deployment stakeholder unnamed | Repository owner | Blocking O4/O5 sign-off |
| **A-03** Independent O5 reviewer not secured | Repository owner | Before M19 |
| FR-2 reference path + oracle not built | M6–M9 scope | Before an O2 reproducibility claim |
| Real AC-4 dataset for KPI measurement | M19/M20 window | Before any KPI can leave NOT YET MEASURED |
