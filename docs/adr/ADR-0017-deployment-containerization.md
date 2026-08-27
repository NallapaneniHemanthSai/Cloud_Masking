# ADR-0017 — Deployment & Containerization (Docker + Compose)

- **Status:** Accepted
- **Milestone:** M17 (Docker)
- **Date:** 2026-08-27
- **Deciders:** Project engineering (sole author on record: repository owner)
- **Supersedes:** the Milestone‑2 placeholder images in `docker/` (`backend.Dockerfile`,
  `frontend.Dockerfile`, `docker-compose.yml`).
- **Related:** ADR‑0004 (Python 3.11 for the geo/ML stack), ADR‑0013 (backend API), ADR‑0014
  (frontend + same‑origin `/api` proxy), ADR‑0015 (degraded/recovery), ADR‑0016 (acceptance harness);
  Risk **R‑12** (GDAL/rasterio system deps differ in Docker → clean‑env build test).

## Context

M1–M16 produced a runnable backend API (`app.main.create_app`, FastAPI) and a built React/TS/Vite
frontend, both exercised so far only against the host `backend/.venv` and the Vite dev server. The
milestone plan defines **M17 = Docker**: *"Dockerfiles + compose; GDAL/geo deps pinned; clean‑env
rebuild test,"* with the single acceptance rule **"`docker compose up` runs the system."** Risk R‑12
explicitly calls for pinning the GDAL/rasterio stack and proving a clean‑environment build so we do not
ship a "works on my machine" image.

Constraints carried in from earlier milestones and the standing project rules:

- **No new capabilities.** M17 packages what exists; it must not alter model architecture, training,
  evaluation metrics, failure‑analysis semantics, the NT‑1..NT‑5 guardrails, or the M11 **MIXED**
  conclusion, and must not fabricate KPI results or download CloudSEN12+.
- **Preserve the API and frontend contracts.** Backend routes are served at the root (no prefix); the
  frontend calls a same‑origin `/api` base and the dev server strips the `/api` prefix before
  forwarding to the backend (ADR‑0014). Production must mirror that rewrite exactly.
- **Configuration stays environment‑driven** (`app.core.config.Settings`, all `*_DIR`, `DATABASE_URL`,
  `API_HOST/PORT`, `LOG_LEVEL`) and **no secrets** may be baked into images or committed config.
- **Keep it as small as the requirement allows** — no Kubernetes, no cloud infra, no auth, no
  Redis/Postgres. The persistence design is the existing single‑file **SQLite** DB.

## Decision

Author two production images and a Compose stack, replacing the M2 placeholders.

### 1. Backend image — full API runtime with a **pinned GDAL/geo + CPU‑torch layer**
- Base **`python:3.11-slim`** (honours ADR‑0004). **Every** dependency is pinned in a dedicated
  **`docker/requirements-backend.txt`**, whose contents were derived by **auditing every `import` under
  `backend/app`** (not guessed) — so the container runs *every* API flow: `/health`, `/version`,
  `/metrics`, `/models`, `/train`, `/predict`, `/evaluate`, `/history`, `/upload`, `/status` +
  degraded/recovery, `/lineage`, `/pipeline`, `/acceptance`, `/docs`.
- **GDAL/geo (R‑12):** the set **includes `rasterio==1.4.4`**, whose manylinux wheel bundles GDAL, so
  the geo stack is version‑pinned and its clean build is verified without a heavier base or system GDAL.
- **Deep learning:** the set **includes CPU `torch==2.13.0`** (reached only through the guarded accessor
  `app/models/_torch.py`), so `/train` and `/predict` **function in‑container**. **MPS acceleration is
  host‑only** (ADR‑0002), so container inference/training is CPU‑speed and intended for *functional*,
  not benchmark, use.
- **Deliberately excluded** — audited to have **zero import sites** under `app/`, so excluding them
  removes no capability: `torchvision`, `torchmetrics`, `mlflow`, `opencv`, `scikit‑learn`,
  `scikit‑image`, `Pillow`, `pandas`, `scipy`; the guarded‑optional `matplotlib` (degrades to
  `NullBackend`) and `albumentations` (guarded by `_require_albumentations()`). `tacoreader` is
  excluded **by policy**: a deployment image must not be able to pull datasets — real‑data acquisition
  stays a host/operator action (ADR‑0012). This keeps the image to what is actually imported rather than
  a fabricated or bloated stack.
- Runs as a **non‑root** user (`appuser`, uid 10001); exposes `8000`; ships a dependency‑free
  **`HEALTHCHECK`** (stdlib `urllib` GET `/health`, port from `$API_PORT`) so Compose gates ordering on
  real readiness.
- Entry point is the project's blessed launcher **`scripts/serve_api.py`** (host/port from
  `API_HOST`/`API_PORT`; wires logging + `create_app()`), i.e. **no new server code** and fully
  environment‑driven.

### 2. Frontend image — multi‑stage build → static nginx with an `/api` reverse proxy
- **Stage 1** `node:20-alpine`: `npm ci` (lockfile present) then `npm run build` (`tsc --noEmit` +
  `vite build`) → static `dist/`.
- The SPA's API base is baked at build time via `ARG VITE_API_BASE_URL=/api` (same‑origin; never a
  secret).
- **Stage 2** `nginx:1.27-alpine`: serve `dist/` with SPA fallback (`try_files … /index.html`). The
  site config is a **template** (`docker/nginx.conf.template`) rendered at container start by nginx's
  envsubst entrypoint — only `${BACKEND_HOST}:${BACKEND_PORT}` are substituted
  (`NGINX_ENVSUBST_FILTER=^BACKEND_`), so the upstream is env‑configurable and nginx's own `$vars` are
  left intact. The `location ^~ /api/` block **strips the `/api` prefix** (`rewrite ^/api/(.*)$ /$1`),
  exactly reproducing the Vite dev‑proxy rewrite so the SPA's `/api` contract holds in production
  **without any backend CORS change** (ADR‑0014). It uses the **Docker embedded DNS resolver**
  (`127.0.0.11`) with a variable `proxy_pass`, so the upstream is **re‑resolved at runtime** and the
  proxy survives a `docker compose restart backend` (new container IP). A self‑served `location =
  /healthz` backs a busybox `wget` healthcheck that reports *frontend* liveness independently of the
  backend.

### 3. Compose stack — private network, health‑gated ordering, persistent volume
- `backend` and `frontend` services on a **named bridge network `cloud-masking`**; the frontend reaches
  the backend by the service DNS name **`backend`**. `frontend` `depends_on: backend (condition:
  service_healthy)`.
- **Persistence:** a **named volume `cloud-masking-data` mounted at `/data`**, with
  `DATABASE_URL=sqlite:////data/cloud_masking.db` and `OUTPUTS_DIR=/data`. The existing DB layer creates
  the parent dir and schema idempotently on startup, so application state survives container
  replacement — matching the existing SQLite/storage design (no new datastore).
- **Configuration is env‑driven with safe defaults and no secrets:** host ports (`BACKEND_PORT`,
  `FRONTEND_PORT`), `LOG_LEVEL`, `APP_ENV`, `RUN_PROFILE` are read from the environment/`.env` with
  sensible fallbacks; `API_HOST=0.0.0.0` is set so the container binds all interfaces.
  `restart: unless-stopped` provides basic recovery.

### 3a. R‑12 confirmed in practice — and caught by the build, not by a user
`rasterio`'s manylinux wheel bundles GDAL/PROJ/GEOS, but GDAL still **dynamically links base system
libraries that `python:3.11-slim` does not ship**. The first clean build of this image failed with:

```
ImportError: libexpat.so.1: cannot open shared object file: No such file or directory
```

This is precisely the "works on my machine" divergence R‑12 predicts, and it is **invisible on the
host** (macOS + Homebrew Python supply the library). Two decisions follow:

1. The image installs `libexpat1` via `apt-get` in its own layer (cleaning `/var/lib/apt/lists`), so
   the pinned wheel actually loads. Pinning the Python package was **necessary but not sufficient**;
   the R‑12 mitigation is *pinned wheel + explicit system library*.
2. The dependency layer **asserts its own imports at build time**
   (`python -c "import torch, rasterio, fastapi, sqlalchemy"`) and asserts that **no CUDA payload** was
   pulled. A missing system library therefore fails `docker build` loudly instead of surfacing as a
   runtime 500 on the first `/predict`. Build‑time assertions are cheap; this one earned its place on
   the very first build.

### 4. Clean‑env rebuild (R‑12)
- A repository‑root **`.dockerignore`** excludes `.venv/`, `node_modules/`, `dist/`, `outputs/`,
  `data/raw|external|processed/`, caches, and `*.db` so the build context is source‑only and the image
  is reproducible from a clean checkout via `docker compose build --no-cache`.

## Alternatives considered

- **"Batteries‑included" image (install the whole dev/ML stack: torchvision/torchmetrics/mlflow/opencv/
  sklearn/pandas/scipy…).** Rejected: those libraries have **zero import sites** under `app/`, so they
  add multi‑GB weight and long, network‑heavy builds for no capability. Instead the image installs the
  **audited exact import set** — which *does* include CPU `torch` (so `/train` & `/predict` work) and
  `rasterio` (R‑12) — and nothing that is never imported.
- **Omitting `torch` for a smaller image (ML endpoints return 503).** Considered, then rejected in
  favour of a complete, self‑demonstrating stack: bundling **CPU torch** lets `docker compose up` run
  *every* endpoint. The cost (a ~430 MB wheel) is accepted; MPS speed remains a host‑only concern.
- **Single combined image (nginx + uvicorn in one container).** Rejected: couples the SPA and API
  lifecycles, breaks the clean two‑image topology, and complicates health/scaling.
- **Baking a base "geo" image (e.g. `osgeo/gdal`).** Rejected: rasterio's manylinux wheels bundle GDAL,
  so pinning `rasterio` on `python:3.11-slim` gives a reproducible geo stack without a heavier base or
  system GDAL — a lighter R‑12 mitigation.
- **Kubernetes / Postgres / Redis / auth gateway.** Rejected: not required by M17 and explicitly out of
  scope ("keep the architecture as small as the repository's actual requirements allow").
- **Static nginx upstream (IP pinned at config load).** Rejected: it would go stale after a
  `docker compose restart backend` (new IP). **Adopted instead:** the template uses the Docker embedded
  resolver `127.0.0.11` + a variable `proxy_pass`, forcing **runtime re‑resolution** so the proxy
  survives a backend restart.

## Consequences

**Positive**
- `docker compose up` brings up the operable system (SPA + API + **all endpoints**, incl. `/train` &
  `/predict`, + health‑gated ordering + persistent SQLite) from a clean checkout; the R‑12 GDAL/geo
  build is pinned and verified.
- The `/api` contract, degraded/recovery, and the M16 acceptance harness all run unchanged; the
  acceptance CLI can be executed **inside** the running backend container.
- The `/api` proxy **survives a backend restart** (runtime DNS re‑resolution).
- Small attack surface: non‑root, no secrets, source‑only build context, and only the audited import
  set installed.

**Negative / limitations**
- Container `torch` is **CPU‑only** — **MPS acceleration is host‑only** (ADR‑0002), so in‑container
  `/train`/`/predict` are slow and intended for *functional*, not benchmark, use.
- The torch wheel makes the backend image large (~430 MB wheel); accepted for a self‑demonstrating
  stack.
- Persistence is single‑file SQLite on a local named volume — right‑sized for this project, not a
  multi‑node datastore.

## Honesty labels
- The deployed system serves **SYNTHETIC/DEMO** results only (as in M13–M16); **no REAL KPI** is
  produced or implied by containerization. All formal KPIs remain **NOT YET MEASURED**; the M11
  real‑data conclusion remains **MIXED**. Container inference runs on **CPU torch** (MPS host‑only).
