"""Training configuration (Milestone 7).

Strongly-typed, validated, serialisable training configuration with a deterministic config hash. Standard-
library only — importable without PyTorch. Configuration-driven: optimizer/scheduler/loss/checkpoint/
logging behaviour is selected here, never hardcoded in the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import DEFAULT_RANDOM_SEED
from app.core.exceptions import ConfigurationError
from app.utils.hashing import stable_hash


@dataclass(frozen=True)
class OptimizerConfig:
    name: str = "adamw"          # adam | adamw | sgd
    lr: float = 1e-3
    weight_decay: float = 1e-4
    momentum: float = 0.9        # sgd only
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "lr": self.lr, "weight_decay": self.weight_decay,
                "momentum": self.momentum, "params": self.params}


@dataclass(frozen=True)
class SchedulerConfig:
    name: str = "cosine"         # cosine | step | plateau | none
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "params": self.params}


@dataclass(frozen=True)
class LossConfig:
    name: str = "cross_entropy"  # cross_entropy | dice | dice_ce
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "params": self.params}


@dataclass(frozen=True)
class EarlyStoppingConfig:
    enabled: bool = False
    monitor: str = "train_loss"
    mode: str = "min"            # min | max
    patience: int = 10
    min_delta: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "monitor": self.monitor, "mode": self.mode,
                "patience": self.patience, "min_delta": self.min_delta}


@dataclass(frozen=True)
class CheckpointConfig:
    dir: str = "checkpoints"
    monitor: str = "train_loss"
    mode: str = "min"            # min | max
    save_best: bool = True
    save_latest: bool = True
    save_every: int = 0          # 0 = never (periodic)
    save_weights: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"dir": self.dir, "monitor": self.monitor, "mode": self.mode,
                "save_best": self.save_best, "save_latest": self.save_latest,
                "save_every": self.save_every, "save_weights": self.save_weights}


@dataclass(frozen=True)
class LoggingConfig:
    dir: str = "logs"
    formats: tuple[str, ...] = ("json", "csv")
    console: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"dir": self.dir, "formats": list(self.formats), "console": self.console}


@dataclass(frozen=True)
class TrainingConfig:
    """Top-level training configuration (aggregates the sub-configs)."""

    experiment_name: str = "baseline"
    epochs: int = 10
    batch_size: int = 8
    grad_accum_steps: int = 1
    device: str = "auto"
    seed: int = DEFAULT_RANDOM_SEED
    deterministic: bool = False
    mixed_precision: bool = False
    init_strategy: str | None = None       # weight init applied by the trainer at setup
    max_grad_norm: float | None = None
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    loss: LossConfig = field(default_factory=LossConfig)
    early_stopping: EarlyStoppingConfig = field(default_factory=EarlyStoppingConfig)
    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def __post_init__(self) -> None:
        if self.epochs <= 0:
            raise ConfigurationError(f"epochs must be > 0, got {self.epochs}.")
        if self.grad_accum_steps <= 0:
            raise ConfigurationError(f"grad_accum_steps must be > 0, got {self.grad_accum_steps}.")
        if self.optimizer.lr <= 0:
            raise ConfigurationError(f"optimizer.lr must be > 0, got {self.optimizer.lr}.")
        for label, mode in (("early_stopping", self.early_stopping.mode),
                            ("checkpoint", self.checkpoint.mode)):
            if mode not in {"min", "max"}:
                raise ConfigurationError(f"{label}.mode must be 'min' or 'max', got {mode!r}.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_name": self.experiment_name,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "grad_accum_steps": self.grad_accum_steps,
            "device": self.device,
            "seed": self.seed,
            "deterministic": self.deterministic,
            "mixed_precision": self.mixed_precision,
            "init_strategy": self.init_strategy,
            "max_grad_norm": self.max_grad_norm,
            "optimizer": self.optimizer.to_dict(),
            "scheduler": self.scheduler.to_dict(),
            "loss": self.loss.to_dict(),
            "early_stopping": self.early_stopping.to_dict(),
            "checkpoint": self.checkpoint.to_dict(),
            "logging": self.logging.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingConfig":
        data = dict(data or {})
        return cls(
            experiment_name=data.get("experiment_name", "baseline"),
            epochs=int(data.get("epochs", 10)),
            batch_size=int(data.get("batch_size", 8)),
            grad_accum_steps=int(data.get("grad_accum_steps", 1)),
            device=data.get("device", "auto"),
            seed=int(data.get("seed", DEFAULT_RANDOM_SEED)),
            deterministic=bool(data.get("deterministic", False)),
            mixed_precision=bool(data.get("mixed_precision", False)),
            init_strategy=data.get("init_strategy"),
            max_grad_norm=data.get("max_grad_norm"),
            optimizer=OptimizerConfig(**{**OptimizerConfig().to_dict(), **(data.get("optimizer") or {})}),
            scheduler=SchedulerConfig(**{**SchedulerConfig().to_dict(), **(data.get("scheduler") or {})}),
            loss=LossConfig(**{**LossConfig().to_dict(), **(data.get("loss") or {})}),
            early_stopping=EarlyStoppingConfig(
                **{**EarlyStoppingConfig().to_dict(), **(data.get("early_stopping") or {})}),
            checkpoint=CheckpointConfig(**{**CheckpointConfig().to_dict(), **(data.get("checkpoint") or {})}),
            logging=LoggingConfig(**{**LoggingConfig().to_dict(),
                                     **_normalise_logging(data.get("logging"))}),
        )

    def config_hash(self) -> str:
        """Deterministic hash of the training configuration."""
        return stable_hash(self.to_dict())


def _normalise_logging(logging_data: dict[str, Any] | None) -> dict[str, Any]:
    """Coerce logging formats (list from JSON) back to a tuple for the frozen dataclass."""
    if not logging_data:
        return {}
    out = dict(logging_data)
    if "formats" in out and out["formats"] is not None:
        out["formats"] = tuple(out["formats"])
    return out
