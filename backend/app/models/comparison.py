"""Architecture comparison records (Milestone 10).

Typed, serialisable profiles + comparisons of architectures — **parameters and shapes are MEASURED**
(by building the model and running a synthetic forward pass); **memory and FLOPs are NOT MEASURED /
DEFERRED** and are never fabricated (ADR-0010). The dataclasses are standard-library; profiling requires
PyTorch (guarded).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.models._torch import require_torch
from app.models.config import ModelConfig
from app.models.summary import count_parameters

# Measurement-status labels (honest reporting).
MEASURED = "MEASURED"
NOT_MEASURED = "NOT_MEASURED"
DEFERRED = "DEFERRED"


@dataclass
class ArchitectureProfile:
    """A measured profile of one architecture at a given input shape."""

    architecture: str
    version: str
    parameter_count: int
    trainable_parameter_count: int
    input_shape: tuple[int, ...]
    output_shape: tuple[int, ...] | None
    config_hash: str
    estimated_memory: str = NOT_MEASURED        # not fabricated
    flops: str = DEFERRED                        # deferred (no reliable dependency-light method yet)
    compute_measurement_status: str = MEASURED   # params/shapes are measured
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "architecture": self.architecture, "version": self.version,
            "parameter_count": self.parameter_count,
            "trainable_parameter_count": self.trainable_parameter_count,
            "input_shape": list(self.input_shape),
            "output_shape": list(self.output_shape) if self.output_shape else None,
            "config_hash": self.config_hash, "estimated_memory": self.estimated_memory,
            "flops": self.flops, "compute_measurement_status": self.compute_measurement_status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ArchitectureProfile":
        out = d.get("output_shape")
        return cls(
            architecture=d["architecture"], version=d.get("version", ""),
            parameter_count=int(d["parameter_count"]),
            trainable_parameter_count=int(d["trainable_parameter_count"]),
            input_shape=tuple(d["input_shape"]),
            output_shape=tuple(out) if out else None,
            config_hash=d.get("config_hash", ""),
            estimated_memory=d.get("estimated_memory", NOT_MEASURED),
            flops=d.get("flops", DEFERRED),
            compute_measurement_status=d.get("compute_measurement_status", MEASURED),
            notes=d.get("notes", ""),
        )


@dataclass
class ArchitectureComparison:
    """A comparison of two or more :class:`ArchitectureProfile`s."""

    profiles: list[ArchitectureProfile] = field(default_factory=list)
    baseline: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = "Parameters/shapes MEASURED; memory NOT_MEASURED; FLOPs DEFERRED. Performance NOT YET MEASURED."

    def parameter_delta(self) -> dict[str, int | None]:
        """Parameter count of each architecture relative to the baseline (absolute delta)."""
        base = next((p for p in self.profiles if p.architecture == self.baseline), None)
        if base is None:
            return {p.architecture: None for p in self.profiles}
        return {p.architecture: p.parameter_count - base.parameter_count for p in self.profiles}

    def to_dict(self) -> dict[str, Any]:
        return {
            "profiles": [p.to_dict() for p in self.profiles],
            "baseline": self.baseline,
            "parameter_delta": self.parameter_delta(),
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ArchitectureComparison":
        return cls(
            profiles=[ArchitectureProfile.from_dict(p) for p in d.get("profiles", [])],
            baseline=d.get("baseline", ""), created_at=d.get("created_at", ""),
            notes=d.get("notes", ""),
        )


def profile_architecture(config: ModelConfig, input_shape: tuple[int, int, int, int],
                         *, registry: Any = None) -> ArchitectureProfile:
    """Build the model and MEASURE its parameters + output shape via a synthetic forward pass.

    Args:
        config: Model configuration (its ``name`` selects the architecture).
        input_shape: ``(B, C, H, W)`` synthetic input.
        registry: Optional registry (defaults to the project default registry).

    Requires PyTorch. Memory is NOT measured and FLOPs are DEFERRED (never fabricated).
    """
    torch, _ = require_torch()
    from app.models.factory import ModelFactory

    factory = ModelFactory(registry) if registry is not None else ModelFactory()
    architecture = factory.registry.resolve(config.name)
    version = factory.registry.metadata(architecture).version
    model = factory.create(config)
    model.eval()

    total, trainable = count_parameters(model)
    with torch.no_grad():
        output = model(torch.zeros(*input_shape))
    return ArchitectureProfile(
        architecture=architecture, version=version, parameter_count=total,
        trainable_parameter_count=trainable, input_shape=tuple(input_shape),
        output_shape=tuple(output.shape), config_hash=config.config_hash())


def compare_architectures(configs: list[ModelConfig], input_shape: tuple[int, int, int, int],
                          *, baseline: str = "unet", registry: Any = None) -> ArchitectureComparison:
    """Profile several architectures at the same input shape and return a comparison."""
    profiles = [profile_architecture(cfg, input_shape, registry=registry) for cfg in configs]
    return ArchitectureComparison(profiles=profiles, baseline=baseline)
