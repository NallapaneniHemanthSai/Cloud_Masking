#!/usr/bin/env python3
"""Acquire a bounded CloudSEN12+ subset and run the M12 readiness pipeline (real data).

Thin driver over ``app.datasets.cloudsen12_access`` (tacoreader 0.6.5 adapter) + the M12 pipeline. It:
  1. loads ONE L1C TACO part's metadata (footer only),
  2. selects a deterministic, class/scene-aware, bounded subset (metadata-only — no raster reads),
  3. downloads ONLY that subset into git-ignored ``data/raw/cloudsen12/`` (compressed GeoTIFFs + checksums),
  4. runs the M12 pipeline (validation → subset → group-aware split → train-only normalization →
     class distribution → patch manifest → DatasetArtifact → readiness gate) into ``data/processed/cloudsen12/``.

Never downloads the full ~1 TB dataset. Never bypasses access controls. No fabricated results.

Usage (project venv):
    backend/.venv/bin/python backend/scripts/acquire_cloudsen12.py --subset 40 --seed 1 --patch 128
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
from app.core.logging_config import setup_logging  # noqa: E402
from app.datasets.cloudsen12_access import (  # noqa: E402
    download_selected,
    load_acquired,
    load_l1c_part,
    read_image,
    read_label,
    select_cloudsen12_subset,
    to_pipeline_inputs,
)
from app.datasets.experimental_config import ExperimentalDatasetConfig  # noqa: E402
from app.datasets.pipeline import default_processed_dir, prepare_real_local_dataset  # noqa: E402
from app.datasets.records import REGIME_REAL, ExperimentalDatasetRecord  # noqa: E402

logger = logging.getLogger("acquire_cloudsen12")


def _parse_args(argv=None):
    settings = get_settings()
    p = argparse.ArgumentParser(description="Acquire a bounded CloudSEN12+ subset + run readiness.")
    p.add_argument("--subset", type=int, default=40)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--patch", type=int, default=128)
    p.add_argument("--part", type=int, default=0)
    p.add_argument("--min-thin", type=float, default=10.0)
    p.add_argument("--min-shadow", type=float, default=10.0)
    p.add_argument("--raw-dir", type=Path, default=settings.data_raw_dir / "cloudsen12")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--resume", action="store_true",
                   help="Reuse an already-downloaded subset (provenance.json) instead of re-downloading.")
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)
    settings = get_settings()
    output = args.output or default_processed_dir("cloudsen12", settings.data_dir)

    resumed = load_acquired(args.raw_dir) if args.resume else None
    if resumed is not None:
        acquired, prov = resumed
        source_url = prov.get("selection", {}).get("source_url", "")
        plan_dict = prov.get("selection", {})
        logger.info("RESUME: reusing %d already-acquired sample(s) from %s (no re-download).",
                    len(acquired), args.raw_dir)
    else:
        df = load_l1c_part(args.part)
        logger.info("L1C part %d metadata: %d samples.", args.part, df.shape[0])
        hi, plan = select_cloudsen12_subset(
            df, seed=args.seed, subset_size=args.subset, part_index=args.part,
            min_thin_pct=args.min_thin, min_shadow_pct=args.min_shadow)
        logger.info("Selected %d sample positions; downloading to %s ...", len(plan.positions), args.raw_dir)
        acquired = download_selected(hi, plan, args.raw_dir)
        source_url = plan.source_url
        plan_dict = plan.to_dict()
    if not acquired:
        logger.error("No samples acquired — aborting (nothing to prepare).")
        return 1

    inputs = to_pipeline_inputs(acquired)
    from app.utils.hashing import stable_hash
    dataset_version = f"cloudsen12plus-1.1.2-l1c-p{args.part}-{stable_hash(plan_dict)[:8]}"
    record = ExperimentalDatasetRecord(
        dataset_id="cloudsen12", dataset_name="CloudSEN12+ (L1C, high-quality subset)",
        version=dataset_version, source="tacofoundation/cloudsen12 (Hugging Face)",
        source_url=source_url, license="CC0-1.0", access_status="tacoreader 0.6.5 (public, CC0)",
        download_date=_today(), local_path=str(args.raw_dir),
        checksum="verified (per-file sha256)", band_count=13, class_count=4,
        class_mapping={"0": "clear", "1": "thick_cloud", "2": "thin_cloud", "3": "cloud_shadow"},
        spatial_resolution="10 m (Sentinel-2)", data_regime=REGIME_REAL,
        notes="Bounded curated subset; raw payloads git-ignored; not redistributed.")

    config = ExperimentalDatasetConfig(
        dataset_id="cloudsen12", dataset_version=dataset_version, patch_size=args.patch,
        subset_size=len(acquired), seed=args.seed, band_count=13, class_count=4)

    prepared = prepare_real_local_dataset(
        config, samples=inputs["samples"], groups=inputs["groups"],
        sample_classes=inputs["sample_classes"], checksums=inputs["checksums"],
        image_reader=read_image, label_reader=read_label, image_size=inputs["image_size"],
        dataset_version=dataset_version, dataset_record=record, output_dir=output, expected_bands=1)

    _print_summary(prepared, acquired, output)
    return 0 if prepared.readiness.ready else 2


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


def _print_summary(prepared, acquired, output: Path) -> None:
    a = prepared.artifact
    cd = prepared.class_distribution
    print()
    print(f"=== CloudSEN12+ REAL acquisition + readiness ===")
    print(f"acquired samples: {len(acquired)}  | dataset_version: {a.dataset_version}")
    print(f"artifact: {a.artifact_id}  content_hash={a.content_hash()[:12]}")
    print(f"validation: {prepared.validation.overall_status}")
    print(f"split: {prepared.split_manifest.counts()}  leakage_ok={prepared.split_manifest.leakage_ok()}")
    print(f"patches: {prepared.patch_count}  normalization_hash={prepared.normalization_hash[:10]}")
    print("class distribution (pixels / fraction):")
    for c in cd.class_names:
        star = "  <-- thin cloud (PRIMARY)" if c == "thin_cloud" else ""
        print(f"  {c:<14} {cd.pixel_counts.get(c, 0):>12}  ({cd.percentages().get(c, 0):.4f}){star}")
    print(f"imbalance_severe={cd.imbalance_severe()}  thin_cloud_fraction={cd.thin_cloud_fraction()}")
    print(f"REAL DATASET READY = {prepared.readiness.ready}")
    if prepared.readiness.critical_failures:
        print(f"failed gates: {prepared.readiness.critical_failures}")
    print(f"outputs -> {output}")


if __name__ == "__main__":
    raise SystemExit(main())
