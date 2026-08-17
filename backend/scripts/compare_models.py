#!/usr/bin/env python3
"""Controlled model-comparison CLI (Milestone 11) — U-Net vs Attention U-Net.

Thin wrapper over ``app.comparison``. Builds (or loads) a single :class:`ComparisonConfig`, checks the
fairness guardrails (architecture must be the ONLY difference), then either runs a clearly-labelled
**synthetic smoke** comparison (``--synthetic-smoke``; VALIDATION ONLY) or the **real** regime (which
requires a real processed dataset and otherwise leaves quality NOT YET MEASURED). It writes the comparison
JSON artifact + Markdown report + CSV summary and prints the model-by-model table, compute comparison,
failure comparison, and the final decision. **No comparison logic lives here.**

Synthetic mode is NEVER a benchmark. Without real controlled results the decision is INCONCLUSIVE.

Usage:
    python backend/scripts/compare_models.py --synthetic-smoke --epochs 1 --patch 16 --seed 1
    python backend/scripts/compare_models.py --synthetic-smoke --seeds 1 2 3
    python backend/scripts/compare_models.py --config experiments/comparison.json --synthetic-smoke
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

from app.comparison import (  # noqa: E402
    ComparisonConfig,
    ComparisonRunner,
    check_config_fairness,
    export_comparison_report,
)
from app.core.config import get_settings  # noqa: E402
from app.core.exceptions import CloudMaskingError, GuardrailViolation  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.models._torch import torch_available  # noqa: E402
from app.models.config import ModelConfig  # noqa: E402

logger = logging.getLogger("compare_models")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    p = argparse.ArgumentParser(description="Controlled comparison: baseline vs improved model.")
    p.add_argument("--baseline", default="unet", help="Baseline architecture name.")
    p.add_argument("--improved", default="attention_unet", help="Improved architecture name.")
    p.add_argument("--config", type=Path, default=None, help="Path to a ComparisonConfig JSON.")
    p.add_argument("--output", type=Path, default=settings.outputs_dir / "comparison",
                   help="Output directory for the artifact + reports.")
    p.add_argument("--device", default="cpu", help="Torch device (cpu | mps | cuda | auto).")
    p.add_argument("--seed", type=int, default=1, help="Base seed (used when --seeds is omitted).")
    p.add_argument("--seeds", type=int, nargs="+", default=None,
                   help="Seed matrix to execute (e.g. --seeds 1 2 3).")
    p.add_argument("--in-channels", type=int, default=13)
    p.add_argument("--classes", type=int, default=4)
    p.add_argument("--encoder-depth", type=int, default=2)
    p.add_argument("--base-channels", type=int, default=8)
    p.add_argument("--patch", type=int, default=16, help="Synthetic patch size (smoke only).")
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=2)
    p.add_argument("--synthetic-smoke", action="store_true",
                   help="Run a SYNTHETIC / VALIDATION-ONLY smoke comparison (never a benchmark).")
    p.add_argument("--log-level", default=settings.log_level)
    return p.parse_args(argv)


def _build_config(args: argparse.Namespace) -> ComparisonConfig:
    if args.config is not None:
        return ComparisonConfig.from_dict(json.loads(Path(args.config).read_text(encoding="utf-8")))
    return ComparisonConfig.cloudsen12(
        baseline=args.baseline, improved=args.improved, in_channels=args.in_channels,
        num_classes=args.classes, patch_size=args.patch, encoder_depth=args.encoder_depth,
        base_channels=args.base_channels, epochs=args.epochs, batch_size=args.batch_size,
        device=args.device, seed=args.seed)


def _print_tables(result) -> None:
    a = result.artifact
    mc = result.metric
    print()
    print(f"Comparison {a.comparison_id}  (data_regime={a.data_regime}, "
          f"metric_status={mc.status})")
    print(f"  config_hash={a.comparison_config_hash[:12]}  content_hash={a.content_hash()[:12]}")
    print()
    print("Model-by-model per-class IoU (baseline -> improved, Δ):")
    for c in mc.per_class:
        b, i, d = c.baseline.get("iou"), c.improved.get("iou"), c.delta.get("iou")
        star = "  <-- thin cloud (PRIMARY)" if c.class_name == "thin_cloud" else ""
        print(f"  {c.class_name:<14} {b!s:>8} -> {i!s:>8}  (Δ {d}){star}")
    print()
    cc = result.compute
    print(f"Compute (status={cc.status}):")
    print(f"  params:   {cc.baseline.parameter_count} -> {cc.improved.parameter_count} "
          f"(x{cc.parameter_ratio})")
    print(f"  train_s:  {cc.baseline.total_training_seconds} -> {cc.improved.total_training_seconds} "
          f"(x{cc.training_time_ratio})")
    print(f"  peak_mem: {cc.baseline.peak_memory} / {cc.improved.peak_memory}")
    print()
    fc = result.failure
    print(f"Failures (status={fc.status}, hypothesis_supported={fc.hypothesis_supported}):")
    print(f"  thin_cloud_failures: {fc.baseline.thin_cloud_failures} -> "
          f"{fc.improved.thin_cloud_failures} (Δ {fc.thin_cloud_failure_delta})")
    print()
    print(f"DECISION: {result.decision.outcome}")
    for line in result.decision.rationale:
        print(f"  - {line}")
    print()
    print("Limitations:")
    for line in a.limitations:
        print(f"  - {line}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)

    try:
        config = _build_config(args)
        logger.info("Comparison '%s' config_hash=%s", config.comparison_name, config.config_hash()[:12])

        # Fairness guardrails — fail fast if any non-architectural control differs.
        fairness = check_config_fairness(config, strict=True)
        logger.info("Fairness passed=%s (%d controls compared).", fairness.passed, len(fairness.compared))

        seeds = args.seeds if args.seeds is not None else [args.seed]
        if not args.synthetic_smoke:
            logger.warning("Real regime selected. Real-data quality is NOT YET MEASURED unless a real "
                           "processed dataset is present; use --synthetic-smoke to validate the pipeline.")
        if args.synthetic_smoke and not torch_available():
            logger.error("PyTorch unavailable — cannot run the synthetic smoke comparison.")
            return 1

        runner = ComparisonRunner(config, output_dir=args.output, synthetic=args.synthetic_smoke,
                                  synthetic_patch=args.patch, batch_size=args.batch_size)
        result = runner.run(seeds=seeds)

        args.output.mkdir(parents=True, exist_ok=True)
        artifact_path = result.artifact.save_json(args.output / "comparison_artifact.json")
        written = export_comparison_report(result.artifact, args.output / "comparison_report")
        (args.output / "comparison_viz_specs.json").write_text(
            json.dumps(result.viz_specs, indent=2), encoding="utf-8")
    except GuardrailViolation as exc:
        logger.error("Fairness guardrail: %s", exc)
        return 2
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    _print_tables(result)
    logger.info("Artifact: %s", artifact_path)
    logger.info("Reports: %s", ", ".join(str(p) for p in written.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
