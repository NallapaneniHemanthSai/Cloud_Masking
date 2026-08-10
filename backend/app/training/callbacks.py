"""Callback framework (Milestone 7, revised).

Reusable callbacks that are **independent from the trainer**. Dispatch is driven by a typed
:class:`CallbackEvent` enum (no string comparisons), and execution order is determined by an explicit
:class:`CallbackPriority` (not registration order). Callbacks never import the trainer. Standard-library
only (checkpoint weights use the guarded checkpoint manager at runtime).
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any

from app.training.checkpoint import CheckpointManager
from app.training.config import EarlyStoppingConfig, TrainingConfig
from app.training.logging import TrainingLogger
from app.training.metadata import CheckpointState, TrainingState

logger = logging.getLogger(__name__)


class CallbackEvent(enum.Enum):
    """Lifecycle events dispatched to callbacks."""

    TRAIN_START = "train_start"
    EPOCH_START = "epoch_start"
    BATCH_START = "batch_start"
    BATCH_END = "batch_end"
    EPOCH_END = "epoch_end"
    TRAIN_END = "train_end"


class CallbackPriority(enum.IntEnum):
    """Explicit callback execution priority (lower value = earlier)."""

    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


# Maps each event to the handler method name (enum -> method; no event-string comparisons).
_EVENT_HANDLERS: dict[CallbackEvent, str] = {
    CallbackEvent.TRAIN_START: "on_train_start",
    CallbackEvent.EPOCH_START: "on_epoch_start",
    CallbackEvent.BATCH_START: "on_batch_start",
    CallbackEvent.BATCH_END: "on_batch_end",
    CallbackEvent.EPOCH_END: "on_epoch_end",
    CallbackEvent.TRAIN_END: "on_train_end",
}


@dataclass
class CallbackContext:
    """State passed to callbacks at each event (no plotting/eval/inference objects)."""

    config: TrainingConfig
    state: TrainingState
    metrics: dict[str, float] = field(default_factory=dict)
    model: Any = None
    optimizer: Any = None
    scheduler: Any = None
    logger: TrainingLogger | None = None
    checkpoint_manager: CheckpointManager | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class Callback:
    """Base callback. Override the hooks you need; all are no-ops by default.

    ``priority`` (a :class:`CallbackPriority`) controls execution order relative to other callbacks;
    lower runs earlier. Registration order breaks ties (stable).
    """

    default_priority: CallbackPriority = CallbackPriority.NORMAL

    def __init__(self, priority: CallbackPriority | None = None) -> None:
        self.priority: CallbackPriority = priority if priority is not None else self.default_priority

    def on_event(self, event: CallbackEvent, ctx: CallbackContext) -> None:
        """Dispatch an event to the matching handler (enum-driven; no string comparison)."""
        getattr(self, _EVENT_HANDLERS[event])(ctx)

    def on_train_start(self, ctx: CallbackContext) -> None: ...
    def on_epoch_start(self, ctx: CallbackContext) -> None: ...
    def on_batch_start(self, ctx: CallbackContext) -> None: ...
    def on_batch_end(self, ctx: CallbackContext) -> None: ...
    def on_epoch_end(self, ctx: CallbackContext) -> None: ...
    def on_train_end(self, ctx: CallbackContext) -> None: ...


class CallbackList:
    """Dispatches events to callbacks in **priority order** (stable within equal priority)."""

    def __init__(self, callbacks: list[Callback] | None = None) -> None:
        # Stable sort by priority: HIGHEST(0) first; equal priority keeps registration order.
        self._callbacks: list[Callback] = sorted(list(callbacks or []), key=lambda cb: int(cb.priority))

    @property
    def callbacks(self) -> list[Callback]:
        return list(self._callbacks)

    def dispatch(self, event: CallbackEvent, ctx: CallbackContext) -> None:
        for cb in self._callbacks:
            cb.on_event(event, ctx)


class LoggingCallback(Callback):
    """Logs per-epoch metrics through the training logger. Runs early (HIGH)."""

    default_priority = CallbackPriority.HIGH

    def on_epoch_end(self, ctx: CallbackContext) -> None:
        if ctx.logger is None:
            return
        record = {"epoch": ctx.state.epoch, "global_step": ctx.state.global_step}
        record.update(ctx.metrics)
        ctx.logger.log(record)


class CheckpointCallback(Callback):
    """Saves latest/best checkpoints via the checkpoint manager (weights optional). Priority NORMAL."""

    default_priority = CallbackPriority.NORMAL

    def __init__(self, config: TrainingConfig, priority: CallbackPriority | None = None) -> None:
        super().__init__(priority)
        self.config = config

    def _payload(self, ctx: CallbackContext) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if ctx.model is not None and hasattr(ctx.model, "state_dict"):
            payload["model_state_dict"] = ctx.model.state_dict()
        if ctx.optimizer is not None and hasattr(ctx.optimizer, "state_dict"):
            payload["optimizer_state_dict"] = ctx.optimizer.state_dict()
        if ctx.scheduler is not None and hasattr(ctx.scheduler, "state_dict"):
            payload["scheduler_state_dict"] = ctx.scheduler.state_dict()
        return payload

    def _state(self, ctx: CallbackContext, value: float | None) -> CheckpointState:
        return CheckpointState(
            epoch=ctx.state.epoch, global_step=ctx.state.global_step,
            monitor=self.config.checkpoint.monitor, mode=self.config.checkpoint.mode,
            metric_value=value, config_hash=self.config.config_hash(), metrics=dict(ctx.metrics))

    def on_epoch_end(self, ctx: CallbackContext) -> None:
        manager = ctx.checkpoint_manager
        if manager is None:
            return
        value = ctx.metrics.get(self.config.checkpoint.monitor)
        payload = self._payload(ctx)
        manager.save_latest(payload, self._state(ctx, value))
        manager.maybe_save_best(payload, self._state(ctx, value), value)


class EarlyStoppingCallback(Callback):
    """Requests a stop when the monitored metric stops improving. Runs late (LOW)."""

    default_priority = CallbackPriority.LOW

    def __init__(self, config: EarlyStoppingConfig, priority: CallbackPriority | None = None) -> None:
        super().__init__(priority)
        self.config = config
        self._best: float | None = None
        self._wait = 0

    def _improved(self, value: float) -> bool:
        if self._best is None:
            return True
        delta = value - self._best
        return -delta > self.config.min_delta if self.config.mode == "min" else delta > self.config.min_delta

    def on_epoch_end(self, ctx: CallbackContext) -> None:
        if not self.config.enabled:
            return
        value = ctx.metrics.get(self.config.monitor)
        if value is None:
            return
        if self._improved(value):
            self._best = value
            self._wait = 0
        else:
            self._wait += 1
            if self._wait >= self.config.patience:
                ctx.state.stop_requested = True
                logger.info("Early stopping at epoch %d (no %s improvement for %d epochs).",
                            ctx.state.epoch + 1, self.config.monitor, self.config.patience)


class ProgressCallback(Callback):
    """Emits a concise progress line each epoch. Runs last (LOWEST)."""

    default_priority = CallbackPriority.LOWEST

    def on_epoch_end(self, ctx: CallbackContext) -> None:
        metrics = " ".join(f"{k}={v:.4f}" for k, v in ctx.metrics.items() if isinstance(v, (int, float)))
        logger.info("epoch %d/%d %s", ctx.state.epoch + 1, ctx.config.epochs, metrics)
