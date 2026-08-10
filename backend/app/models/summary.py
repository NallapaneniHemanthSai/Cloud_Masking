"""Model summary utilities (Milestone 6).

Reports parameter counts and a configuration summary for a model. Parameter counting requires PyTorch
(guarded); the :class:`ModelSummary` dataclass itself is standard-library and serialisable. No FLOP
computation in this milestone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models._torch import require_torch
from app.models.config import ModelConfig


@dataclass
class ModelSummary:
    """A serialisable summary of a model (no plotting/training objects)."""

    architecture: str
    parameter_count: int
    trainable_parameter_count: int
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "architecture": self.architecture,
            "parameter_count": self.parameter_count,
            "trainable_parameter_count": self.trainable_parameter_count,
            "config": self.config,
        }


def count_parameters(model: Any) -> tuple[int, int]:
    """Return ``(total_parameters, trainable_parameters)`` for a torch model (requires PyTorch)."""
    require_torch()
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return int(total), int(trainable)


def summarize(model: Any, config: ModelConfig, architecture: str | None = None) -> ModelSummary:
    """Build a :class:`ModelSummary` for a model + its config."""
    total, trainable = count_parameters(model)
    return ModelSummary(
        architecture=architecture or config.name,
        parameter_count=total,
        trainable_parameter_count=trainable,
        config=config.to_dict(),
    )
