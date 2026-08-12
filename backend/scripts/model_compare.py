#!/usr/bin/env python3
"""Architecture comparison CLI (Milestone 10) — U-Net vs improved Attention U-Net.

Thin wrapper over ``app.models.comparison``. Builds both architectures at the same input shape, MEASURES
their parameters + output shape, and prints/writes a structured comparison. Memory is NOT MEASURED and
FLOPs are DEFERRED (never fabricated). **No performance is compared — real-data results are NOT YET
MEASURED.** No training code lives here.

Usage:
    python backend/scripts/model_compare.py --in-channels 13 --classes 4 --patch 128
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.exceptions import CloudMaskingError  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.models._torch import torch_available  # noqa: E402
from app.models.config import ModelConfig  # noqa: E402

logger = logging.getLogger("model_compare")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Compare U-Net and the improved Attention U-Net.")
    parser.add_argument("--in-channels", type=int, default=13)
    parser.add_argument("--classes", type=int, default=4)
    parser.add_argument("--encoder-depth", type=int, default=4)
    parser.add_argument("--base-channels", type=int, default=32)
    parser.add_argument("--patch", type=int, default=128)
    parser.add_argument("--output-dir", type=Path, default=settings.outputs_dir / "model_compare")
    parser.add_argument("--log-level", default=settings.log_level)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)

    def cfg(name: str) -> ModelConfig:
        return ModelConfig(name=name, in_channels=args.in_channels, num_classes=args.classes,
                           encoder_depth=args.encoder_depth, base_channels=args.base_channels)

    unet_cfg, attn_cfg = cfg("unet"), cfg("attention_unet")
    logger.info("Configs: unet_hash=%s attention_hash=%s", unet_cfg.config_hash(), attn_cfg.config_hash())

    if not torch_available():
        logger.warning("PyTorch unavailable — availability=False; parameters/shapes NOT MEASURED.")
        print(json.dumps({"availability": False,
                          "configs": {"unet": unet_cfg.to_dict(), "attention_unet": attn_cfg.to_dict()},
                          "measurement_status": "NOT_MEASURED (torch unavailable)"}, indent=2))
        return 0

    try:
        from app.models.comparison import compare_architectures
        comparison = compare_architectures([unet_cfg, attn_cfg],
                                           (1, args.in_channels, args.patch, args.patch))
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    out = args.output_dir / f"comparison_c{args.in_channels}_k{args.classes}_p{args.patch}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(comparison.to_dict(), indent=2), encoding="utf-8")

    print()
    print("Architecture comparison (availability=True; performance NOT YET MEASURED):")
    for p in comparison.profiles:
        print(f"  {p.architecture:<16} params={p.parameter_count:>10,}  out={p.output_shape}  "
              f"mem={p.estimated_memory}  flops={p.flops}")
    print(f"  parameter delta vs {comparison.baseline}: {comparison.parameter_delta()}")
    print()
    logger.info("Wrote comparison: %s", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
