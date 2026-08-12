"""Segmentation models (Milestone 6) — baseline architecture + metadata infrastructure.

Reusable, strongly-typed model abstractions designed to plug into training and inference later **without
modification** — no training/optimisation/loss/evaluation/inference code lives here. PyTorch is a guarded
optional dependency: the package imports on a bare interpreter, and model construction raises a clear
:class:`app.core.exceptions.ModelError` when torch is absent.

Public surface:

* Config: :class:`ModelConfig`, :class:`Activation`, :class:`Normalization`.
* Metadata: :class:`ModelMetadata`, :class:`CheckpointMetadata`, :class:`ExperimentMetadata`,
  :class:`ModelSummary`.
* Registry/factory: :class:`ModelRegistry`, :func:`default_registry`, :class:`ModelFactory`.
* Architectures: :func:`build_unet` (baseline), :func:`build_attention_unet` (improved, M10).
* Comparison: :class:`ArchitectureProfile`, :class:`ArchitectureComparison`, :func:`profile_architecture`,
  :func:`compare_architectures`.
* Initialization: :class:`InitStrategy`, :func:`get_initializer`, :func:`apply_initialization`.
* Utilities: :func:`count_parameters`, :func:`summarize`, :func:`torch_available`.
"""

from app.models._torch import torch_available
from app.models.artifact import ModelArtifact
from app.models.attention_unet import build_attention_unet
from app.models.comparison import (
    ArchitectureComparison,
    ArchitectureProfile,
    compare_architectures,
    profile_architecture,
)
from app.models.config import Activation, ModelConfig, Normalization
from app.models.factory import ModelFactory
from app.models.initialization import (
    InitializationReport,
    InitStrategy,
    apply_initialization,
    get_initializer,
    is_initializable,
)
from app.models.metadata import (
    CheckpointMetadata,
    ExperimentMetadata,
    ModelMetadata,
)
from app.models.registry import ModelRegistry, RegistryEntry, default_registry
from app.models.summary import ModelSummary, count_parameters, summarize
from app.models.unet import build_unet

__all__ = [
    "ModelConfig",
    "Activation",
    "Normalization",
    "ModelMetadata",
    "CheckpointMetadata",
    "ExperimentMetadata",
    "ModelArtifact",
    "ModelSummary",
    "ModelRegistry",
    "RegistryEntry",
    "default_registry",
    "ModelFactory",
    "build_unet",
    "build_attention_unet",
    "ArchitectureProfile",
    "ArchitectureComparison",
    "profile_architecture",
    "compare_architectures",
    "InitStrategy",
    "InitializationReport",
    "get_initializer",
    "apply_initialization",
    "is_initializable",
    "count_parameters",
    "summarize",
    "torch_available",
]
