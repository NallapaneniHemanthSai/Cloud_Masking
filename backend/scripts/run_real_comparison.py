#!/usr/bin/env python3
"""Real M11 controlled comparison on the prepared CloudSEN12+ subset (U-Net vs Attention U-Net).

Runs ONLY after the M12 readiness gate is TRUE. Builds real normalized patches from the acquired subset
(train-only normalization applied to every split — no leakage), then drives the **existing M11
ComparisonRunner** via its small real-data hook (``data_provider``) — both arms get identical data, split,
preprocessing, normalization, seed, budget, optimizer, scheduler, loss, device; only the architecture
differs. Reuses M7 training, M8 evaluation, M9 failure analysis. Trains on MPS when available.

Usage (project venv, with SSL_CERT_FILE/CURL_CA_BUNDLE set for rasterio /vsicurl if reading remote):
    backend/.venv/bin/python backend/scripts/run_real_comparison.py --epochs 12 --batch 8 --device mps
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import numpy as np  # noqa: E402

from app.comparison import ComparisonConfig, ComparisonRunner, export_comparison_report  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.datasets.cloudsen12_access import read_image, read_label  # noqa: E402
from app.datasets.pipeline import default_processed_dir  # noqa: E402
from app.datasets.records import ExperimentalSplitManifest  # noqa: E402
from app.preprocessing.normalization import BandStats, NormalizationStatistics, normalize  # noqa: E402
from app.preprocessing.patching import generate_patch_grid  # noqa: E402

logger = logging.getLogger("run_real_comparison")
_NODATA = 65535.0


def _parse_args(argv=None):
    settings = get_settings()
    p = argparse.ArgumentParser(description="Real M11 U-Net vs Attention U-Net on CloudSEN12+ subset.")
    p.add_argument("--processed", type=Path, default=default_processed_dir("cloudsen12", settings.data_dir))
    p.add_argument("--patch", type=int, default=128)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--epochs", type=int, default=12)
    p.add_argument("--encoder-depth", type=int, default=3)
    p.add_argument("--base-channels", type=int, default=16)
    p.add_argument("--device", default="mps")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--seeds", type=int, nargs="+", default=None)
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def _load_norm(processed: Path) -> tuple[NormalizationStatistics, BandStats]:
    stats = NormalizationStatistics.load_json(processed / "normalization_statistics.json")
    bs = BandStats(minimum=stats.minimums, maximum=stats.maximums, mean=stats.means, std=stats.stds,
                   p_low=stats.p_low, p_high=stats.p_high)
    return stats, bs


def _id_to_paths(processed: Path, settings) -> dict[str, tuple[str, str, str]]:
    prov = json.loads((Path(settings.data_raw_dir) / "cloudsen12" / "provenance.json").read_text())
    return {s["sample_id"]: (s["image_path"], s["label_path"], s.get("roi_id", "")) for s in prov["samples"]}


def _build_split_patches(ids, id2paths, bs, mode, patch):
    """Return list of (img (C,ps,ps) f32, label (ps,ps) i64, meta) for the given sample ids."""
    out = []
    for sid in ids:
        ip, lp, roi = id2paths[sid]
        img = normalize(read_image(ip).astype("float64"), mode=mode, stats=bs,
                        nodata=_NODATA).astype("float32")          # (C,512,512)
        lab = read_label(lp).astype("int64")                        # (512,512)
        h, w = lab.shape
        for win in generate_patch_grid(h, w, patch, 0):
            r, c = win.row_off, win.col_off
            if r + patch > h or c + patch > w:
                continue
            out.append((img[:, r:r + patch, c:c + patch], lab[r:r + patch, c:c + patch],
                        {"sample_id": sid, "group": roi, "split": "?"}))
    return out


def _make_batches(patches, batch, shuffle_seed=None):
    import torch
    idx = list(range(len(patches)))
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(idx)
    xb, meta = [], []
    for i in range(0, len(idx), batch):
        chunk = idx[i:i + batch]
        x = torch.from_numpy(np.ascontiguousarray(np.stack([patches[j][0] for j in chunk])))
        y = torch.from_numpy(np.ascontiguousarray(np.stack([patches[j][1] for j in chunk])))
        xb.append((x, y))
        meta.append([patches[j][2] for j in chunk])
    return xb, meta


def main(argv=None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)
    settings = get_settings()
    processed = args.processed
    output = args.output or (processed / "m11")

    split = ExperimentalSplitManifest.load_json(processed / "split_manifest.json")
    if not split.leakage_ok():
        logger.error("Split leakage detected — refusing to train."); return 2
    stats, bs = _load_norm(processed)
    id2paths = _id_to_paths(processed, settings)
    mode = stats.normalization_mode

    logger.info("Building real patches (patch=%d) ...", args.patch)
    train_p = _build_split_patches(split.ids_for("train"), id2paths, bs, mode, args.patch)
    test_p = _build_split_patches(split.ids_for("test"), id2paths, bs, mode, args.patch)
    logger.info("Patches: train=%d test=%d", len(train_p), len(test_p))

    # Identical, fixed-order batches for BOTH arms (fairness): train shuffled once with a fixed seed.
    train_batches, _ = _make_batches(train_p, args.batch, shuffle_seed=args.seed)
    test_batches, test_meta = _make_batches(test_p, args.batch, shuffle_seed=None)
    del train_p, test_p

    def data_provider(plan):
        return train_batches, test_batches, test_meta

    # Real comparison config — small U-Net, MPS, identical everything except architecture.
    config = ComparisonConfig.cloudsen12(
        in_channels=13, num_classes=4, patch_size=args.patch, encoder_depth=args.encoder_depth,
        base_channels=args.base_channels, epochs=args.epochs, batch_size=args.batch,
        device=args.device, seed=args.seed)
    cfg_dict = config.to_dict()
    cfg_dict["dataset_version"] = _dataset_version(processed)
    cfg_dict["comparison_name"] = "unet_vs_attention_unet_REAL_cloudsen12"
    config = ComparisonConfig.from_dict(cfg_dict)

    seeds = args.seeds if args.seeds is not None else [args.seed]
    runner = ComparisonRunner(config, synthetic=False, data_provider=data_provider,
                              batch_size=args.batch, output_dir=output)
    logger.info("Running REAL M11 comparison on device=%s, seeds=%s ...", args.device, seeds)
    result = runner.run(seeds=seeds)

    output.mkdir(parents=True, exist_ok=True)
    result.artifact.save_json(output / "comparison_artifact.json")
    export_comparison_report(result.artifact, output / "comparison_report")
    (output / "viz_specs.json").write_text(json.dumps(result.viz_specs, indent=2), encoding="utf-8")

    _print_report(result)
    return 0


def _dataset_version(processed: Path) -> str:
    try:
        return json.loads((processed / "dataset_artifact.json").read_text())["dataset_version"]
    except Exception:  # noqa: BLE001
        return ""


def _print_report(result) -> None:
    mc, cc, fc, d = result.metric, result.compute, result.failure, result.decision
    print("\n================ REAL M11 COMPARISON (CloudSEN12+, MEASURED) ================")
    print(f"data_regime={result.artifact.data_regime}  metric_status={mc.status}  "
          f"seeds_executed={result.seeds_executed}")
    print(f"device: baseline={cc.baseline.device} improved={cc.improved.device}")
    print("\nPer-class IoU / Dice / Recall  (baseline -> improved, Δ):")
    for c in mc.per_class:
        b, i, dl = c.baseline, c.improved, c.delta
        tag = "  <== THIN CLOUD" if c.class_name == "thin_cloud" else (
            "  <== CLOUD SHADOW" if c.class_name == "cloud_shadow" else "")
        print(f"  {c.class_name:<13} IoU {b.get('iou')!s:>7}->{i.get('iou')!s:>7} (Δ{dl.get('iou')}) "
              f"| Dice {b.get('dice')!s:>7}->{i.get('dice')!s:>7} | Rec {b.get('recall')!s:>7}->{i.get('recall')!s:>7}{tag}")
    print(f"\nmacro IoU Δ={mc.macro_delta.get('iou')}  micro IoU Δ={mc.micro_delta.get('iou')}  "
          f"weighted IoU Δ={mc.weighted_delta.get('iou')}")
    t = mc.thin_cloud
    print(f"THIN-CLOUD: IoU {t.baseline_iou}->{t.improved_iou} (Δ{t.iou_delta}) | "
          f"Dice {t.baseline_dice}->{t.improved_dice} | Recall {t.baseline_recall}->{t.improved_recall} | "
          f"FN {t.baseline_false_negatives}->{t.improved_false_negatives} | regressed={t.regressed}")
    print(f"\nCompute: params {cc.baseline.parameter_count}->{cc.improved.parameter_count} "
          f"(x{cc.parameter_ratio}) | train_s {cc.baseline.total_training_seconds}->"
          f"{cc.improved.total_training_seconds} (x{cc.training_time_ratio})")
    print(f"Failures: thin_cloud {fc.baseline.thin_cloud_failures}->{fc.improved.thin_cloud_failures} "
          f"(Δ{fc.thin_cloud_failure_delta}) | FP {fc.baseline.false_positives}->{fc.improved.false_positives} "
          f"| FN {fc.baseline.false_negatives}->{fc.improved.false_negatives}")
    print(f"\nDECISION: {d.outcome}  (uncertainty={d.uncertainty_status})")
    for r in d.rationale:
        print(f"  - {r}")


if __name__ == "__main__":
    raise SystemExit(main())
