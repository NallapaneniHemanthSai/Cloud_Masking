#!/usr/bin/env python3
"""Verify dataset provenance, presence, and integrity — Milestone 3 (revised).

Thin CLI over :mod:`app.datasets.verification`. It:
  1. validates the manifest (required provenance fields),
  2. builds a structured report per dataset (manifest / directory / download / checksum / completeness /
     overall),
  3. prints a readable summary table.

It does **not** fail merely because datasets have not been downloaded yet (those are ``PENDING``). It
fails only on genuine problems (missing expected files, checksum mismatch) or, with ``--require-present``,
when a dataset is still not present. No preprocessing verification.

Usage:
    python backend/scripts/verify_datasets.py
    python backend/scripts/verify_datasets.py --require-present
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# --- Path bootstrap: make the backend package importable when run as a script from any cwd. --------
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.exceptions import CloudMaskingError  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.datasets.manifest import default_manifest_path, load_manifest  # noqa: E402
from app.datasets.verification import render_table, verify_all  # noqa: E402

logger = logging.getLogger("verify_datasets")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Verify dataset provenance, presence, and integrity.")
    parser.add_argument("--manifest", type=Path,
                        default=default_manifest_path(settings.data_manifests_dir),
                        help="Path to datasets.yaml provenance manifest.")
    parser.add_argument("--data-root", type=Path, default=settings.data_dir,
                        help=f"Data root directory (default: {settings.data_dir}).")
    parser.add_argument("--require-present", action="store_true",
                        help="Treat a not-yet-downloaded dataset as a failure.")
    parser.add_argument("--log-level", default=settings.log_level, help="Logging level (default: INFO).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)

    try:
        records = load_manifest(args.manifest)  # manifest consistency + required fields
    except CloudMaskingError as exc:
        logger.error("Manifest validation failed: %s", exc)
        return 1

    logger.info("Manifest OK: %d dataset(s) with all required provenance fields.", len(records))
    report = verify_all(records, args.data_root, require_present=args.require_present)

    # Structured, readable summary table (printed to stdout).
    print()
    print(render_table(report))
    print()

    if report.passed:
        logger.info("Dataset verification result: PASS")
        return 0
    logger.error("Dataset verification result: FAIL — see table/details above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
