"""Model configuration (Milestone 6).

Strongly-typed, validated, serialisable model configuration with a deterministic config hash. Standard-
library only — importable without PyTorch. No training/optimisation parameters live here.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import ConfigurationError
from app.utils.hashing import stable_hash


class Activation(str, enum.Enum):
    """Supported activation functions."""

    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    GELU = "gelu"
    ELU = "elu"


class Normalization(str, enum.Enum):
    """Supported normalization layers."""

    BATCH = "batch"
    GROUP = "group"
    INSTANCE = "instance"
    NONE = "none"


@dataclass(frozen=True)
class ModelConfig:
    """Validated segmentation-model configuration.

    Attributes:
        name: Registered architecture name (e.g. ``"unet"``).
        in_channels: Number of input channels (e.g. 13 for CloudSEN12 L1C, 4 for On Cloud N).
        num_classes: Number of output classes (e.g. 4 for CloudSEN12 multi-class).
        encoder_depth: Number of downsampling stages (> 0).
        base_channels: Channel count of the first encoder stage (doubles each stage).
        activation: Activation function name (:class:`Activation`).
        normalization: Normalization layer name (:class:`Normalization`).
        dropout: Dropout probability in [0, 1).
        group_norm_groups: Groups for group-norm (used only when normalization == group).
    """

    name: str = "unet"
    in_channels: int = 13
    num_classes: int = 4
    encoder_depth: int = 4
    base_channels: int = 32
    activation: str = Activation.RELU.value
    normalization: str = Normalization.BATCH.value
    dropout: float = 0.0
    group_norm_groups: int = 8

    def __post_init__(self) -> None:
        if self.in_channels <= 0:
            raise ConfigurationError(f"in_channels must be > 0, got {self.in_channels}.")
        if self.num_classes <= 0:
            raise ConfigurationError(f"num_classes must be > 0, got {self.num_classes}.")
        if self.encoder_depth <= 0:
            raise ConfigurationError(f"encoder_depth must be > 0, got {self.encoder_depth}.")
        if self.base_channels <= 0:
            raise ConfigurationError(f"base_channels must be > 0, got {self.base_channels}.")
        if not (0.0 <= self.dropout < 1.0):
            raise ConfigurationError(f"dropout must be in [0, 1), got {self.dropout}.")
        if self.activation not in {a.value for a in Activation}:
            raise ConfigurationError(f"Unknown activation {self.activation!r}.")
        if self.normalization not in {n.value for n in Normalization}:
            raise ConfigurationError(f"Unknown normalization {self.normalization!r}.")

    def encoder_channels(self) -> list[int]:
        """Channel counts for each encoder stage (excludes the bottleneck)."""
        return [self.base_channels * (2 ** i) for i in range(self.encoder_depth)]

    def bottleneck_channels(self) -> int:
        """Channel count of the bottleneck (deepest) block."""
        return self.base_channels * (2 ** self.encoder_depth)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "in_channels": self.in_channels,
            "num_classes": self.num_classes,
            "encoder_depth": self.encoder_depth,
            "base_channels": self.base_channels,
            "activation": self.activation,
            "normalization": self.normalization,
            "dropout": self.dropout,
            "group_norm_groups": self.group_norm_groups,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelConfig":
        allowed = {f for f in cls().to_dict()}
        return cls(**{k: v for k, v in (data or {}).items() if k in allowed})

    def config_hash(self) -> str:
        """Deterministic hash of the configuration."""
        return stable_hash(self.to_dict())
