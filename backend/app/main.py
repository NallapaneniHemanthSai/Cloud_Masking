"""Backend application entry point (Milestone 13 — Backend API).

Provides the FastAPI application factory. Kept **import-clean** at module top (standard library only) so
``import app.main`` succeeds on a bare interpreter and during the M2 import tests — FastAPI and all heavy
dependencies are imported lazily inside :func:`create_app`. The API is a thin adapter over ``app.services``;
no domain logic lives here (ADR-0013).
"""

from __future__ import annotations

from typing import Any


def create_app() -> Any:
    """Build and return the FastAPI application (routers + telemetry + logging + DB lifespan)."""
    import time
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    from app.api.routers import (
        evaluation,
        history,
        models,
        prediction,
        system,
        training,
        upload,
    )
    from app.core.config import get_settings
    from app.core.constants import API_VERSION
    from app.core.exceptions import CloudMaskingError, InferenceError, TrainingError
    from app.core.logging_config import setup_logging
    from app.core.telemetry import get_registry
    from app.db.base import default_database

    settings = get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: "FastAPI"):
        default_database()          # create the SQLite schema idempotently on startup
        yield

    app = FastAPI(
        title="Cloud Masking API",
        version=API_VERSION,
        description="Backend API for multispectral Sentinel-2 cloud segmentation (M13).",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def _telemetry(request: "Request", call_next):
        start = time.perf_counter()
        error = False
        try:
            response = await call_next(request)
            error = response.status_code >= 500
            return response
        except Exception:
            error = True
            raise
        finally:
            get_registry().record(request.url.path, time.perf_counter() - start, error=error)

    @app.exception_handler(CloudMaskingError)
    async def _handle_domain_error(_request: "Request", exc: CloudMaskingError):
        torch_missing = isinstance(exc, (TrainingError, InferenceError)) and "PyTorch" in str(exc)
        status = 503 if torch_missing else 422
        return JSONResponse(status_code=status,
                            content={"detail": str(exc), "error_type": type(exc).__name__})

    for module in (system, models, training, prediction, evaluation, history, upload):
        app.include_router(module.router)

    return app


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    from app.core.config import get_settings as _get_settings

    _settings = _get_settings()
    uvicorn.run(create_app(), host=_settings.api_host, port=_settings.api_port)
