"""Training engine (Milestone 7).

Reusable, configuration-driven training infrastructure — no evaluation metrics, benchmarks, deployment,
API, or frontend code. The :class:`Trainer` is decoupled from evaluation/deployment so later milestones
plug in via callbacks / an optional metrics function without architectural change. PyTorch is a guarded
optional dependency: the package imports on a bare interpreter and training raises a clear
:class:`app.core.exceptions.TrainingError`/`ModelError` when torch is absent. See ADR-0007.

Public surface:

* Config: :class:`TrainingConfig` (+ optimizer/scheduler/loss/checkpoint/logging/early-stopping sub-configs).
* Trainer/engine: :class:`Trainer`, :class:`TrainingEngine`.
* Abstractions: :func:`build_optimizer`, :func:`build_scheduler`, :func:`build_criterion`.
* Checkpointing: :class:`CheckpointManager`, :class:`CheckpointState`.
* Callbacks: :class:`Callback`, :class:`CallbackList`, :class:`CheckpointCallback`,
  :class:`LoggingCallback`, :class:`EarlyStoppingCallback`, :class:`ProgressCallback`.
* Logging: :class:`TrainingLogger`, :class:`MetricSink`.
* Metadata: :class:`TrainingState`, :class:`TrainingMetadata`, :class:`TrainerSummary`.
* Experiment: :class:`ExperimentRun`, :func:`create_experiment`.
* Reproducibility: :func:`set_seed`, :func:`capture_environment`, :func:`resolve_device`.
"""

from app.training.artifact import TrainingArtifact
from app.training.callbacks import (
    Callback,
    CallbackContext,
    CallbackEvent,
    CallbackList,
    CallbackPriority,
    CheckpointCallback,
    EarlyStoppingCallback,
    LoggingCallback,
    ProgressCallback,
)
from app.training.checkpoint import CheckpointManager
from app.training.lifecycle import (
    TrainerState,
    TrainerStateMachine,
    is_valid_transition,
)
from app.training.config import (
    CheckpointConfig,
    EarlyStoppingConfig,
    LoggingConfig,
    LossConfig,
    OptimizerConfig,
    SchedulerConfig,
    TrainingConfig,
)
from app.training.engine import TrainingEngine
from app.training.experiment import ExperimentRun, create_experiment, experiment_id_for
from app.training.logging import MetricSink, TrainingLogger
from app.training.loss import build_criterion, list_losses
from app.training.metadata import (
    CheckpointState,
    TrainerSummary,
    TrainingMetadata,
    TrainingState,
)
from app.training.optimizer import build_optimizer, list_optimizers
from app.training.scheduler import build_scheduler, list_schedulers
from app.training.seed import capture_environment, resolve_device, set_seed
from app.training.trainer import Trainer

__all__ = [
    "TrainingConfig",
    "OptimizerConfig",
    "SchedulerConfig",
    "LossConfig",
    "EarlyStoppingConfig",
    "CheckpointConfig",
    "LoggingConfig",
    "Trainer",
    "TrainingEngine",
    "build_optimizer",
    "list_optimizers",
    "build_scheduler",
    "list_schedulers",
    "build_criterion",
    "list_losses",
    "CheckpointManager",
    "CheckpointState",
    "Callback",
    "CallbackContext",
    "CallbackEvent",
    "CallbackPriority",
    "CallbackList",
    "CheckpointCallback",
    "LoggingCallback",
    "EarlyStoppingCallback",
    "ProgressCallback",
    "TrainerState",
    "TrainerStateMachine",
    "is_valid_transition",
    "TrainingLogger",
    "MetricSink",
    "TrainingState",
    "TrainingMetadata",
    "TrainerSummary",
    "TrainingArtifact",
    "ExperimentRun",
    "create_experiment",
    "experiment_id_for",
    "set_seed",
    "capture_environment",
    "resolve_device",
]
