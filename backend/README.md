# Cloud Masking — Backend

FastAPI + PyTorch backend for the *Cloud Masking Across Thin Cloud, Haze, Snow and Bright Surfaces*
capstone. **Milestone 2 status: scaffold only** (no runtime logic; nothing installed).

## Python version

**Python 3.11.x only** — see [`../docs/adr/ADR-0004-python-runtime.md`](../docs/adr/ADR-0004-python-runtime.md).
The host interpreter (3.14) is intentionally not used because the geospatial/ML wheel ecosystem
(`rasterio`, `GDAL`, `albumentations`, `opencv`) and stable PyTorch Apple-Silicon (MPS) builds target 3.11.

## Layout

```
backend/
├── app/
│   ├── api/           # FastAPI routers (M13)         core/          # config, constants, logging, exceptions
│   ├── models/        # segmentation nets (M6/M10)    services/      # use-case orchestration
│   ├── preprocessing/ # bands, indices, tiling (M4)   inference/     # prediction pipeline (M13)
│   ├── training/      # trainer, losses (M6/M7)        evaluation/    # metrics, guardrails (M8/M9)
│   ├── datasets/      # loaders, manifest (M3/M4)      change_detection/  # O4 (M12)
│   ├── db/            # SQLite models (M13)            schemas/       # API DTOs (M13)
│   ├── utils/         # geo/io/repro helpers
│   └── main.py        # app factory placeholder (M13)
├── tests/             # structure + import tests (functional tests from M6)
├── configs/           # config.template.yaml, smoke.yaml, full.yaml, logging.yaml
├── scripts/           # download/validate/preprocess/train/evaluate/predict (M3+)
├── pyproject.toml     # metadata + pytest/ruff/black/mypy config
├── requirements.in    # AUTHORITATIVE runtime deps (soft constraints; NOT installed at M2)
└── requirements-dev.in
```

## Dependency workflow

`requirements.in` (+ `requirements-dev.in`) are the **hand-edited authoritative sources** with soft
constraints. A fully-pinned lock (`requirements.txt`) is **deliberately deferred** until package
selection stabilises in later milestones, then generated reproducibly:

```bash
pip-compile requirements.in -o requirements.txt
pip-compile requirements-dev.in -o requirements-dev.txt
```

## Setup (for later milestones — do NOT run at M2)

```bash
# From backend/ — create a Python 3.11 virtual environment (exact tool of your choice):
python3.11 -m venv .venv
source .venv/bin/activate
# Until a lock is generated, install directly from the authoritative source:
pip install -r requirements-dev.in
```

## Verify the scaffold (M2)

Structure/import tests are standard-library only and run without installing dependencies:

```bash
cd backend && python -m pytest -q
```

(If `pytest` is not present, the scaffold can be verified with the compile/import check documented in the
repository root `README.md`.)
