#!/usr/bin/env python3
"""Evaluation CLI (Milestone 8) — thin wrapper over the evaluation framework.

Loads an :class:`EvaluationConfig`, runs an evaluation, generates JSON/CSV/Markdown reports, and prints a
concise summary. **No evaluation logic lives here** — it delegates to ``app.evaluation``.

Without a downloaded dataset this runs on **synthetic** predictions/targets (``--demo``, the default) so
the pipeline and reports can be exercised. Synthetic outputs are clearly labelled and are NOT real-data
metrics.

Usage:
    python backend/scripts/evaluate.py --mode multiclass --split test
    python backend/scripts/evaluate.py --mode binary --split test
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
from app.evaluation import (  # noqa: E402
    EvaluationConfig,
    EvaluationRunner,
    build_summary,
    export_evaluation_report,
    stratified_evaluation,
)

logger = logging.getLogger("evaluate")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run a segmentation evaluation and write reports.")
    parser.add_argument("--mode", choices=["multiclass", "binary"], default="multiclass")
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--split", default="test")
    parser.add_argument("--model-id", default="synthetic-model")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=settings.outputs_dir / "evaluation")
    parser.add_argument("--demo", action="store_true", default=True,
                        help="Run on synthetic data (default; no real dataset required).")
    parser.add_argument("--log-level", default=settings.log_level)
    return parser.parse_args(argv)


def _synthetic_grouped_batches(config: EvaluationConfig, seed: int):
    """Generate synthetic (targets, predictions, group) batches. SYNTHETIC — not real-data metrics."""
    import numpy as np
    rng = np.random.RandomState(seed)
    batches = []
    for group in ("region_a", "region_b"):
        for _ in range(2):
            targets = rng.randint(0, config.num_classes, size=(16, 16))
            # Predictions: mostly correct, with some noise, to produce non-trivial metrics.
            noise = rng.rand(16, 16) < 0.25
            preds = np.where(noise, rng.randint(0, config.num_classes, size=(16, 16)), targets)
            batches.append((targets, preds, group))
    return batches


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)

    try:
        if args.mode == "binary":
            config = EvaluationConfig.on_cloud_n(split=args.split, model_id=args.model_id)
        else:
            config = EvaluationConfig.cloudsen12(split=args.split, model_id=args.model_id)
        if args.dataset:
            config = EvaluationConfig.from_dict({**config.to_dict(), "dataset": args.dataset})

        logger.warning("Running on SYNTHETIC data — outputs are NOT real-data metrics (NOT YET MEASURED).")
        batches = _synthetic_grouped_batches(config, args.seed)
        stratified = stratified_evaluation(config, batches)
        run = EvaluationRunner(config).build_run(stratified.overall, stratified=stratified,
                                                 notes="synthetic demo (not real-data metrics)")
        written = export_evaluation_report(run, args.output_dir / f"{config.dataset}_{args.split}_eval")
        summary = build_summary(run.result)
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    print()
    print("Evaluation summary (SYNTHETIC):", summary.to_dict())
    print()
    logger.info("Reports: %s", ", ".join(str(p) for p in written.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
