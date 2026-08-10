"""Learning-rate scheduler abstraction (Milestone 7).

Configuration-driven scheduler construction via a small registry (CosineAnnealingLR, StepLR,
ReduceLROnPlateau). Selection is configuration-only; ``none`` returns no scheduler. PyTorch is guarded.
``ReduceLROnPlateau`` steps on a monitored metric (flagged via :func:`steps_on_metric`).
"""

from __future__ import annotations

from typing import Any, Callable

from app.core.exceptions import TrainingError
from app.models._torch import require_torch
from app.training.config import SchedulerConfig

SchedulerBuilder = Callable[[Any, SchedulerConfig, int], Any]

# Schedulers that require the monitored metric passed to .step(metric).
_METRIC_SCHEDULERS = {"plateau"}


def _cosine(optimizer: Any, cfg: SchedulerConfig, epochs: int) -> Any:
    torch, _ = require_torch()
    t_max = cfg.params.get("T_max", epochs)
    return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=t_max,
                                                      **_without(cfg.params, "T_max"))


def _step(optimizer: Any, cfg: SchedulerConfig, epochs: int) -> Any:
    torch, _ = require_torch()
    step_size = cfg.params.get("step_size", max(1, epochs // 3))
    gamma = cfg.params.get("gamma", 0.1)
    return torch.optim.lr_scheduler.StepLR(optimizer, step_size=step_size, gamma=gamma)


def _plateau(optimizer: Any, cfg: SchedulerConfig, epochs: int) -> Any:
    torch, _ = require_torch()
    return torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode=cfg.params.get("mode", "min"),
        factor=cfg.params.get("factor", 0.1), patience=cfg.params.get("patience", 5))


_SCHEDULERS: dict[str, SchedulerBuilder] = {"cosine": _cosine, "step": _step, "plateau": _plateau}


def _without(d: dict[str, Any], key: str) -> dict[str, Any]:
    return {k: v for k, v in d.items() if k != key}


def list_schedulers() -> list[str]:
    return sorted(_SCHEDULERS)


def steps_on_metric(config: SchedulerConfig) -> bool:
    """True when the scheduler's ``.step`` needs the monitored metric (ReduceLROnPlateau)."""
    return config.name in _METRIC_SCHEDULERS


def build_scheduler(optimizer: Any, config: SchedulerConfig, epochs: int) -> Any | None:
    """Build a torch scheduler from ``config`` (requires PyTorch). ``none`` -> ``None``."""
    if config.name in {"none", "", None}:
        return None
    if config.name not in _SCHEDULERS:
        raise TrainingError(f"Unknown scheduler {config.name!r}; expected one of {list_schedulers()} or 'none'.")
    return _SCHEDULERS[config.name](optimizer, config, epochs)
