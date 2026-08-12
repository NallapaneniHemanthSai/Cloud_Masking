#!/usr/bin/env python3
"""Failure-analysis CLI (Milestone 9) — thin wrapper over ``app.failure_analysis``.

Loads an evaluation result (or runs a synthetic demo), runs failure analysis, writes JSON/CSV/Markdown
reports, prints the top confusing cases, and optionally emits visualization specs. **No analysis logic
lives here.**

Without a real dataset this runs on **synthetic** predictions/targets (``--demo``, the default). Synthetic
outputs are clearly labelled and are NOT real-data failure statistics (NOT YET MEASURED).

Usage:
    python backend/scripts/analyze_failures.py --mode multiclass --split test
    python backend/scripts/analyze_failures.py --input outputs/evaluation/cloudsen12_test_eval.json
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
from app.evaluation.config import CLOUDSEN12_CLASS_NAMES, ON_CLOUD_N_CLASS_NAMES  # noqa: E402
from app.evaluation.records import EvaluationRun  # noqa: E402
from app.failure_analysis import (  # noqa: E402
    FailureAnalysisConfig,
    analyze_failures,
    confusing_case_specs,
    export_failure_report,
)

logger = logging.getLogger("analyze_failures")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Analyse confusing cases / failures from an evaluation.")
    parser.add_argument("--input", type=Path, default=None,
                        help="Path to an M8 EvaluationRun JSON (pixel-level analysis).")
    parser.add_argument("--mode", choices=["multiclass", "binary"], default="multiclass")
    parser.add_argument("--split", default="test")
    parser.add_argument("--model-id", default="synthetic-model")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--viz-specs", action="store_true", help="Also emit confusing-case viz specs.")
    parser.add_argument("--output-dir", type=Path, default=settings.outputs_dir / "failure_analysis")
    parser.add_argument("--log-level", default=settings.log_level)
    return parser.parse_args(argv)


def _synthetic_samples(num_classes: int, seed: int):
    import numpy as np
    rng = np.random.RandomState(seed)
    samples = []
    for i, group in enumerate(("region_a", "region_b", "region_a", "region_b")):
        targets = rng.randint(0, num_classes, size=(16, 16))
        noise = rng.rand(16, 16) < (0.15 + 0.15 * (i % 3))   # varying difficulty
        preds = np.where(noise, rng.randint(0, num_classes, size=(16, 16)), targets)
        samples.append({"sample_id": f"chip_{i:03d}", "targets": targets, "predictions": preds,
                        "group": group, "source_reference": f"data/{group}/chip_{i:03d}.tif"})
    return samples


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)

    try:
        names = ON_CLOUD_N_CLASS_NAMES if args.mode == "binary" else CLOUDSEN12_CLASS_NAMES
        dataset = "on_cloud_n" if args.mode == "binary" else "cloudsen12"
        config = FailureAnalysisConfig(dataset=dataset, split=args.split, mode=args.mode,
                                       class_names=names, model_id=args.model_id, top_k=args.top_k)

        evaluation_result = None
        if args.input is not None:
            evaluation_result = EvaluationRun.load_json(args.input).result
            logger.info("Loaded evaluation result from %s (pixel-level analysis).", args.input)
            samples = None
        else:
            logger.warning("SYNTHETIC data — outputs are NOT real-data failure statistics (NOT YET MEASURED).")
            samples = _synthetic_samples(len(names), args.seed)

        # Pixel-level needs a confusion; synthesise one from the samples when no --input is given.
        confusion = None
        if evaluation_result is None:
            from app.evaluation import EvaluationConfig, EvaluationRunner
            ecfg = (EvaluationConfig.on_cloud_n(split=args.split) if args.mode == "binary"
                    else EvaluationConfig.cloudsen12(split=args.split))
            runner = EvaluationRunner(ecfg)
            for s in samples:
                runner.update(s["targets"], s["predictions"])
            confusion = runner.confusion

        result = analyze_failures(config, evaluation_result=evaluation_result, confusion=confusion,
                                  samples=samples)
        written = export_failure_report(result, args.output_dir / f"{dataset}_{args.split}_failures")

        if args.viz_specs and result.sample_failures:
            specs = [confusing_case_specs(sf, config,
                                          ground_truth_source=Path(sf.source_reference),
                                          prediction_source=Path(sf.source_reference))
                     for sf in result.sample_failures[:args.top_k]]
            (args.output_dir / f"{dataset}_{args.split}_viz_specs.json").write_text(
                json.dumps(specs, indent=2), encoding="utf-8")
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    print()
    print("Top confusing cases:")
    for h in result.hard_examples.get("by_error_rate", [])[:args.top_k]:
        print(f"  #{h.rank} {h.sample_id}: error_rate={h.value:.3f} severity={h.severity}")
    print()
    logger.info("Reports: %s", ", ".join(str(p) for p in written.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
