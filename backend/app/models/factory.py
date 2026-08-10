"""Model factory (Milestone 6).

Builds models from a :class:`ModelConfig` via a :class:`ModelRegistry`, and produces model/checkpoint
metadata. Building a model requires PyTorch (guarded); registry lookup and config hashing do not. No
training/optimisation code.
"""

from __future__ import annotations

from typing import Any

from app.models._torch import require_torch
from app.models.artifact import ModelArtifact
from app.models.config import ModelConfig
from app.models.metadata import CheckpointMetadata
from app.models.registry import ModelRegistry, default_registry
from app.models.summary import ModelSummary, summarize


class ModelFactory:
    """Creates models and derives their metadata from a registry."""

    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry or default_registry()

    def create(self, config: ModelConfig) -> Any:
        """Instantiate a model for ``config`` (requires PyTorch)."""
        require_torch()
        entry = self.registry.get(config.name)
        return entry.builder(config)

    def summary(self, config: ModelConfig) -> ModelSummary:
        """Build a model and return its :class:`ModelSummary` (requires PyTorch)."""
        model = self.create(config)
        return summarize(model, config, architecture=self.registry.resolve(config.name))

    def checkpoint_metadata(self, config: ModelConfig, *, model_id: str | None = None,
                            notes: str = "") -> CheckpointMetadata:
        """Build :class:`CheckpointMetadata` for ``config`` (counts params; requires PyTorch).

        No weights are saved — only metadata is produced.
        """
        summary = self.summary(config)
        architecture = self.registry.resolve(config.name)
        return CheckpointMetadata(
            model_id=model_id or f"{architecture}-{config.config_hash()[:8]}",
            architecture=architecture,
            config_hash=config.config_hash(),
            parameter_count=summary.parameter_count,
            notes=notes,
        )

    def build_artifact(self, config: ModelConfig, *, dataset_version: str = "",
                       notes: str = "") -> ModelArtifact:
        """Build a :class:`ModelArtifact` (canonical saved-model metadata; no weights) for ``config``.

        Requires PyTorch (the embedded checkpoint metadata counts parameters).
        """
        checkpoint = self.checkpoint_metadata(config)
        return ModelArtifact.create(
            model_id=checkpoint.model_id, architecture=checkpoint.architecture,
            config_hash=config.config_hash(), checkpoint_metadata=checkpoint,
            dataset_version=dataset_version, notes=notes,
        )
