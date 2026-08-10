"""Milestone 6 (revised) verification: ModelArtifact, capability metadata, initialization reports.

Synthetic models only; no training. Model-building tests require torch (skipped otherwise); metadata /
artifact / capability tests are pure-stdlib and always run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models import _torch as torch_mod
from app.models.artifact import ModelArtifact
from app.models.config import ModelConfig
from app.models.factory import ModelFactory
from app.models.initialization import InitializationReport, apply_initialization
from app.models.metadata import CheckpointMetadata, ModelMetadata
from app.models.registry import default_registry

HAS_TORCH = torch_mod.torch_available()


# ---------------------------------------------------------------------------------------------------
# ModelArtifact serialization + deterministic hashing
# ---------------------------------------------------------------------------------------------------

def _artifact() -> ModelArtifact:
    ck = CheckpointMetadata(model_id="unet-abc", architecture="unet", config_hash="cfg",
                            parameter_count=100, created_at="t")
    return ModelArtifact.create(model_id="unet-abc", architecture="unet", config_hash="cfg",
                                checkpoint_metadata=ck, dataset_version="cloudsen12-v1.1.2",
                                created_at="t", notes="baseline")


def test_artifact_id_and_content_hash_deterministic() -> None:
    a = _artifact()
    b = _artifact()
    assert a.content_hash() == b.content_hash()
    assert a.artifact_id == b.artifact_id
    assert a.artifact_id.startswith("unet-")
    # content hash ignores created_at / notes
    c = ModelArtifact.create(model_id="unet-abc", architecture="unet", config_hash="cfg",
                             checkpoint_metadata=a.checkpoint_metadata,
                             dataset_version="cloudsen12-v1.1.2", created_at="different", notes="other")
    assert c.content_hash() == a.content_hash()
    # a different config hash changes the content hash
    d = ModelArtifact.create(model_id="unet-abc", architecture="unet", config_hash="OTHER",
                             dataset_version="cloudsen12-v1.1.2")
    assert d.content_hash() != a.content_hash()


def test_artifact_json_roundtrip_and_export(tmp_path: Path) -> None:
    a = _artifact()
    restored = ModelArtifact.from_dict(a.to_dict())
    # to_dict adds a derived content_hash; identity fields must roundtrip
    assert restored.artifact_id == a.artifact_id
    assert restored.checkpoint_metadata is not None
    assert restored.checkpoint_metadata.model_id == "unet-abc"
    assert ModelArtifact.from_json(a.to_json()).content_hash() == a.content_hash()
    path = a.save_json(tmp_path / "artifact.json")
    assert ModelArtifact.load_json(path).artifact_id == a.artifact_id
    assert "content_hash" in a.to_dict()


# ---------------------------------------------------------------------------------------------------
# Capability metadata
# ---------------------------------------------------------------------------------------------------

def test_capability_metadata_defaults_and_roundtrip() -> None:
    meta = default_registry().metadata("unet")
    assert meta.supported_input_channels == [4, 13]
    assert meta.supported_output_classes == [2, 4]
    assert meta.minimum_patch_size == 16
    assert "torch" in meta.optional_dependencies
    assert "batch" in meta.supported_normalization
    assert meta.supported_preprocessing_versions  # non-empty
    # roundtrip preserves capability fields
    assert ModelMetadata.from_dict(meta.to_dict()).to_dict() == meta.to_dict()


# ---------------------------------------------------------------------------------------------------
# Initialization reporting (requires torch to build a model)
# ---------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_initialization_report_structure_and_serialization() -> None:
    cfg = ModelConfig(in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)
    model = ModelFactory().create(cfg)
    returned, report = apply_initialization(model, "xavier", return_report=True)
    assert returned is model
    assert isinstance(report, InitializationReport)
    assert report.strategy == "xavier"
    assert report.parameter_tensors_initialized > 0
    assert len(report.modules_initialized) > 0
    # conv/linear layers initialised; norm layers (e.g. BatchNorm2d) recorded as skipped
    assert len(report.skipped_modules) > 0
    d = report.to_dict()
    assert set(d) == {"strategy", "modules_initialized", "parameter_tensors_initialized",
                      "skipped_modules", "timestamp"}


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_factory_build_artifact_embeds_checkpoint() -> None:
    cfg = ModelConfig(in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)
    artifact = ModelFactory().build_artifact(cfg, dataset_version="cloudsen12-v1.1.2")
    assert artifact.architecture == "unet"
    assert artifact.checkpoint_metadata is not None
    assert artifact.checkpoint_metadata.parameter_count > 0
    assert artifact.config_hash == cfg.config_hash()
    assert artifact.artifact_id.startswith("unet-")
