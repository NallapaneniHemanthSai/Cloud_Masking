"""Prediction service (Milestone 13).

Runs inference through the reused :class:`app.inference.predictor.Predictor` (M6 models + M4 tiling + M7
checkpoint loading) and persists a :class:`PredictionRow`. Accepts an inline ``(C,H,W)`` image or, by
default, a small synthetic input (labelled ``SYNTHETIC``). Requires torch. An untrained model yields a
structurally-valid mask — **not** a benchmark.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.core.exceptions import InferenceError
from app.db.base import Database
from app.db.models import PredictionRow


def run_prediction(db: Database, *, architecture: str = "unet", in_channels: int = 13, num_classes: int = 4,
                   encoder_depth: int = 2, base_channels: int = 8, device: str = "cpu", patch_size: int = 32,
                   checkpoint_path: str | None = None, image: Any = None, synthetic: bool = True,
                   source: str = "") -> dict[str, Any]:
    """Run tiled inference and persist the prediction record."""
    from app.models._torch import torch_available
    if not torch_available():
        raise InferenceError("PyTorch is required for /predict but is not available in this environment.")

    import numpy as np

    from app.inference.predictor import Predictor
    from app.models import ModelConfig

    config = ModelConfig(name=architecture, in_channels=in_channels, num_classes=num_classes,
                         encoder_depth=encoder_depth, base_channels=base_channels)
    predictor = Predictor(config, device=device, patch_size=patch_size)
    if checkpoint_path:
        predictor.load_checkpoint(Path(checkpoint_path))
        source = source or f"checkpoint:{checkpoint_path}"

    if image is not None:
        arr = np.asarray(image, dtype="float32")
        regime = "REAL" if not synthetic else "SYNTHETIC"
    else:
        rng = np.random.RandomState(0)
        arr = rng.rand(in_channels, patch_size, patch_size).astype("float32")
        regime = "SYNTHETIC"
        source = source or "synthetic-input"
    if arr.ndim != 3 or arr.shape[0] != in_channels:
        raise InferenceError(f"image must be (C={in_channels},H,W); got {list(arr.shape)}.")

    result = predictor.predict(arr, source=source, data_regime=regime)
    rd = result.to_dict()

    with db.session() as s:
        row = PredictionRow(
            prediction_id=f"{rd['prediction_id']}-{uuid.uuid4().hex[:6]}", architecture=architecture,
            model_ref=checkpoint_path or "in-memory", num_classes=num_classes,
            input_shape=str(rd["input_shape"]), output_shape=str(rd["output_shape"]),
            device=result.device, data_regime=regime, source=source,
            class_pixel_counts=json.dumps(result.class_pixel_counts),
            notes="Untrained model unless a checkpoint was provided — mask is structural, not a benchmark.")
        s.add(row)
        s.flush()
        persisted = row.to_dict()
    persisted["input_shape"] = rd["input_shape"]
    persisted["output_shape"] = rd["output_shape"]
    return persisted
