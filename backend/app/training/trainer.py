"""Reusable Trainer (Milestone 7).

Orchestrates a training run: initialise model/optimizer/scheduler/criterion, execute epochs via the
:class:`TrainingEngine`, dispatch callbacks, drive checkpointing and logging. It is **independent of
evaluation and deployment** — validation metrics plug in later (M8) via a callback / ``metrics_fn``
without changing the trainer. PyTorch is guarded (constructing a trainer is fine; :meth:`fit` requires
torch).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Iterable

from app.models._torch import require_torch
from app.training.artifact import TrainingArtifact
from app.training.callbacks import (
    Callback,
    CallbackContext,
    CallbackEvent,
    CallbackList,
    CheckpointCallback,
    EarlyStoppingCallback,
    LoggingCallback,
    ProgressCallback,
)
from app.training.checkpoint import CheckpointManager
from app.training.config import TrainingConfig
from app.training.engine import TrainingEngine
from app.training.lifecycle import TrainerState, TrainerStateMachine
from app.training.logging import ConsoleSink, TrainingLogger
from app.training.loss import build_criterion
from app.training.metadata import TrainerSummary, TrainingMetadata, TrainingState
from app.training.optimizer import build_optimizer
from app.training.scheduler import build_scheduler, steps_on_metric
from app.training.seed import capture_environment, resolve_device, set_seed

logger = logging.getLogger(__name__)


class Trainer:
    """Configuration-driven training orchestrator."""

    def __init__(self, config: TrainingConfig, model: Any, train_loader: Iterable[Any], *,
                 callbacks: list[Callback] | None = None, output_dir: Path | str | None = None,
                 training_logger: TrainingLogger | None = None,
                 checkpoint_manager: CheckpointManager | None = None) -> None:
        self.config = config
        self.model = model
        self.train_loader = train_loader
        self.output_dir = Path(output_dir) if output_dir else None
        self.device = resolve_device(config.device)
        self.engine = TrainingEngine()
        self.state = TrainingState(monitor=config.checkpoint.monitor)

        self.logger = training_logger
        self.checkpoint_manager = checkpoint_manager
        self._explicit_callbacks = callbacks
        self.callbacks: CallbackList | None = None

        self.optimizer: Any = None
        self.scheduler: Any = None
        self.criterion: Any = None
        self._scaler: Any = None
        self._is_setup = False
        self._machine = TrainerStateMachine()   # lifecycle state machine (CREATED)

    @property
    def trainer_state(self) -> TrainerState:
        """Current lifecycle state."""
        return self._machine.state

    @classmethod
    def from_configs(cls, config: TrainingConfig, model_config: Any, train_loader: Iterable[Any],
                     **kwargs: Any) -> "Trainer":
        """Build the model from a ``ModelConfig`` (via ModelFactory) and construct a Trainer."""
        from app.models.factory import ModelFactory
        model = ModelFactory().create(model_config)
        return cls(config, model, train_loader, **kwargs)

    # --- setup ------------------------------------------------------------------------------------
    def setup(self) -> "Trainer":
        """Initialise seed, device, model, optimizer, scheduler, criterion, logger, callbacks."""
        try:
            return self._setup()
        except Exception:
            if self._machine.state not in (TrainerState.COMPLETED, TrainerState.FAILED):
                self._machine.transition_to(TrainerState.FAILED)
            raise

    def _setup(self) -> "Trainer":
        torch, _ = require_torch()
        set_seed(self.config.seed, deterministic=self.config.deterministic)

        self.model = self.model.to(self.device)
        if self.config.init_strategy:
            from app.models.initialization import apply_initialization
            apply_initialization(self.model, self.config.init_strategy)

        self.optimizer = build_optimizer(self.model.parameters(), self.config.optimizer)
        self.scheduler = build_scheduler(self.optimizer, self.config.scheduler, self.config.epochs)
        self.criterion = build_criterion(self.config.loss)

        if self.config.mixed_precision and self.device == "cuda":
            self._scaler = torch.cuda.amp.GradScaler()

        if self.logger is None:
            if self.output_dir is not None:
                self.logger = TrainingLogger.from_config(
                    self.output_dir / self.config.logging.dir,
                    self.config.logging.formats, self.config.logging.console)
            else:
                self.logger = TrainingLogger([ConsoleSink()]) if self.config.logging.console else TrainingLogger()

        if self.checkpoint_manager is None and self.output_dir is not None:
            self.checkpoint_manager = CheckpointManager(
                self.output_dir / self.config.checkpoint.dir,
                monitor=self.config.checkpoint.monitor, mode=self.config.checkpoint.mode,
                save_best=self.config.checkpoint.save_best, save_latest=self.config.checkpoint.save_latest,
                save_weights=self.config.checkpoint.save_weights)

        self.callbacks = CallbackList(self._explicit_callbacks or self._default_callbacks())
        self._is_setup = True
        self._machine.transition_to(TrainerState.INITIALIZED)
        return self

    def _default_callbacks(self) -> list[Callback]:
        cbs: list[Callback] = [LoggingCallback(), ProgressCallback()]
        if self.config.early_stopping.enabled:
            cbs.append(EarlyStoppingCallback(self.config.early_stopping))
        if self.checkpoint_manager is not None:
            cbs.append(CheckpointCallback(self.config))
        return cbs

    def training_metadata(self, experiment_id: str) -> TrainingMetadata:
        """Reproducibility metadata for this run."""
        return TrainingMetadata(
            experiment_id=experiment_id, config_hash=self.config.config_hash(),
            seed=self.config.seed, deterministic=self.config.deterministic, device=self.device,
            environment=capture_environment().to_dict())

    def build_training_artifact(self, experiment_run: Any, *, model_artifact: Any = None,
                                notes: str = "") -> TrainingArtifact:
        """Assemble a :class:`TrainingArtifact` for this run (canonical completed-run metadata)."""
        experiment_id = getattr(experiment_run, "experiment_id", None)
        if experiment_id is None and isinstance(experiment_run, dict):
            experiment_id = experiment_run.get("experiment_id", "")
        checkpoint_state: Any = None
        if self.checkpoint_manager is not None:
            try:
                checkpoint_state = self.checkpoint_manager.resume_metadata("best")
            except Exception:  # noqa: BLE001 - no best checkpoint yet is fine
                checkpoint_state = None
        return TrainingArtifact.create(
            experiment_run=experiment_run,
            training_metadata=self.training_metadata(experiment_id or ""),
            training_config_hash=self.config.config_hash(),
            environment_capture=capture_environment().to_dict(),
            model_artifact=model_artifact, checkpoint_state=checkpoint_state, notes=notes)

    # --- fit --------------------------------------------------------------------------------------
    def fit(self) -> TrainerSummary:
        """Run the training loop and return a :class:`TrainerSummary`."""
        try:
            return self._fit()
        except Exception:
            if self._machine.state not in (TrainerState.COMPLETED, TrainerState.FAILED):
                self._machine.transition_to(TrainerState.FAILED)
            raise

    def _fit(self) -> TrainerSummary:
        if not self._is_setup:
            self.setup()
        self._machine.transition_to(TrainerState.RUNNING)
        start = time.time()
        ctx = CallbackContext(
            config=self.config, state=self.state, model=self.model, optimizer=self.optimizer,
            scheduler=self.scheduler, logger=self.logger, checkpoint_manager=self.checkpoint_manager)

        self.callbacks.dispatch(CallbackEvent.TRAIN_START, ctx)
        epochs_run = 0
        for epoch in range(self.config.epochs):
            self.state.epoch = epoch
            self.callbacks.dispatch(CallbackEvent.EPOCH_START, ctx)

            metrics = self.engine.train_epoch(
                self.model, self.train_loader, self.optimizer, self.criterion,
                self.config, self.device, self.callbacks, ctx, scaler=self._scaler)
            metrics["lr"] = float(self.optimizer.param_groups[0]["lr"])

            self._step_scheduler(metrics)
            self._update_best(metrics)
            ctx.metrics = metrics
            self.state.last_metrics = metrics
            epochs_run += 1

            # checkpoint/logging/early-stopping happen at EPOCH_END.
            self._machine.transition_to(TrainerState.CHECKPOINTING)
            self.callbacks.dispatch(CallbackEvent.EPOCH_END, ctx)
            self._machine.transition_to(TrainerState.RUNNING)
            if self.state.stop_requested:
                break
        self.callbacks.dispatch(CallbackEvent.TRAIN_END, ctx)
        if self.logger is not None:
            self.logger.close()
        self._machine.transition_to(TrainerState.COMPLETED)

        return TrainerSummary(
            experiment_id=f"{self.config.experiment_name}-{self.config.config_hash()[:8]}",
            epochs_planned=self.config.epochs, epochs_run=epochs_run,
            best_metric=self.state.best_metric, best_epoch=self.state.best_epoch,
            stopped_early=self.state.stop_requested, final_metrics=self.state.last_metrics,
            duration_seconds=round(time.time() - start, 4), config_hash=self.config.config_hash())

    def _step_scheduler(self, metrics: dict[str, float]) -> None:
        if self.scheduler is None:
            return
        if steps_on_metric(self.config.scheduler):
            self.scheduler.step(metrics.get(self.config.checkpoint.monitor, 0.0))
        else:
            self.scheduler.step()

    def _update_best(self, metrics: dict[str, float]) -> None:
        value = metrics.get(self.state.monitor)
        if value is None:
            return
        mode = self.config.checkpoint.mode
        improved = (self.state.best_metric is None
                    or (value < self.state.best_metric if mode == "min" else value > self.state.best_metric))
        if improved:
            self.state.best_metric = value
            self.state.best_epoch = self.state.epoch
