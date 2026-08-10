"""Base segmentation-model abstraction (Milestone 6).

Defines the common interface all baseline/segmentation models implement so they can later plug into
training and inference without modification. PyTorch is a guarded dependency: when it is unavailable, the
base class raises a clear :class:`ModelError` on construction instead of failing at import time. No
training/optimisation code.
"""

from __future__ import annotations

from app.models._torch import TORCH_AVAILABLE, nn, require_torch
from app.models.config import ModelConfig
from app.models.summary import count_parameters

if TORCH_AVAILABLE:  # real base class only when torch is present

    class BaseSegmentationModel(nn.Module):  # type: ignore[misc]
        """Abstract base for segmentation models (channels-first, logits output)."""

        architecture_name: str = "base"

        def __init__(self, config: ModelConfig) -> None:
            super().__init__()
            self.config = config

        def forward(self, x):  # noqa: ANN001, ANN201 - torch tensors
            raise NotImplementedError("Subclasses must implement forward().")

        def num_parameters(self, trainable_only: bool = False) -> int:
            """Total (or trainable) parameter count."""
            total, trainable = count_parameters(self)
            return trainable if trainable_only else total

else:  # pragma: no cover - exercised only without torch

    class BaseSegmentationModel:  # type: ignore[no-redef]
        """Placeholder that raises a clear error when torch is unavailable."""

        architecture_name: str = "base"

        def __init__(self, *args, **kwargs) -> None:
            require_torch()
