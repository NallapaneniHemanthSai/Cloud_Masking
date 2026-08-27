# Docker (Milestone 17)

Functional container images and Compose stack for the Cloud Masking system. These replace the
Milestone‑2 placeholders. Design rationale: **ADR‑0017**; full operator guide:
[`../docs/deployment/README.md`](../docs/deployment/README.md).

| File | Purpose |
|------|---------|
| `backend.Dockerfile` | API image — `python:3.11-slim`, **every dep pinned** (incl. CPU **torch** + rasterio/GDAL), non‑root, env‑driven stdlib `/health` healthcheck. |
| `frontend.Dockerfile` | SPA image — multi‑stage `node:20-alpine` build → `nginx:1.27-alpine` static serve + `/api` proxy; `VITE_API_BASE_URL=/api` baked at build. |
| `requirements-backend.txt` | **Fully pinned** runtime deps, derived by auditing every `import` under `app/` (GDAL/geo pinned — Risk R‑12; zero‑import heavy libs deliberately excluded). |
| `nginx.conf.template` | Rendered at container start (envsubst `${BACKEND_HOST}:${BACKEND_PORT}`); serves the SPA (history fallback), a self‑served `/healthz`, and proxies `/api/*` → backend (strips `/api`, re‑resolves the upstream via Docker DNS so it survives a backend restart). |
| `docker-compose.yml` | Two services on a named bridge network, health‑gated order, named volume for SQLite/app data. |

## Quick start (from the repository root)

```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
```

- **UI:** http://localhost:8080  ·  **API + Swagger:** http://localhost:8000/docs
- Override host ports with `BACKEND_PORT` / `FRONTEND_PORT` (see `../.env.example`).

Clean‑environment rebuild (Risk R‑12):

```bash
docker compose -f docker/docker-compose.yml build --no-cache
```

Tear down (keep data) / (drop the data volume):

```bash
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml down -v
```

## Verify

```bash
# static contract checks — no Docker daemon needed
backend/.venv/bin/python backend/tests/test_deployment.py

# black-box probe of a RUNNING stack (non-zero exit on any failure)
backend/.venv/bin/python backend/scripts/verify_deployment.py \
    --api-url http://localhost:8000 --frontend-url http://localhost:8080
```

## Notes / honest limitations

- **Risk R-12 is real here, not theoretical.** `rasterio`'s wheel bundles GDAL but still links base
  system libraries: on `python:3.11-slim`, `import rasterio` fails with
  `libexpat.so.1: cannot open shared object file` until `libexpat1` is installed. The backend image
  installs it *and* asserts `import torch, rasterio, fastapi, sqlalchemy` **during the build**, so a
  missing system library fails the build instead of surfacing as a runtime 500.

- The backend image bundles **CPU PyTorch**, so **every** API flow runs in‑container — including
  `/train` and `/predict` — alongside health, version, models, evaluate, history, upload, status +
  degraded/recovery, lineage, pipeline, and acceptance. Deliberately **excluded** (audited: zero import
  sites under `app/`, so no capability is lost): torchvision, torchmetrics, mlflow, opencv, scikit‑learn/
  image, pandas, scipy; `tacoreader` is excluded **by policy** (a deployment image must not pull datasets).
- **MPS acceleration is host‑only** — container torch is CPU, so in‑container inference/training is
  slower and intended for functional (not benchmark) use.
- Deployed results are **SYNTHETIC/DEMO** only; no REAL KPI is produced. Formal KPIs remain **NOT YET
  MEASURED**; the M11 real‑data conclusion remains **MIXED**.
- **No secrets** are baked into images or committed config; all configuration is environment‑driven.
