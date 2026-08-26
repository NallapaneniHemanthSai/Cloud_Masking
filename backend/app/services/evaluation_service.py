"""Evaluation service (Milestone 13).

Runs an evaluation through the reused M8 framework (`EvaluationRunner` + `build_summary`) and persists an
:class:`EvaluationRunRow`. Defaults to **synthetic** predictions/targets (labelled ``SYNTHETIC``) so the
endpoint needs no real dataset. numpy only (no torch). Thin-cloud IoU is surfaced explicitly.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import EvaluationError
from app.db.base import Database
from app.db.models import EvaluationRunRow


def run_evaluation(db: Database, *, mode: str = "multiclass", dataset: str = "cloudsen12",
                   split: str = "test", seed: int = 0, synthetic: bool = True) -> dict[str, Any]:
    """Run a (synthetic by default) evaluation and persist its summary."""
    if not synthetic:
        raise EvaluationError("Only synthetic evaluation is exposed via the API in M13 (real-data "
                              "evaluation runs through the offline pipeline). Set synthetic=true.")
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise EvaluationError("numpy is required for /evaluate.") from exc

    from app.evaluation import EvaluationConfig, EvaluationRunner, build_summary

    config = (EvaluationConfig.on_cloud_n(split=split) if mode == "binary"
              else EvaluationConfig.cloudsen12(split=split))
    runner = EvaluationRunner(config)
    rng = np.random.RandomState(seed)
    for _ in range(4):                                   # synthetic (targets, preds) batches
        targets = rng.randint(0, config.num_classes, size=(16, 16))
        noise = rng.rand(16, 16) < 0.25
        preds = np.where(noise, rng.randint(0, config.num_classes, size=(16, 16)), targets)
        runner.update(targets, preds)
    result = runner.compute_result()
    summary = build_summary(result)

    evaluation_id = f"eval-{uuid.uuid4().hex[:12]}"
    with db.session() as s:
        row = EvaluationRunRow(
            evaluation_id=evaluation_id, dataset=dataset, split=split, model_id="synthetic-model",
            config_hash=config.config_hash(), data_regime="SYNTHETIC",
            pixel_accuracy=summary.pixel_accuracy, macro_iou=summary.macro_iou,
            thin_cloud_iou=summary.thin_cloud_iou,
            notes="SYNTHETIC / VALIDATION ONLY — not a real-data metric.")
        s.add(row)
        s.flush()
        out = row.to_dict()
    out["per_class_iou"] = summary.per_class_iou
    out["config_hash"] = config.config_hash()
    return out
