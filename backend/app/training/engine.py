"""Training engine — low-level epoch/step mechanics (Milestone 7).

Executes forward → loss → backward → optimizer step with configurable gradient accumulation, optional
gradient clipping, and optional CUDA mixed precision. Dispatches ``on_batch_end`` callbacks and returns the
epoch's training loss. **No evaluation metrics** are computed (training loss is the optimization objective).
PyTorch is guarded.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from app.models._torch import require_torch
from app.training.callbacks import CallbackContext, CallbackEvent, CallbackList
from app.training.config import TrainingConfig
from app.training.loss import Criterion

logger = logging.getLogger(__name__)


def _to_device(batch: Any, device: str) -> tuple[Any, Any]:
    inputs, targets = batch
    if hasattr(inputs, "to"):
        inputs = inputs.to(device)
    if hasattr(targets, "to"):
        targets = targets.to(device)
    return inputs, targets


class TrainingEngine:
    """Runs one training epoch. Stateless except for the objects passed in."""

    def train_epoch(self, model: Any, loader: Iterable[Any], optimizer: Any, criterion: Criterion,
                    config: TrainingConfig, device: str, callbacks: CallbackList,
                    ctx: CallbackContext, scaler: Any = None) -> dict[str, float]:
        """Train for one epoch; returns ``{"train_loss": <mean>}``."""
        torch, _ = require_torch()
        model.train()
        accum = config.grad_accum_steps
        use_amp = bool(config.mixed_precision and device == "cuda" and scaler is not None)

        total_loss = 0.0
        n_batches = 0
        pending = 0
        optimizer.zero_grad(set_to_none=True)

        for batch in loader:
            callbacks.dispatch(CallbackEvent.BATCH_START, ctx)
            inputs, targets = _to_device(batch, device)
            if use_amp:
                with torch.cuda.amp.autocast():
                    loss = criterion(model(inputs), targets) / accum
                scaler.scale(loss).backward()
            else:
                loss = criterion(model(inputs), targets) / accum
                loss.backward()

            pending += 1
            n_batches += 1
            total_loss += loss.item() * accum

            if pending == accum:
                self._optimizer_step(optimizer, model, config, use_amp, scaler)
                ctx.state.global_step += 1
                pending = 0

            ctx.metrics = {"train_loss": total_loss / n_batches}
            callbacks.dispatch(CallbackEvent.BATCH_END, ctx)

        if pending > 0:  # flush a partial accumulation window
            self._optimizer_step(optimizer, model, config, use_amp, scaler)
            ctx.state.global_step += 1

        return {"train_loss": total_loss / max(n_batches, 1)}

    @staticmethod
    def _optimizer_step(optimizer: Any, model: Any, config: TrainingConfig,
                        use_amp: bool, scaler: Any) -> None:
        torch, _ = require_torch()
        if config.max_grad_norm is not None:
            if use_amp:
                scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
        if use_amp:
            scaler.step(optimizer)
            scaler.update()
        else:
            optimizer.step()
        optimizer.zero_grad(set_to_none=True)
