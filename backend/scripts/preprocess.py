#!/usr/bin/env python3
"""Plan/inspect preprocessing for a dataset (Milestone 4).

Thin CLI: builds a :class:`PreprocessingConfig`, discovers + validates a dataset, and prints a dry
preprocessing plan (no heavy IO, no model code). Actual array processing is exercised by the pipeline's
``process_array`` (covered by unit tests); this script does not download or write data.

Usage:
    python backend/scripts/preprocess.py --dataset on_cloud_n
    python backend/scripts/preprocess.py --dataset cloudsen12 --patch-size 256 --overlap 32
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
from app.core.constants import DATASET_DIRNAMES, Dataset  # noqa: E402
from app.core.exceptions import CloudMaskingError  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.preprocessing.config import PreprocessingConfig  # noqa: E402
from app.preprocessing.loader import get_layout  # noqa: E402
from app.preprocessing.pipeline import PreprocessingPipeline  # noqa: E402

logger = logging.getLogger("preprocess")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Plan preprocessing for a dataset.")
    parser.add_argument("--dataset", choices=[d.value for d in Dataset], required=True)
    parser.add_argument("--root", type=Path, default=None,
                        help="Dataset root (default: <DATA_RAW_DIR>/<dataset>).")
    parser.add_argument("--patch-size", type=int, default=None)
    parser.add_argument("--overlap", type=int, default=None)
    parser.add_argument("--normalization", default=None, help="none|minmax|zscore|percentile")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--image-size", type=int, nargs=2, metavar=("H", "W"), default=None,
                        help="Optional nominal image size to estimate patches/sample.")
    parser.add_argument("--log-level", default=settings.log_level)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)
    settings = get_settings()

    root = args.root or (settings.data_raw_dir / DATASET_DIRNAMES[Dataset(args.dataset)])

    # Build config from defaults + any provided overrides (no hardcoded constants).
    overrides = {k: v for k, v in {
        "patch_size": args.patch_size,
        "overlap": args.overlap,
        "normalization_mode": args.normalization,
        "random_seed": args.seed,
    }.items() if v is not None}

    try:
        config = PreprocessingConfig.from_dict(overrides)
        layout = get_layout(args.dataset)
        pipeline = PreprocessingPipeline(config, layout)
        plan = pipeline.plan(root, sample_image_size=tuple(args.image_size) if args.image_size else None)
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    print()
    print(plan.render())
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
