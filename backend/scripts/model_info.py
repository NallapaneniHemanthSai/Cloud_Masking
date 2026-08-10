#!/usr/bin/env python3
"""Report baseline-model metadata (Milestone 6).

Thin CLI: builds a :class:`ModelConfig`, and — if PyTorch is available — constructs the model, prints a
:class:`ModelSummary` (parameter counts) and a :class:`CheckpointMetadata` JSON (no weights saved). If
PyTorch is unavailable it prints a meaningful message plus the deterministic config hash. No training.

Usage:
    python backend/scripts/model_info.py --name unet --in-channels 13 --classes 4
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.exceptions import CloudMaskingError  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.models._torch import torch_available  # noqa: E402
from app.models.config import ModelConfig  # noqa: E402
from app.models.factory import ModelFactory  # noqa: E402

logger = logging.getLogger("model_info")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report baseline model metadata.")
    parser.add_argument("--name", default="unet")
    parser.add_argument("--in-channels", type=int, default=13)
    parser.add_argument("--classes", type=int, default=4)
    parser.add_argument("--encoder-depth", type=int, default=4)
    parser.add_argument("--base-channels", type=int, default=32)
    parser.add_argument("--activation", default="relu")
    parser.add_argument("--normalization", default="batch")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)

    try:
        config = ModelConfig(
            name=args.name, in_channels=args.in_channels, num_classes=args.classes,
            encoder_depth=args.encoder_depth, base_channels=args.base_channels,
            activation=args.activation, normalization=args.normalization,
        )
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    logger.info("Config: %s | hash=%s", config.to_dict(), config.config_hash())

    if not torch_available():
        logger.warning("PyTorch not available — reporting config only (guarded).")
        return 0

    try:
        factory = ModelFactory()
        model = factory.create(config)
        summary = factory.summary(config)
        artifact = factory.build_artifact(config, dataset_version="")
        from app.models.initialization import apply_initialization
        _, init_report = apply_initialization(model, "kaiming", return_report=True)
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    print()
    print("Model summary:", summary.to_dict())
    print()
    print("Model artifact:")
    print(artifact.to_json())
    print()
    print("Initialization report:", init_report.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
