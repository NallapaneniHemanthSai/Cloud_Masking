"""Milestone 10 verification: improved model (Attention U-Net) + architecture comparison.

Synthetic tensors only; no real dataset, no performance claims. Model-building/forward tests require torch
(skipped otherwise); config/registry/metadata/comparison-record tests are pure-stdlib and always run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.constants import IMPROVED_MODEL_VERSION, MODEL_VERSION
from app.models import _torch as torch_mod
from app.models.comparison import (
    DEFERRED,
    MEASURED,
    NOT_MEASURED,
    ArchitectureComparison,
    ArchitectureProfile,
)
from app.models.config import ModelConfig
from app.models.factory import ModelFactory
from app.models.metadata import ModelMetadata
from app.models.registry import default_registry

HAS_TORCH = torch_mod.torch_available()


# ---------------------------------------------------------------------------------------------------
# Registry — both architectures present; U-Net unchanged
# ---------------------------------------------------------------------------------------------------

def test_registry_has_both_architectures() -> None:
    reg = default_registry()
    assert set(reg.list_models()) == {"unet", "attention_unet"}
    assert reg.resolve("attn_unet") == "attention_unet"
    assert reg.resolve("baseline") == "unet"          # baseline alias unchanged


def test_unet_metadata_unchanged_and_improved_versioned() -> None:
    reg = default_registry()
    assert reg.metadata("unet").version == MODEL_VERSION       # baseline version not overwritten
    assert reg.metadata("unet").improvement_mechanism == []
    attn = reg.metadata("attention_unet")
    assert attn.version == IMPROVED_MODEL_VERSION and attn.improves_over == "unet"
    assert "attention_gates" in attn.improvement_mechanism


def test_model_metadata_improvement_fields_roundtrip() -> None:
    m = ModelMetadata("attention_unet", "attention_unet", version=IMPROVED_MODEL_VERSION,
                      improvement_mechanism=["attention_gates"], improves_over="unet")
    assert ModelMetadata.from_dict(m.to_dict()).to_dict() == m.to_dict()


# ---------------------------------------------------------------------------------------------------
# Config (reused ModelConfig) + deterministic hashing
# ---------------------------------------------------------------------------------------------------

def test_improved_config_reuses_model_config_and_hash_deterministic() -> None:
    a = ModelConfig(name="attention_unet", in_channels=13, num_classes=4)
    b = ModelConfig(name="attention_unet", in_channels=13, num_classes=4)
    assert a.config_hash() == b.config_hash()
    assert a.config_hash() != ModelConfig(name="unet", in_channels=13, num_classes=4).config_hash()


# ---------------------------------------------------------------------------------------------------
# Comparison records (no torch)
# ---------------------------------------------------------------------------------------------------

def test_architecture_profile_and_comparison_serialize() -> None:
    p1 = ArchitectureProfile("unet", MODEL_VERSION, 100, 100, (1, 4, 64, 64), (1, 2, 64, 64), "h1")
    p2 = ArchitectureProfile("attention_unet", IMPROVED_MODEL_VERSION, 130, 130, (1, 4, 64, 64),
                             (1, 2, 64, 64), "h2")
    assert p1.estimated_memory == NOT_MEASURED and p1.flops == DEFERRED
    assert p1.compute_measurement_status == MEASURED
    comp = ArchitectureComparison(profiles=[p1, p2], baseline="unet")
    assert comp.parameter_delta() == {"unet": 0, "attention_unet": 30}
    assert ArchitectureComparison.from_dict(comp.to_dict()).parameter_delta() == comp.parameter_delta()
    assert "NOT YET MEASURED" in comp.notes


# ---------------------------------------------------------------------------------------------------
# Torch: forward, params, factory, artifact, comparison profiling, baseline regression
# ---------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_attention_unet_forward_shape() -> None:
    import torch
    cfg = ModelConfig(name="attention_unet", in_channels=4, num_classes=3, encoder_depth=2, base_channels=8)
    model = ModelFactory().create(cfg)
    model.eval()
    with torch.no_grad():
        out = model(torch.zeros(2, 4, 64, 64))
    assert tuple(out.shape) == (2, 3, 64, 64)


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_baseline_unet_regression_param_count() -> None:
    from app.models import count_parameters
    # Same config as M6 test → must still be exactly 29,706 (refactor preserved behaviour).
    cfg = ModelConfig(in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)
    total, _ = count_parameters(ModelFactory().create(cfg))
    assert total == 29706


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_attention_unet_has_more_params_than_unet() -> None:
    from app.models import count_parameters
    base = count_parameters(ModelFactory().create(
        ModelConfig(name="unet", in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)))[0]
    attn = count_parameters(ModelFactory().create(
        ModelConfig(name="attention_unet", in_channels=4, num_classes=2, encoder_depth=2,
                    base_channels=8)))[0]
    assert attn > base   # attention gates add a modest number of parameters


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_factory_artifact_records_improved_version() -> None:
    cfg = ModelConfig(name="attention_unet", in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)
    artifact = ModelFactory().build_artifact(cfg, dataset_version="cloudsen12-v1.1.2")
    assert artifact.architecture == "attention_unet"
    assert artifact.model_version == IMPROVED_MODEL_VERSION
    assert artifact.checkpoint_metadata.parameter_count > 0
    assert artifact.config_hash == cfg.config_hash()


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_profile_and_compare_measure_shapes(tmp_path: Path) -> None:
    from app.models.comparison import compare_architectures, profile_architecture
    cfg = ModelConfig(name="attention_unet", in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)
    prof = profile_architecture(cfg, (1, 4, 32, 32))
    assert prof.output_shape == (1, 2, 32, 32) and prof.parameter_count > 0
    assert prof.estimated_memory == NOT_MEASURED and prof.flops == DEFERRED   # not fabricated

    comp = compare_architectures(
        [ModelConfig(name="unet", in_channels=4, num_classes=2, encoder_depth=2, base_channels=8), cfg],
        (1, 4, 32, 32))
    delta = comp.parameter_delta()
    assert delta["unet"] == 0 and delta["attention_unet"] > 0


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_deterministic_construction() -> None:
    from app.models import count_parameters
    cfg = ModelConfig(name="attention_unet", in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)
    a = count_parameters(ModelFactory().create(cfg))[0]
    b = count_parameters(ModelFactory().create(cfg))[0]
    assert a == b   # construction is deterministic given the config
