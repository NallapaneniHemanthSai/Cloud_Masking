# Cloud Masking — Backend

FastAPI + PyTorch backend for the *Cloud Masking Across Thin Cloud, Haze, Snow and Bright Surfaces*
capstone. Exposes the M6–M16 capabilities as a service layer: dataset pipeline, U-Net / Attention U-Net,
training, evaluation, failure analysis, model comparison, degraded mode + recovery, and the D5
acceptance harness.

**Full documentation → [`../docs/`](../docs/README.md)** · install: [`../docs/install/`](../docs/install/README.md)
· API reference: [`../docs/api/`](../docs/api/README.md) · internals: [`../docs/developer_guide/`](../docs/developer_guide/README.md)

> **Honesty:** the API's default `/train`, `/predict` and `/evaluate` paths operate on bounded
> **SYNTHETIC** inputs and are never benchmarks. No formal KPI is served by any endpoint — all remain
> **NOT YET MEASURED** — and the bounded M11 real-data conclusion remains **MIXED**.

## Python version

**Python 3.11.x only** — see [`../docs/adr/ADR-0004-python-runtime.md`](../docs/adr/ADR-0004-python-runtime.md).
The host interpreter (3.14) is intentionally not used: the geospatial/ML wheel ecosystem (`rasterio`,
GDAL) and stable PyTorch Apple-Silicon (MPS) builds target 3.11.

## Layout

```
backend/
├── app/
│   ├── api/              FastAPI routers (M13) — thin adapters, no domain logic
│   ├── core/             config · constants · logging · exceptions (stdlib only)
│   ├── services/         use-cases (M13) · lineage + integration/degraded/recovery (M15)
│   ├── datasets/         manifest · integrity · CloudSEN12+ access · readiness gate (M3/M12)
│   ├── preprocessing/    bands · normalization · patching · splitting · augmentation (M4)
│   ├── visualization/    backend-independent figure specs · statistics · reports (M5)
│   ├── models/           U-Net (M6) · Attention U-Net (M10) · registry · factory
│   ├── training/         trainer · optimizer/scheduler/loss · callbacks · checkpoints (M7)
│   ├── evaluation/       confusion · per-class + stratified metrics (M8)
│   ├── failure_analysis/ taxonomy · pixel/sample errors · ranking (M9)
│   ├── comparison/       fairness guardrails · decision framework (M11)
│   ├── inference/        tiled prediction + stitching (M13)
│   ├── acceptance/       D5 harness — NT-1..NT-5 (M16)
│   ├── db/ · schemas/    SQLAlchemy models · Pydantic v2 DTOs (M13)
│   └── main.py           create_app() — import-clean, lazy heavy imports
├── tests/                pytest-compatible AND standalone-runnable
├── configs/              config.template.yaml · smoke.yaml · full.yaml · logging.yaml
└── scripts/              one CLI per capability
```

## Setup

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.in
```

`requirements.in` is the **authoritative** runtime source (soft constraints). The exactly-pinned set the
container uses is [`../docker/requirements-backend.txt`](../docker/requirements-backend.txt); a full
transitive `pip-compile` lock for the host venv is still deferred.

## Run

```bash
backend/.venv/bin/python backend/scripts/serve_api.py     # http://127.0.0.1:8000 · Swagger at /docs
```

Configuration is entirely environment-driven (`API_HOST`, `API_PORT`, `LOG_LEVEL`, `DATABASE_URL`,
`OUTPUTS_DIR`, `RANDOM_SEED`, …) with safe defaults — see `.env.example`. No secrets are required.

## Test

`pytest` is **not** installed here, so every test file also runs standalone:

```bash
backend/.venv/bin/python backend/tests/test_comparison.py            # M11 — 23
backend/.venv/bin/python backend/tests/test_datasets_experimental.py # M12 — 18
backend/.venv/bin/python backend/tests/test_api.py                   # M13 — 15
backend/.venv/bin/python backend/tests/test_integration.py           # M15 — 10
backend/.venv/bin/python backend/tests/test_acceptance.py            # M16 — 13
backend/.venv/bin/python backend/tests/test_deployment.py            # M17 — 34
backend/.venv/bin/python backend/tests/test_documentation.py         # M18
```

Whole-system gates:

```bash
backend/.venv/bin/python backend/scripts/run_acceptance.py        # NT-1..NT-5, non-zero on failure
backend/.venv/bin/python backend/scripts/verify_deployment.py     # probes a running stack
backend/.venv/bin/python backend/scripts/generate_api_docs.py --check
```

## Scripts

See [`scripts/README.md`](scripts/README.md). Data-acquisition scripts document and never bypass access
controls; **no dataset is downloaded automatically**, and the deployment image cannot download one.
