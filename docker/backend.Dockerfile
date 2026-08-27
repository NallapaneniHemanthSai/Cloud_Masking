# Backend image — Cloud Masking API (Milestone 17).
# Replaces the Milestone-2 placeholder. Python 3.11 per ADR-0004; every dependency pinned in
# docker/requirements-backend.txt (incl. rasterio, whose wheel bundles GDAL — Risk R-12). See ADR-0017.
#
# Build context is the repository root (see docker/docker-compose.yml `context: ..`).

FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="cloud-masking-backend" \
      org.opencontainers.image.description="Cloud Masking FastAPI backend (Sentinel-2 cloud segmentation)." \
      org.opencontainers.image.licenses="TBD" \
      org.opencontainers.image.source="https://github.com/"

# --- Runtime configuration (env-driven; no secrets) --------------------------------------------
# Every value below is an overridable default, not a hard-coded path. `app.core.constants.PROJECT_ROOT`
# resolves to /app because the source is copied to /app/backend/app/core/constants.py.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend \
    APP_ENV=production \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    LOG_LEVEL=INFO \
    DATA_DIR=/app/data \
    MODELS_DIR=/app/models \
    OUTPUTS_DIR=/data \
    DATABASE_URL=sqlite:////data/cloud_masking.db \
    MLFLOW_TRACKING_URI=file:/data/mlruns

# --- System libraries the wheels do NOT bundle (Risk R-12) ---------------------------------------
# rasterio's manylinux wheel bundles GDAL/PROJ/GEOS, but GDAL still dynamically links a handful of
# base system libraries. On python:3.11-slim that means `import rasterio` fails with
#   ImportError: libexpat.so.1: cannot open shared object file
# This is exactly the "works on my machine" failure R-12 predicts, and it is invisible until the
# image is actually built and imported — which is why the dependency layer below asserts the imports.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# --- PyTorch: CPU build, from PyTorch's CPU wheel index ------------------------------------------
# torch's default PyPI wheel drags the NVIDIA CUDA runtime in (nvidia-cudnn-cu13 alone is ~445 MB),
# which is dead weight here: containers on this project run CPU-only (MPS is host-only, ADR-0002).
# The CPU index serves torch-2.13.0+cpu for cp311/manylinux_aarch64 and x86_64, so `torch==2.13.0`
# below resolves to the +cpu local version and no nvidia-* package is pulled. Its own layer, because
# it is by far the slowest one to rebuild.
ARG TORCH_VERSION=2.13.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --index-url ${TORCH_INDEX_URL} "torch==${TORCH_VERSION}"

# --- Remaining dependencies (pinned) — torch is already satisfied, so it is not re-resolved -------
COPY docker/requirements-backend.txt /tmp/requirements-backend.txt
RUN pip install --no-cache-dir -r /tmp/requirements-backend.txt \
    && rm -f /tmp/requirements-backend.txt \
    && python -c "import torch, rasterio, fastapi, sqlalchemy; print('runtime imports OK', torch.__version__)" \
    && python -c "import importlib.util as u, sys; sys.exit(1) if u.find_spec('nvidia') else print('no CUDA payload')" 

# --- Non-root user + writable state dir ---------------------------------------------------------
# A fresh named volume mounted at /data inherits this ownership, so the non-root process can write
# the SQLite DB, uploads and mlruns without a host-side chown.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data /app/data /app/models \
    && chown -R appuser:appuser /data /app

WORKDIR /app

# --- Application source (context-root relative; .dockerignore keeps this lean) ------------------
COPY --chown=appuser:appuser backend/ /app/backend/

USER appuser
WORKDIR /app/backend

EXPOSE 8000

# Dependency-free health probe (no curl/apt needed): stdlib GET /health on the configured port.
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=20s \
    CMD ["python", "-c", "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('API_PORT','8000')+'/health', timeout=3).status==200 else 1)"]

# The project's blessed launcher (wires logging + create_app); host/port come from API_HOST/API_PORT,
# so the entrypoint stays environment-driven and no new server code is introduced (ADR-0017).
CMD ["python", "scripts/serve_api.py"]
