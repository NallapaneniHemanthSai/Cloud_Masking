"""Shared CLI helper for dataset download scripts (Milestone 3, revised).

Centralises argument parsing, manifest loading, and result printing so the per-dataset scripts
(``download_cloudsen12.py``, ``download_on_cloud_n.py``) contain no duplicated logic and no HTTP code —
they simply call :func:`run` with their dataset id. All HTTP/download logic lives in
``app.datasets.download``.
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
from app.core.constants import DATASET_DIRNAMES, Dataset  # noqa: E402
from app.core.exceptions import CloudMaskingError  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.datasets.download import STATUS_MANUAL_REQUIRED, download_dataset  # noqa: E402
from app.datasets.manifest import default_manifest_path, load_manifest  # noqa: E402


def _parse_args(dataset_key: str, default_out: Path, default_manifest: Path,
                default_log_level: str, argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"Download the '{dataset_key}' dataset (provenance-driven).")
    parser.add_argument("--output-dir", type=Path, default=default_out,
                        help=f"Destination directory (default: {default_out}).")
    parser.add_argument("--manifest", type=Path, default=default_manifest,
                        help="Path to datasets.yaml provenance manifest.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without fetching anything.")
    parser.add_argument("--no-resume", action="store_true", help="Disable resumable downloads.")
    parser.add_argument("--log-level", default=default_log_level, help="Logging level (default: INFO).")
    return parser.parse_args(argv)


def run(dataset_key: str, argv: list[str] | None = None) -> int:
    """Run the download CLI for one dataset. Returns a process exit code."""
    settings = get_settings()
    logger = logging.getLogger(f"download_{dataset_key}")
    default_out = settings.data_raw_dir / DATASET_DIRNAMES[Dataset(dataset_key)]
    args = _parse_args(dataset_key, default_out,
                       default_manifest_path(settings.data_manifests_dir),
                       settings.log_level, argv)
    setup_logging(args.log_level)

    try:
        records = load_manifest(args.manifest)
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    record = records.get(dataset_key)
    if record is None:
        logger.error("Dataset '%s' not found in manifest %s", dataset_key, args.manifest)
        return 1

    # Provenance echo (verified metadata).
    logger.info("%s [%s] — version: %s", record.name, record.role, record.version)
    logger.info("Licence: %s", record.license)
    logger.info("Redistribution: %s", record.redistribution)
    logger.info("Source: %s", record.source)
    logger.info("Output directory: %s", args.output_dir)

    result = download_dataset(record, args.output_dir, resume=not args.no_resume, dry_run=args.dry_run)

    if result.status == STATUS_MANUAL_REQUIRED:
        logger.warning("Manual access required — this script will NOT bypass access controls.")
        logger.warning("%s", result.message)
        for i, step in enumerate(result.manual_steps, start=1):
            logger.warning("  step %d: %s", i, step)
        return 0  # documented, not an error

    logger.info("Result: %s — %s", result.status, result.message)
    if not result.ok:
        return 1
    logger.info("Next: run backend/scripts/verify_datasets.py to validate integrity.")
    return 0
