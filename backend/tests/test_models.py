"""Milestone 6 verification: baseline model architecture + metadata (synthetic models only, no training).

Covers registry, metadata serialization, config hashing, checkpoint/experiment metadata, init selection,
guarded imports, and parameter counting. Model-building/param-count tests require torch (skipped otherwise).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import ConfigurationError, ModelError
from app.models import _torch as torch_mod
from app.models.config import Activation, ModelConfig, Normalization
from app.models.factory import ModelFactory
from app.models.initialization import InitStrategy, apply_initialization, get_initializer
from app.models.metadata import CheckpointMetadata, ExperimentMetadata, ModelMetadata
from app.models.registry import ModelRegistry, default_registry
from app.models.summary import ModelSummary, count_parameters

HAS_TORCH = torch_mod.torch_available()


# ---------------------------------------------------------------------------------------------------
# Config + deterministic hashing
# ---------------------------------------------------------------------------------------------------

def test_config_validation_and_channels() -> None:
    cfg = ModelConfig(in_channels=13, num_classes=4, encoder_depth=4, base_channels=32)
    assert cfg.encoder_channels() == [32, 64, 128, 256]
    assert cfg.bottleneck_channels() == 512
    with pytest.raises(ConfigurationError):
        ModelConfig(num_classes=0)
    with pytest.raises(ConfigurationError):
        ModelConfig(activation="banana")


def test_config_hash_is_deterministic() -> None:
    a = ModelConfig(in_channels=13, num_classes=4)
    b = ModelConfig(in_channels=13, num_classes=4)
    assert a.config_hash() == b.config_hash()
    assert a.config_hash() != ModelConfig(in_channels=4, num_classes=2).config_hash()
    # round-trip through dict preserves the hash
    assert ModelConfig.from_dict(a.to_dict()).config_hash() == a.config_hash()


# ---------------------------------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------------------------------

def test_default_registry_has_unet_with_aliases() -> None:
    reg = default_registry()
    assert "unet" in reg.list_models()
    assert reg.resolve("baseline") == "unet"       # alias resolution
    assert reg.has("unet2d")
    meta = reg.metadata("unet")
    assert meta.architecture == "unet" and "baseline" in meta.tags


def test_registry_register_and_duplicate() -> None:
    reg = ModelRegistry()
    reg.register("m", lambda cfg: object(), metadata=ModelMetadata("m", "m", aliases=["alt"]))
    assert reg.resolve("alt") == "m" and reg.aliases("m") == ["alt"]
    with pytest.raises(ModelError):
        reg.register("m", lambda cfg: object())
    with pytest.raises(ModelError):
        reg.resolve("missing")


# ---------------------------------------------------------------------------------------------------
# Metadata serialization
# ---------------------------------------------------------------------------------------------------

def test_model_metadata_roundtrip() -> None:
    m = ModelMetadata("unet", "unet", description="d", tags=["baseline"], aliases=["b"])
    assert ModelMetadata.from_dict(m.to_dict()).to_dict() == m.to_dict()


def test_checkpoint_metadata_roundtrip(tmp_path: Path) -> None:
    ck = CheckpointMetadata(model_id="unet-abc", architecture="unet", config_hash="h",
                            parameter_count=1234, created_at="2026-01-01T00:00:00+00:00")
    assert CheckpointMetadata.from_dict(ck.to_dict()).to_dict() == ck.to_dict()
    assert CheckpointMetadata.from_json(ck.to_json()).model_id == "unet-abc"
    p = ck.save_json(tmp_path / "ck.json")
    assert CheckpointMetadata.load_json(p).parameter_count == 1234


def test_experiment_metadata_roundtrip_with_checkpoint(tmp_path: Path) -> None:
    ck = CheckpointMetadata(model_id="unet-abc", architecture="unet", parameter_count=10,
                            created_at="t")
    exp = ExperimentMetadata(experiment_id="exp1", dataset="cloudsen12", config_hash="h",
                             checkpoint=ck, created_at="t")
    restored = ExperimentMetadata.from_dict(exp.to_dict())
    assert restored.to_dict() == exp.to_dict()
    assert restored.checkpoint is not None and restored.checkpoint.model_id == "unet-abc"
    p = exp.save_json(tmp_path / "exp.json")
    assert ExperimentMetadata.load_json(p).dataset == "cloudsen12"


# ---------------------------------------------------------------------------------------------------
# Initialization selection
# ---------------------------------------------------------------------------------------------------

def test_get_initializer_returns_callable_and_rejects_unknown() -> None:
    for strategy in (s.value for s in InitStrategy):
        assert callable(get_initializer(strategy))
    with pytest.raises(ModelError):
        get_initializer("nope")


# ---------------------------------------------------------------------------------------------------
# Guarded imports
# ---------------------------------------------------------------------------------------------------

def test_require_torch_raises_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate torch being unavailable and confirm a clear ModelError (not ImportError)."""
    monkeypatch.setattr(torch_mod, "torch", None)
    with pytest.raises(ModelError):
        torch_mod.require_torch()
    # An initializer built while "torch is None" also raises clearly when applied.
    init_fn = get_initializer("xavier")
    with pytest.raises(ModelError):
        init_fn(object())


def test_factory_create_without_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch_mod, "torch", None)
    with pytest.raises(ModelError):
        ModelFactory().create(ModelConfig())


# ---------------------------------------------------------------------------------------------------
# Parameter counting / model building (requires torch)
# ---------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_build_unet_and_count_parameters() -> None:
    cfg = ModelConfig(in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)
    factory = ModelFactory()
    model = factory.create(cfg)
    total, trainable = count_parameters(model)
    assert total > 0 and trainable == total   # nothing frozen
    summary = factory.summary(cfg)
    assert isinstance(summary, ModelSummary) and summary.parameter_count == total


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_unet_forward_shape() -> None:
    import torch
    cfg = ModelConfig(in_channels=4, num_classes=3, encoder_depth=2, base_channels=8)
    model = ModelFactory().create(cfg)
    model.eval()
    with torch.no_grad():
        out = model(torch.zeros(1, 4, 64, 64))
    assert tuple(out.shape) == (1, 3, 64, 64)   # per-class logits at input resolution


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_apply_initialization_runs() -> None:
    cfg = ModelConfig(in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)
    model = ModelFactory().create(cfg)
    assert apply_initialization(model, "kaiming") is model


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_factory_checkpoint_metadata_counts_params() -> None:
    cfg = ModelConfig(in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)
    ck = ModelFactory().checkpoint_metadata(cfg)
    assert ck.architecture == "unet" and ck.parameter_count > 0
    assert ck.config_hash == cfg.config_hash()
