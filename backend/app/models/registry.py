"""Model registry (Milestone 6).

Maps architecture names (and aliases) to builder callables + descriptive metadata. Registration, lookup,
metadata, aliases, version, and tags are supported. Holds **no training state** and does not itself require
PyTorch (builders do, when invoked). Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.core.constants import IMPROVED_MODEL_VERSION, PREPROCESSING_VERSION
from app.core.exceptions import ModelError
from app.models.config import ModelConfig, Normalization
from app.models.metadata import ModelMetadata

ModelBuilder = Callable[[ModelConfig], Any]


@dataclass
class RegistryEntry:
    """A single registered architecture."""

    name: str
    builder: ModelBuilder
    metadata: ModelMetadata


class ModelRegistry:
    """Registry of architecture name/alias -> builder + metadata."""

    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}
        self._aliases: dict[str, str] = {}

    def register(self, name: str, builder: ModelBuilder, *,
                 metadata: ModelMetadata | None = None,
                 aliases: list[str] | None = None, overwrite: bool = False) -> None:
        """Register an architecture with optional metadata and aliases."""
        if not overwrite and name in self._entries:
            raise ModelError(f"Model '{name}' is already registered.")
        meta = metadata or ModelMetadata(name=name, architecture=name, aliases=list(aliases or []))
        self._entries[name] = RegistryEntry(name=name, builder=builder, metadata=meta)
        for alias in list(aliases or []) + list(meta.aliases):
            if alias and alias != name:
                self._aliases[alias] = name

    def resolve(self, name: str) -> str:
        """Resolve an alias to its canonical registered name."""
        if name in self._entries:
            return name
        if name in self._aliases:
            return self._aliases[name]
        raise ModelError(f"Unknown model '{name}'. Registered: {self.list_models()}.")

    def get(self, name: str) -> RegistryEntry:
        return self._entries[self.resolve(name)]

    def has(self, name: str) -> bool:
        return name in self._entries or name in self._aliases

    def metadata(self, name: str) -> ModelMetadata:
        return self.get(name).metadata

    def aliases(self, name: str) -> list[str]:
        canonical = self.resolve(name)
        return sorted(a for a, target in self._aliases.items() if target == canonical)

    def list_models(self) -> list[str]:
        return sorted(self._entries)


def default_registry() -> ModelRegistry:
    """Return a registry pre-populated with the baseline + improved architectures."""
    # Imported here so the registry module itself never requires torch to import.
    from app.models.attention_unet import build_attention_unet
    from app.models.unet import build_unet

    norm_values = [n.value for n in Normalization]
    registry = ModelRegistry()
    registry.register(
        "unet", build_unet,
        metadata=ModelMetadata(
            name="unet", architecture="unet",
            description="Baseline U-Net (encoder/decoder/head) for multi-class cloud segmentation.",
            tags=["baseline", "segmentation", "cnn"],
            aliases=["baseline", "unet2d"],
            # Capability metadata (validated/recommended values; empty would mean unconstrained).
            supported_input_channels=[4, 13],       # On Cloud N (4) / CloudSEN12 L1C (13)
            supported_output_classes=[2, 4],         # binary / multi-class
            minimum_patch_size=16,                   # 2**encoder_depth for the default depth (4)
            optional_dependencies=["torch"],
            supported_normalization=norm_values,
            supported_preprocessing_versions=[PREPROCESSING_VERSION],
        ),
    )
    registry.register(
        "attention_unet", build_attention_unet,
        metadata=ModelMetadata(
            name="attention_unet", architecture="attention_unet",
            version=IMPROVED_MODEL_VERSION,        # separate version; does not overwrite the baseline
            description="Improved Attention U-Net: attention gates re-weight skip features by relevance.",
            tags=["improved", "attention", "segmentation", "cnn"],
            aliases=["attn_unet", "aunet"],
            supported_input_channels=[4, 13],
            supported_output_classes=[2, 4],
            minimum_patch_size=16,
            optional_dependencies=["torch"],
            supported_normalization=norm_values,
            supported_preprocessing_versions=[PREPROCESSING_VERSION],
            # Improvement metadata (why it is EXPECTED to improve — not a performance claim).
            improvement_mechanism=["attention_gates", "relevance_weighted_skip_features"],
            improves_over="unet",
        ),
    )
    return registry
