#!/usr/bin/env python3
"""Serve the Cloud Masking backend API with uvicorn (Milestone 13).

Thin launcher — all app wiring lives in ``app.main.create_app``. Swagger is served at ``/docs`` and the
OpenAPI schema at ``/openapi.json``.

Usage (project venv):
    backend/.venv/bin/python backend/scripts/serve_api.py --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Serve the Cloud Masking backend API.")
    parser.add_argument("--host", default=settings.api_host)
    parser.add_argument("--port", type=int, default=settings.api_port)
    parser.add_argument("--log-level", default=settings.log_level)
    args = parser.parse_args(argv)

    setup_logging(args.log_level.upper())      # project logging expects an uppercase Python level
    import uvicorn

    from app.main import create_app
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level=args.log_level.lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
