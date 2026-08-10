#!/usr/bin/env python3
"""Produce a reproducible train/val/test split manifest (Milestone 4).

Thin CLI: discovers a dataset's samples and writes a deterministic split manifest (YAML). No preprocessing
of pixels; no model code. If the dataset is not downloaded, it reports that gracefully and writes nothing.

Usage:
    python backend/scripts/split_dataset.py --dataset on_cloud_n --seed 42
    python backend/scripts/split_dataset.py --dataset cloudsen12 --train 0.7 --val 0.15 --test 0.15
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
from app.core.constants import DATASET_DIRNAMES, DEFAULT_RANDOM_SEED, Dataset  # noqa: E402
from app.core.exceptions import CloudMaskingError  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.preprocessing.config import SplitRatios  # noqa: E402
from app.preprocessing.loader import discover_samples, get_layout  # noqa: E402
from app.preprocessing.splitting import split_samples  # noqa: E402

logger = logging.getLogger("split_dataset")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Create a reproducible split manifest for a dataset.")
    parser.add_argument("--dataset", choices=[d.value for d in Dataset], required=True)
    parser.add_argument("--root", type=Path, default=None,
                        help="Dataset root (default: <DATA_RAW_DIR>/<dataset>).")
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--train", type=float, default=None)
    parser.add_argument("--val", type=float, default=None)
    parser.add_argument("--test", type=float, default=None)
    parser.add_argument("--output", type=Path, default=None,
                        help="Manifest output path (default: <DATA_MANIFESTS_DIR>/<dataset>_splits.yaml).")
    parser.add_argument("--log-level", default=settings.log_level)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)
    settings = get_settings()

    root = args.root or (settings.data_raw_dir / DATASET_DIRNAMES[Dataset(args.dataset)])
    output = args.output or (settings.data_manifests_dir / f"{args.dataset}_splits.yaml")

    ratios = SplitRatios() if args.train is None else SplitRatios(
        train=args.train, val=args.val, test=args.test)

    try:
        layout = get_layout(args.dataset)
        discovery = discover_samples(root, layout)
        if not discovery.samples:
            logger.warning("No samples found for '%s' under %s. %s",
                           args.dataset, root, "; ".join(discovery.messages))
            logger.warning("Nothing to split — download the dataset first (see docs/datasets/).")
            return 0
        manifest = split_samples([s.sample_id for s in discovery.samples], ratios=ratios, seed=args.seed)
        manifest.save_yaml(output)
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    counts = manifest.to_dict()["counts"]
    logger.info("Split written to %s — train=%d val=%d test=%d",
                output, counts["train"], counts["val"], counts["test"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
