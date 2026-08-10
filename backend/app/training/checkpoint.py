"""Checkpoint manager (Milestone 7).

Saves/loads training checkpoints with a best/latest policy and resume metadata. Weights **may** be saved
(``torch.save``); a JSON :class:`CheckpointState` sidecar is **always** written. No evaluation logic —
evaluation metrics, if present, are optional metadata only. PyTorch is guarded (metadata works without it;
weight save/load requires torch).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.exceptions import TrainingError
from app.models._torch import require_torch, torch_available
from app.training.metadata import CheckpointState

logger = logging.getLogger(__name__)

BEST_TAG = "best"
LATEST_TAG = "latest"


class CheckpointManager:
    """Manages checkpoint files and their metadata sidecars."""

    def __init__(self, directory: Path, *, monitor: str = "train_loss", mode: str = "min",
                 save_best: bool = True, save_latest: bool = True, save_weights: bool = True) -> None:
        if mode not in {"min", "max"}:
            raise TrainingError(f"mode must be 'min' or 'max', got {mode!r}.")
        self.directory = Path(directory)
        self.monitor = monitor
        self.mode = mode
        self.save_best_enabled = save_best
        self.save_latest_enabled = save_latest
        self.save_weights = save_weights
        self.best_value: float | None = None

    # --- policy -----------------------------------------------------------------------------------
    def is_improvement(self, value: float) -> bool:
        """True when ``value`` improves on the best-so-far under the configured mode."""
        if value is None:
            return False
        if self.best_value is None:
            return True
        return value < self.best_value if self.mode == "min" else value > self.best_value

    # --- save / load ------------------------------------------------------------------------------
    def _paths(self, tag: str) -> tuple[Path, Path]:
        self.directory.mkdir(parents=True, exist_ok=True)
        return self.directory / f"{tag}.pt", self.directory / f"{tag}.json"

    def save(self, payload: dict[str, Any], state: CheckpointState, tag: str) -> Path:
        """Save a checkpoint payload (weights optional) + a metadata sidecar; returns the sidecar path.

        ``payload`` may contain ``model_state_dict`` / ``optimizer_state_dict`` / ``scheduler_state_dict``
        and is written with ``torch.save`` only when ``save_weights`` is True and torch is available.
        """
        weights_path, meta_path = self._paths(tag)
        state.has_model_weights = bool(self.save_weights and "model_state_dict" in payload)
        state.has_optimizer_state = "optimizer_state_dict" in payload
        state.has_scheduler_state = payload.get("scheduler_state_dict") is not None

        if self.save_weights and payload:
            if not torch_available():
                logger.warning("torch unavailable — skipping weight save for %s (metadata still written).", tag)
            else:
                torch, _ = require_torch()
                torch.save(payload, weights_path)
                logger.info("Saved checkpoint weights: %s", weights_path)

        meta_path.write_text(state.to_json(), encoding="utf-8")
        logger.info("Saved checkpoint metadata: %s", meta_path)
        return meta_path

    def save_latest(self, payload: dict[str, Any], state: CheckpointState) -> Path | None:
        if not self.save_latest_enabled:
            return None
        return self.save(payload, state, LATEST_TAG)

    def maybe_save_best(self, payload: dict[str, Any], state: CheckpointState,
                        value: float | None) -> Path | None:
        """Save the 'best' checkpoint when ``value`` improves the monitored metric."""
        if not self.save_best_enabled or value is None or not self.is_improvement(value):
            return None
        self.best_value = value
        state.metric_value = value
        return self.save(payload, state, BEST_TAG)

    def load(self, tag: str = LATEST_TAG, map_location: str | None = None) -> dict[str, Any]:
        """Load a checkpoint payload (requires torch)."""
        torch, _ = require_torch()
        weights_path = self.directory / f"{tag}.pt"
        if not weights_path.is_file():
            raise TrainingError(f"Checkpoint weights not found: {weights_path}")
        return torch.load(weights_path, map_location=map_location, weights_only=False)

    def resume_metadata(self, tag: str = LATEST_TAG) -> CheckpointState:
        """Read the checkpoint metadata sidecar for resuming (no torch required)."""
        meta_path = self.directory / f"{tag}.json"
        if not meta_path.is_file():
            raise TrainingError(f"Checkpoint metadata not found: {meta_path}")
        return CheckpointState.from_json(meta_path.read_text(encoding="utf-8"))
