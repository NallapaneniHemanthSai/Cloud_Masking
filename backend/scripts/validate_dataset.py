#!/usr/bin/env python3
"""Dataset validation CLI (Milestone 12) — thin wrapper over ``app.datasets``.

Inspects the **local filesystem** (never the network), reports availability
(``PRESENT`` / ``PARTIAL`` / ``NOT_PRESENT``) and a structured validation status
(``READY`` / ``READY_WITH_WARNINGS`` / ``INCOMPLETE`` / ``INVALID`` / ``NOT_PRESENT``). With
``--synthetic-smoke`` it validates a labelled synthetic fixture (PIPELINE VALIDATION ONLY). **No hidden
downloads.** No validation logic lives here.

Usage:
    python backend/scripts/validate_dataset.py --dataset cloudsen12
    python backend/scripts/validate_dataset.py --dataset cloudsen12 --synthetic-smoke
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.exceptions import CloudMaskingError  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.datasets.availability import check_availability  # noqa: E402
from app.datasets.experimental_config import ExperimentalDatasetConfig  # noqa: E402
from app.datasets.manifest import default_manifest_path, load_manifest  # noqa: E402
from app.datasets.pipeline import prepare_experimental_dataset  # noqa: E402

logger = logging.getLogger("validate_dataset")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    p = argparse.ArgumentParser(description="Validate an experimental dataset (availability + integrity).")
    p.add_argument("--dataset", default="cloudsen12")
    p.add_argument("--manifest", type=Path, default=default_manifest_path(settings.data_manifests_dir))
    p.add_argument("--data-root", type=Path, default=settings.data_dir)
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--subset", type=int, default=24)
    p.add_argument("--synthetic-smoke", action="store_true",
                   help="Validate a SYNTHETIC / PIPELINE-VALIDATION-ONLY fixture (never a benchmark).")
    p.add_argument("--require-ready", action="store_true",
                   help="Exit non-zero unless the dataset validates as READY.")
    p.add_argument("--log-level", default=settings.log_level)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)

    try:
        records = load_manifest(args.manifest)
        availability = check_availability(records, args.data_root,
                                          metadata_dir=get_settings().data_metadata_dir,
                                          manifest_path=args.manifest)
        print()
        print(availability.render_table())
        print()

        config = ExperimentalDatasetConfig(dataset_id=args.dataset, subset_size=args.subset, seed=args.seed)
        prepared = prepare_experimental_dataset(
            config, synthetic=args.synthetic_smoke, output_dir=args.output, data_root=args.data_root)
        v = prepared.validation
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    print(f"Dataset '{args.dataset}' [{prepared.data_regime}] validation: {v.overall_status}")
    print(f"  file={v.file_status} checksum={v.checksum_status} metadata={v.metadata_status} "
          f"label={v.label_status} dimension={v.dimension_status} completeness={v.completeness_status}")
    for f in v.failures:
        print(f"  FAIL: {f}")
    for w in v.warnings:
        print(f"  WARN: {w}")
    print()

    if args.require_ready and not v.is_ready:
        logger.error("Dataset is not READY (status=%s).", v.overall_status)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
