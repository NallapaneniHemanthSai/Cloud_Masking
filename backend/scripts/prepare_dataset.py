#!/usr/bin/env python3
"""Dataset preparation CLI (Milestone 12) — thin wrapper over ``app.datasets``.

Prepares one reproducible experimental dataset: availability → validation → deterministic subset →
group-aware split → train-only normalization → class distribution → dataset artifact → readiness gate →
M11 handoff. With ``--synthetic-smoke`` it runs the whole pipeline on a labelled synthetic fixture
(PIPELINE VALIDATION ONLY, NOT A BENCHMARK). Without real data present, the real regime honestly reports
``NOT PRESENT`` and readiness ``False`` — **no hidden downloads, no fabricated results.** No pipeline logic
lives here.

Usage:
    python backend/scripts/prepare_dataset.py --dataset cloudsen12 --synthetic-smoke --subset 24 --seed 1
    python backend/scripts/prepare_dataset.py --dataset cloudsen12 --require-ready
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
from app.datasets.experimental_config import ExperimentalDatasetConfig  # noqa: E402
from app.datasets.pipeline import default_processed_dir, prepare_experimental_dataset  # noqa: E402

logger = logging.getLogger("prepare_dataset")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    p = argparse.ArgumentParser(description="Prepare a reproducible experimental dataset.")
    p.add_argument("--dataset", default="cloudsen12")
    p.add_argument("--manifest", type=Path, default=None, help="Optional ExperimentalDatasetConfig JSON.")
    p.add_argument("--subset", type=int, default=24, help="Curated subset target size.")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--data-root", type=Path, default=settings.data_dir)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--patch", type=int, default=16)
    p.add_argument("--band-count", type=int, default=13)
    p.add_argument("--classes", type=int, default=4)
    p.add_argument("--synthetic-smoke", action="store_true",
                   help="Run the full pipeline on a SYNTHETIC / PIPELINE-VALIDATION-ONLY fixture.")
    p.add_argument("--require-ready", action="store_true",
                   help="Exit non-zero unless the prepared dataset passes the readiness gate.")
    p.add_argument("--log-level", default=settings.log_level)
    return p.parse_args(argv)


def _build_config(args: argparse.Namespace) -> ExperimentalDatasetConfig:
    if args.manifest is not None:
        import json
        return ExperimentalDatasetConfig.from_dict(
            json.loads(Path(args.manifest).read_text(encoding="utf-8")))
    return ExperimentalDatasetConfig(dataset_id=args.dataset, subset_size=args.subset, seed=args.seed,
                                     patch_size=args.patch, band_count=args.band_count,
                                     class_count=args.classes)


def _default_output(args: argparse.Namespace, settings) -> Path:
    if args.output is not None:
        return args.output
    if args.synthetic_smoke:                # keep synthetic OUT of data/processed (never mix with real)
        return settings.outputs_dir / "dataset_synthetic" / args.dataset
    return default_processed_dir(args.dataset, args.data_root)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)
    settings = get_settings()
    output = _default_output(args, settings)

    try:
        config = _build_config(args)
        logger.info("Experimental config hash: %s", config.config_hash()[:12])
        prepared = prepare_experimental_dataset(
            config, synthetic=args.synthetic_smoke, output_dir=output, data_root=args.data_root)
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    _print_summary(prepared, output)

    if args.require_ready and not prepared.readiness.ready:
        logger.error("Readiness gate FAILED — dataset is not experiment-ready.")
        return 2
    return 0


def _print_summary(prepared, output: Path) -> None:
    a = prepared.artifact
    v = prepared.validation
    print()
    print(f"Experimental dataset [{prepared.data_regime}]  artifact={a.artifact_id}")
    print(f"  dataset_version={a.dataset_version}  content_hash={a.content_hash()[:12]}")
    print(f"  validation={v.overall_status}  READY={prepared.readiness.ready}")
    if prepared.subset is not None:
        print(f"  subset={prepared.subset.size}/{prepared.subset.pool_size}  "
              f"selection_hash={prepared.subset.selection_hash()[:10]}")
    if prepared.split_manifest is not None:
        print(f"  split={prepared.split_manifest.counts()}  leakage_ok={prepared.split_manifest.leakage_ok()}")
    if prepared.class_distribution is not None:
        cd = prepared.class_distribution
        print("  class distribution (pixels):")
        for c in cd.class_names:
            star = "  <-- thin cloud (PRIMARY)" if c == "thin_cloud" else ""
            print(f"    {c:<14} {cd.pixel_counts.get(c, 0):>10}  ({cd.percentages().get(c, 0):.4f}){star}")
        print(f"  imbalance_severe={cd.imbalance_severe()}  thin_cloud_fraction={cd.thin_cloud_fraction()}")
    if prepared.readiness.critical_failures:
        print(f"  critical gate failures: {prepared.readiness.critical_failures}")
    if prepared.readiness.warnings:
        print(f"  warnings: {prepared.readiness.warnings}")
    if prepared.written:
        print(f"  outputs -> {output}")
    print()
    print("  NOTE: real model quality is NOT YET MEASURED — this is a dataset-readiness milestone.")


if __name__ == "__main__":
    raise SystemExit(main())
