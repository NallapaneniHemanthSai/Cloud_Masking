"""Inference / prediction (Milestone 13).

Loads (or builds) a segmentation model and runs **tiled** prediction over a ``(C, H, W)`` image, stitching
per-tile argmax label maps back into a full ``(H, W)`` mask. Reuses M6 models (`ModelFactory`/`ModelConfig`),
M4 tiling (`generate_patch_grid`), and M7 checkpoint loading (`CheckpointManager`). torch/numpy are guarded —
constructing a :class:`Predictor` needs torch; the record type is stdlib-only. No training, no evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.models.config import ModelConfig
from app.preprocessing.patching import generate_patch_grid
from app.utils.hashing import stable_hash


@dataclass
class PredictionResult:
    """A stitched prediction + metadata (no raw logits stored)."""

    architecture: str
    num_classes: int
    input_shape: tuple[int, ...]
    output_shape: tuple[int, ...]
    device: str
    class_pixel_counts: dict[str, int] = field(default_factory=dict)
    config_hash: str = ""
    source: str = ""
    data_regime: str = "SYNTHETIC"

    def prediction_id(self) -> str:
        return "pred-" + stable_hash({
            "architecture": self.architecture, "config_hash": self.config_hash,
            "input_shape": list(self.input_shape), "class_pixel_counts": self.class_pixel_counts,
            "device": self.device, "source": self.source})[:12]

    def to_dict(self) -> dict[str, Any]:
        return {"prediction_id": self.prediction_id(), "architecture": self.architecture,
                "num_classes": self.num_classes, "input_shape": list(self.input_shape),
                "output_shape": list(self.output_shape), "device": self.device,
                "class_pixel_counts": self.class_pixel_counts, "config_hash": self.config_hash,
                "source": self.source, "data_regime": self.data_regime}


class Predictor:
    """Runs tiled inference for one model (requires torch)."""

    def __init__(self, config: ModelConfig, *, device: str = "cpu", patch_size: int = 32) -> None:
        from app.models._torch import require_torch
        from app.models.factory import ModelFactory
        from app.training.seed import resolve_device
        require_torch()
        self.config = config
        self.device = resolve_device(device)
        self.patch_size = patch_size
        self.model = ModelFactory().create(config).to(self.device)
        self.model.eval()

    def load_checkpoint(self, path: Path, tag: str = "best") -> "Predictor":
        """Load model weights from an M7 checkpoint directory (best/latest tag) or a .pt file."""
        import torch
        p = Path(path)
        if p.is_dir():
            from app.training.checkpoint import CheckpointManager
            payload = CheckpointManager(p).load(tag, map_location=self.device)
        else:
            payload = torch.load(p, map_location=self.device, weights_only=False)
        state = payload.get("model_state_dict", payload) if isinstance(payload, dict) else payload
        self.model.load_state_dict(state)
        self.model.eval()
        return self

    def predict(self, image: Any, *, source: str = "", data_regime: str = "SYNTHETIC") -> PredictionResult:
        """Tiled argmax prediction over a ``(C, H, W)`` image → stitched ``(H, W)`` label map."""
        import numpy as np
        import torch

        arr = np.asarray(image, dtype="float32")
        if arr.ndim != 3:
            from app.core.exceptions import InferenceError
            raise InferenceError(f"image must be (C,H,W), got shape {arr.shape}.")
        c, h, w = arr.shape
        ps = self.patch_size
        out = np.zeros((h, w), dtype="int64")

        with torch.no_grad():
            for win in generate_patch_grid(h, w, ps, 0):
                r, cc, th, tw = win.row_off, win.col_off, win.height, win.width
                tile = arr[:, r:r + th, cc:cc + tw]
                if (th, tw) != (ps, ps):                      # pad partial edge tiles to a full patch
                    padded = np.zeros((c, ps, ps), dtype="float32")
                    padded[:, :th, :tw] = tile
                    tile = padded
                x = torch.from_numpy(tile[None]).to(self.device)
                pred = self.model(x).argmax(dim=1)[0].cpu().numpy()
                out[r:r + th, cc:cc + tw] = pred[:th, :tw]

        counts = {str(int(k)): int(v) for k, v in zip(*np.unique(out, return_counts=True))}
        return PredictionResult(
            architecture=self.config.name, num_classes=self.config.num_classes,
            input_shape=(c, h, w), output_shape=(h, w), device=self.device,
            class_pixel_counts=counts, config_hash=self.config.config_hash(), source=source,
            data_regime=data_regime)
