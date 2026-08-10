"""Optimizer abstraction (Milestone 7).

Configuration-driven optimizer construction via a small registry (Adam, AdamW, SGD). No optimizer is
hardcoded. PyTorch is guarded — building an optimizer raises a clear error when torch is absent. No
training-loop code.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from app.core.exceptions import TrainingError
from app.models._torch import require_torch
from app.training.config import OptimizerConfig

OptimizerBuilder = Callable[[Iterable[Any], OptimizerConfig], Any]


def _adam(params: Iterable[Any], cfg: OptimizerConfig) -> Any:
    torch, _ = require_torch()
    return torch.optim.Adam(params, lr=cfg.lr, weight_decay=cfg.weight_decay, **cfg.params)


def _adamw(params: Iterable[Any], cfg: OptimizerConfig) -> Any:
    torch, _ = require_torch()
    return torch.optim.AdamW(params, lr=cfg.lr, weight_decay=cfg.weight_decay, **cfg.params)


def _sgd(params: Iterable[Any], cfg: OptimizerConfig) -> Any:
    torch, _ = require_torch()
    return torch.optim.SGD(params, lr=cfg.lr, weight_decay=cfg.weight_decay,
                           momentum=cfg.momentum, **cfg.params)


_OPTIMIZERS: dict[str, OptimizerBuilder] = {"adam": _adam, "adamw": _adamw, "sgd": _sgd}


def list_optimizers() -> list[str]:
    return sorted(_OPTIMIZERS)


def build_optimizer(params: Iterable[Any], config: OptimizerConfig) -> Any:
    """Build a torch optimizer from ``config`` (requires PyTorch)."""
    if config.name not in _OPTIMIZERS:
        raise TrainingError(f"Unknown optimizer {config.name!r}; expected one of {list_optimizers()}.")
    return _OPTIMIZERS[config.name](params, config)
