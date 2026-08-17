"""Controlled-comparison configuration (Milestone 11).

:class:`ComparisonConfig` is the **single source of truth** for a controlled baseline-vs-improved
comparison. It holds every *shared* experiment control (dataset / preprocessing / split / training /
evaluation) exactly once, plus the two :class:`ModelConfig`s — the architecture being the **only**
intentional difference. Per-model :class:`ExperimentPlan`s are *derived* from this one object, so both
models are guaranteed to receive identical controls by construction (the fairness guardrails then re-check
this). Standard-library only — importable without PyTorch. Deterministic config + fairness hashes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import (
    COMPARISON_VERSION,
    DEFAULT_NORMALIZATION_MODE,
    DEFAULT_PATCH_SIZE,
    PREPROCESSING_VERSION,
)
from app.core.exceptions import ConfigurationError
from app.evaluation.config import CLOUDSEN12_CLASS_NAMES, EvaluationConfig
from app.failure_analysis.config import FailureAnalysisConfig
from app.models.config import ModelConfig
from app.training.config import TrainingConfig
from app.utils.hashing import stable_hash

#: Default intended seed matrix (section 19). Rows are only *run* when compute/data permit.
DEFAULT_SEEDS: tuple[int, ...] = (1, 2, 3)


@dataclass(frozen=True)
class ExperimentPlan:
    """A fully-resolved plan for **one** model in the comparison (one arm of one seed row).

    Built by :meth:`ComparisonConfig.plan_for`; both arms share every field except ``model`` (the
    intentional difference) and the per-experiment identifiers (``experiment_name`` / ``model_id``).
    """

    label: str                       # "baseline" | "improved"
    seed: int
    model: ModelConfig
    training: TrainingConfig
    evaluation: EvaluationConfig
    failure: FailureAnalysisConfig

    @property
    def experiment_name(self) -> str:
        return self.training.experiment_name

    @property
    def model_id(self) -> str:
        return self.evaluation.model_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label, "seed": self.seed, "model": self.model.to_dict(),
            "training": self.training.to_dict(), "evaluation": self.evaluation.to_dict(),
            "failure": self.failure.to_dict(),
        }

    def fairness_signature(self) -> dict[str, Any]:
        """The shared controls that MUST match the paired arm (excludes model + identifiers).

        Deliberately omits ``model`` (the intended difference), ``training.experiment_name`` /
        ``evaluation.model_id`` / ``failure.model_id`` (per-arm identifiers) and the per-experiment
        output directories (``checkpoint.dir`` / ``logging.dir``) which never affect learning.
        """
        t = self.training.to_dict()
        e = self.evaluation.to_dict()
        f = self.failure.to_dict()
        for identity_key in ("experiment_name",):
            t.pop(identity_key, None)
        t.get("checkpoint", {}).pop("dir", None)
        t.get("logging", {}).pop("dir", None)
        e.pop("model_id", None)
        f.pop("model_id", None)
        return {"seed": self.seed, "training": t, "evaluation": e, "failure": f}


@dataclass(frozen=True)
class ComparisonConfig:
    """Shared experiment controls + the two architectures (architecture is the ONLY difference)."""

    comparison_name: str = "unet_vs_attention_unet"

    # --- shared dataset / preprocessing controls (must match across both arms) ---------------------
    dataset: str = "cloudsen12"
    dataset_version: str = ""                     # e.g. patch-manifest hash / dataset release id
    preprocessing_version: str = PREPROCESSING_VERSION
    patch_size: int = DEFAULT_PATCH_SIZE
    normalization: str = DEFAULT_NORMALIZATION_MODE
    augmentation: tuple[str, ...] = ()            # ordered augmentation ops (empty = none)
    split: str = "test"                           # evaluation split
    split_id: str = ""                            # deterministic split identifier / hash
    training_budget: str = ""                     # human-readable budget (e.g. "10 epochs")

    # --- shared training + evaluation configs (reused verbatim from M7 / M8) -----------------------
    training: TrainingConfig = field(default_factory=TrainingConfig)
    evaluation: EvaluationConfig = field(
        default_factory=lambda: EvaluationConfig.cloudsen12(split="test"))
    top_k: int = 5                                # failure-analysis top-K (shared)

    # --- the two architectures (the ONLY intentional difference) ----------------------------------
    baseline_model: ModelConfig = field(default_factory=lambda: ModelConfig(name="unet"))
    improved_model: ModelConfig = field(default_factory=lambda: ModelConfig(name="attention_unet"))

    # --- intended experiment matrix (section 19) --------------------------------------------------
    seeds: tuple[int, ...] = DEFAULT_SEEDS

    comparison_version: str = COMPARISON_VERSION
    params: dict[str, Any] = field(default_factory=dict)

    # --- validation -------------------------------------------------------------------------------
    def __post_init__(self) -> None:
        if self.patch_size <= 0:
            raise ConfigurationError(f"patch_size must be > 0, got {self.patch_size}.")
        if not self.seeds:
            raise ConfigurationError("seeds must contain at least one seed.")
        if self.baseline_model.config_hash() == self.improved_model.config_hash():
            raise ConfigurationError(
                "baseline and improved models are identical — a comparison needs an architectural "
                "difference (their config hashes match).")
        for label, m in (("baseline", self.baseline_model), ("improved", self.improved_model)):
            if m.in_channels != self.baseline_model.in_channels:
                raise ConfigurationError(f"{label} in_channels must match across arms (fair task).")
            if m.num_classes != self.evaluation.num_classes:
                raise ConfigurationError(
                    f"{label} num_classes ({m.num_classes}) must match evaluation "
                    f"num_classes ({self.evaluation.num_classes}).")

    # --- derivation: one source -> two identical-except-architecture plans -------------------------
    def _class_names(self) -> tuple[str, ...]:
        names = self.evaluation.class_names
        return tuple(names) if names else CLOUDSEN12_CLASS_NAMES

    def training_config_for(self, model: ModelConfig, *, seed: int,
                            experiment_name: str) -> TrainingConfig:
        """Derive a per-arm :class:`TrainingConfig` — identical to ``self.training`` except name/seed."""
        data = self.training.to_dict()
        data["experiment_name"] = experiment_name
        data["seed"] = seed
        return TrainingConfig.from_dict(data)

    def evaluation_config_for(self, model_id: str) -> EvaluationConfig:
        """Derive a per-arm :class:`EvaluationConfig` — identical to ``self.evaluation`` except model_id."""
        data = self.evaluation.to_dict()
        data["model_id"] = model_id
        data["split"] = self.split
        return EvaluationConfig.from_dict(data)

    def failure_config_for(self, model_id: str) -> FailureAnalysisConfig:
        """Derive a per-arm :class:`FailureAnalysisConfig` sharing the comparison controls."""
        return FailureAnalysisConfig(
            dataset=self.dataset, split=self.split,
            mode=self.evaluation.mode, class_names=self._class_names(),
            model_id=model_id, top_k=self.top_k, ignore_index=self.evaluation.ignore_index)

    def plan_for(self, arm: str, *, seed: int | None = None) -> ExperimentPlan:
        """Build the fully-resolved :class:`ExperimentPlan` for ``arm`` ('baseline' | 'improved')."""
        if arm == "baseline":
            model = self.baseline_model
        elif arm == "improved":
            model = self.improved_model
        else:
            raise ConfigurationError(f"arm must be 'baseline' or 'improved', got {arm!r}.")
        used_seed = self.training.seed if seed is None else seed
        experiment_name = f"{self.comparison_name}-{arm}-s{used_seed}"
        model_id = f"{model.name}-{model.config_hash()[:8]}-s{used_seed}"
        return ExperimentPlan(
            label=arm, seed=used_seed, model=model,
            training=self.training_config_for(model, seed=used_seed, experiment_name=experiment_name),
            evaluation=self.evaluation_config_for(model_id),
            failure=self.failure_config_for(model_id))

    def plans(self, *, seed: int | None = None) -> tuple[ExperimentPlan, ExperimentPlan]:
        """The (baseline, improved) plan pair for one seed row."""
        return self.plan_for("baseline", seed=seed), self.plan_for("improved", seed=seed)

    # --- serialisation + hashing ------------------------------------------------------------------
    def shared_controls(self) -> dict[str, Any]:
        """All fairness-relevant shared controls (excludes the two model configs)."""
        t = self.training.to_dict()
        t.pop("experiment_name", None)          # per-arm identifier, not a fairness control
        t.get("checkpoint", {}).pop("dir", None)
        t.get("logging", {}).pop("dir", None)
        e = self.evaluation.to_dict()
        e.pop("model_id", None)
        return {
            "dataset": self.dataset, "dataset_version": self.dataset_version,
            "preprocessing_version": self.preprocessing_version, "patch_size": self.patch_size,
            "normalization": self.normalization, "augmentation": list(self.augmentation),
            "split": self.split, "split_id": self.split_id, "training_budget": self.training_budget,
            "training": t, "evaluation": e, "top_k": self.top_k,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_name": self.comparison_name,
            "dataset": self.dataset, "dataset_version": self.dataset_version,
            "preprocessing_version": self.preprocessing_version, "patch_size": self.patch_size,
            "normalization": self.normalization, "augmentation": list(self.augmentation),
            "split": self.split, "split_id": self.split_id, "training_budget": self.training_budget,
            "training": self.training.to_dict(), "evaluation": self.evaluation.to_dict(),
            "top_k": self.top_k,
            "baseline_model": self.baseline_model.to_dict(),
            "improved_model": self.improved_model.to_dict(),
            "seeds": list(self.seeds), "comparison_version": self.comparison_version,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ComparisonConfig":
        data = dict(data or {})
        aug = data.get("augmentation")
        return cls(
            comparison_name=data.get("comparison_name", "unet_vs_attention_unet"),
            dataset=data.get("dataset", "cloudsen12"),
            dataset_version=data.get("dataset_version", ""),
            preprocessing_version=data.get("preprocessing_version", PREPROCESSING_VERSION),
            patch_size=int(data.get("patch_size", DEFAULT_PATCH_SIZE)),
            normalization=data.get("normalization", DEFAULT_NORMALIZATION_MODE),
            augmentation=tuple(aug) if aug else (),
            split=data.get("split", "test"), split_id=data.get("split_id", ""),
            training_budget=data.get("training_budget", ""),
            training=TrainingConfig.from_dict(data.get("training") or {}),
            evaluation=(EvaluationConfig.from_dict(data["evaluation"])
                        if data.get("evaluation") else EvaluationConfig.cloudsen12(split="test")),
            top_k=int(data.get("top_k", 5)),
            baseline_model=(ModelConfig.from_dict(data["baseline_model"])
                            if data.get("baseline_model") else ModelConfig(name="unet")),
            improved_model=(ModelConfig.from_dict(data["improved_model"])
                            if data.get("improved_model") else ModelConfig(name="attention_unet")),
            seeds=tuple(data.get("seeds") or DEFAULT_SEEDS),
            comparison_version=data.get("comparison_version", COMPARISON_VERSION),
            params=dict(data.get("params", {}) or {}),
        )

    def fairness_hash(self) -> str:
        """Deterministic hash of the **shared** controls only (identical for both arms)."""
        return stable_hash(self.shared_controls())

    def config_hash(self) -> str:
        """Deterministic hash of the whole comparison (shared controls + both architectures + seeds)."""
        return stable_hash({
            "shared": self.shared_controls(),
            "baseline_model": self.baseline_model.to_dict(),
            "improved_model": self.improved_model.to_dict(),
            "seeds": list(self.seeds),
        })

    # --- factory ----------------------------------------------------------------------------------
    @classmethod
    def cloudsen12(cls, *, baseline: str = "unet", improved: str = "attention_unet",
                   in_channels: int = 13, num_classes: int = 4, patch_size: int = DEFAULT_PATCH_SIZE,
                   encoder_depth: int = 4, base_channels: int = 32, epochs: int = 10,
                   batch_size: int = 8, device: str = "auto", seed: int = 42,
                   **kwargs: Any) -> "ComparisonConfig":
        """Build a standard CloudSEN12 U-Net vs Attention U-Net comparison config."""
        def m(name: str) -> ModelConfig:
            return ModelConfig(name=name, in_channels=in_channels, num_classes=num_classes,
                               encoder_depth=encoder_depth, base_channels=base_channels)
        training = TrainingConfig(experiment_name="comparison", epochs=epochs, batch_size=batch_size,
                                  device=device, seed=seed)
        evaluation = EvaluationConfig.cloudsen12(split=kwargs.pop("split", "test"))
        return cls(baseline_model=m(baseline), improved_model=m(improved), patch_size=patch_size,
                   training=training, evaluation=evaluation, training_budget=f"{epochs} epochs", **kwargs)
