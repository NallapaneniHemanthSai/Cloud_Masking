# Installation Guide

Getting the Cloud Masking system running from a fresh `git clone`. Two supported paths:

| Path | Use it when | Time | Needs |
|------|-------------|------|-------|
| **[A — Docker](#path-a--docker-recommended)** | You want the system running with the fewest moving parts | ~10 min (first build) | Docker Desktop |
| **[B — Host / development](#path-b--host-development)** | You are going to change the code | ~15 min | Python 3.11.x, Node 20+ |

Both serve the identical API contract, so the frontend is unchanged between them (ADR-0014 / ADR-0017).

> **What you will *not* get by installing.** No dataset is downloaded and no model is trained. Every
> result the freshly-installed system produces is **SYNTHETIC / DEMO** and labelled as such in the UI
> and in API responses. Acquiring real CloudSEN12+ data is a separate, deliberate step — see
> [Getting real data](#getting-real-data-optional).

---

## Prerequisites

| Component | Requirement | Why |
|-----------|-------------|-----|
| **Python** | **3.11.x only** | Geo/ML wheels + stable PyTorch Apple-Silicon (MPS). Host 3.14 is intentionally not used — [ADR-0004](../adr/ADR-0004-python-runtime.md). |
| **Node** | **≥ 20** | Vite 6 / React 18 frontend. |
| **Docker** | any recent version | Path A only. |
| **Compute** | Apple Silicon (MPS) or CPU | No CUDA anywhere in this project — [ADR-0002](../adr/ADR-0002-compute-environment.md). |
| **Disk** | ~4 GB | Mostly the PyTorch wheel; more if you later fetch data. |

Check what you have:

```bash
python3.11 --version && node --version && docker --version
```

---

## Path A — Docker (recommended)

```bash
git clone <repository-url> Cloud_Masking
cd Cloud_Masking
docker compose -f docker/docker-compose.yml up -d --build
```

The first build takes several minutes (it downloads the CPU PyTorch wheel). When it finishes:

| What | URL |
|------|-----|
| Web UI | <http://localhost:8080> |
| API | <http://localhost:8000> |
| Swagger | <http://localhost:8000/docs> |

Confirm it actually works — this exits non-zero if anything is wrong:

```bash
docker compose -f docker/docker-compose.yml ps          # both services should read "healthy"
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8080/api/health              # same API, through the frontend proxy
```

Stop it (keeping your data) or wipe it completely:

```bash
docker compose -f docker/docker-compose.yml down        # keeps the cloud-masking-data volume
docker compose -f docker/docker-compose.yml down -v     # discards it
```

Ports, log level and profile are environment-driven — see the
[deployment guide](../deployment/README.md) for the full table.

---

## Path B — Host (development)

### 1. Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.in
```

`requirements.in` is the **authoritative** dependency source (soft constraints). The exactly-pinned set
the container uses lives in [`docker/requirements-backend.txt`](../../docker/requirements-backend.txt).

> **macOS TLS note.** Framework Python 3.11 has no system CA store, so any network call
> (`tacoreader`, `rasterio`) fails certificate verification until `SSL_CERT_FILE` / `CURL_CA_BUNDLE`
> point at `certifi.where()`. `app.datasets.cloudsen12_access.ensure_tls_ca()` does this for you; call
> it before network access in your own scripts.

Start the API:

```bash
backend/.venv/bin/python backend/scripts/serve_api.py     # http://127.0.0.1:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Vite proxies `/api/*` to `http://127.0.0.1:8000`, stripping the prefix — the same rewrite nginx performs
in Docker, which is why no CORS configuration exists anywhere in the backend.

### 3. Verify the install

```bash
backend/.venv/bin/python backend/scripts/run_acceptance.py       # NT-1..NT-5, exits non-zero on failure
backend/.venv/bin/python backend/tests/test_deployment.py        # deployment contract, no Docker needed
backend/.venv/bin/python backend/tests/test_documentation.py     # docs complete & consistent
```

`pytest` is **not** installed in this project's venv, so every test file is also runnable directly as a
standalone harness (for example `python backend/tests/test_acceptance.py`). See the
[developer guide](../developer_guide/README.md#running-the-tests).

---

## Configuration

Nothing is hard-coded; everything comes from the environment with safe defaults.

```bash
cp .env.example .env          # then edit — the file is git-ignored
```

| Variable | Default | Meaning |
|----------|---------|---------|
| `APP_ENV` | `development` | Environment tag |
| `RUN_PROFILE` | `smoke` | `smoke` (tiny) or `full` (the AC-4 frozen envelope) |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Bind address (Docker sets `0.0.0.0`) |
| `LOG_LEVEL` | `INFO` | Root log level |
| `DATABASE_URL` | `sqlite:///./outputs/cloud_masking.db` | SQLite location |
| `OUTPUTS_DIR` / `DATA_DIR` / `MODELS_DIR` | project-relative | Artifact roots |
| `RANDOM_SEED` | `42` | Global reproducibility seed |

**No secret belongs in any of these**, and none is required — the system has no credentials, no auth,
and no external service calls in normal operation.

---

## Getting real data (optional)

The repository ships **no** dataset, and the Docker image deliberately cannot download one
(`tacoreader` is not installed in it). On the host:

```bash
backend/.venv/bin/python backend/scripts/acquire_cloudsen12.py --help
backend/.venv/bin/python backend/scripts/validate_dataset.py --help
```

CloudSEN12+ is **CC0-1.0** (redistribution permitted). On Cloud N is **competition-licensed and must not
be redistributed** — it stays git-ignored and reference-only. Read
[`docs/datasets/licenses.md`](../datasets/licenses.md) before fetching anything.

Downloaded data lands in git-ignored paths and must pass the M12 readiness gate before it can drive an
experiment. See the [dataset guide](../datasets/README.md).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImportError: libexpat.so.1` in a container | `rasterio`'s wheel bundles GDAL but links system libs `python:3.11-slim` omits | Already fixed in `docker/backend.Dockerfile`; rebuild without cache |
| `ModuleNotFoundError: pytest` | Intentional — pytest is not installed | Run test files directly, e.g. `python backend/tests/test_acceptance.py` |
| `CERTIFICATE_VERIFY_FAILED` | macOS framework Python has no CA store | `ensure_tls_ca()`, or export `SSL_CERT_FILE=$(python -c "import certifi;print(certifi.where())")` |
| `/train` or `/predict` returns **503** | PyTorch missing in that environment | Install `requirements-dev.in`; the Docker image already has CPU torch |
| Vite dev server 404s on everything | Started from the wrong directory | Run `npm run dev` from `frontend/` |
| Port 8000/8080 already in use | Something else is bound | `BACKEND_PORT=18000 FRONTEND_PORT=18080 docker compose -f docker/docker-compose.yml up -d` |
| Frontend loads but every panel errors | Backend not reachable | Check `curl http://localhost:8000/health` and the browser console |

---

## Next steps

- [User guide](../user_guide/README.md) — driving the system.
- [Developer guide](../developer_guide/README.md) — changing it.
- [API reference](../api/README.md) — every endpoint and DTO.
- [Deployment guide](../deployment/README.md) — containers, volumes, health checks.
