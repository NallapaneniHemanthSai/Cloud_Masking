"""Training loss (optimization objective) — Milestone 7.

Configuration-driven training criterion (cross-entropy, soft Dice, combined). This is the **optimization
objective** the trainer minimises — it is not an evaluation metric (evaluation metrics arrive in M8).
PyTorch is guarded. Selection is configuration-only.
"""

from __future__ import annotations

from typing import Any, Callable

from app.core.exceptions import TrainingError
from app.models._torch import require_torch
from app.training.config import LossConfig

# A criterion maps (logits, targets) -> scalar loss tensor.
Criterion = Callable[[Any, Any], Any]

_DICE_SMOOTH = 1.0


def _cross_entropy(cfg: LossConfig) -> Criterion:
    torch, nn = require_torch()
    weight = cfg.params.get("weight")
    weight_t = torch.tensor(weight, dtype=torch.float32) if weight is not None else None
    ce = nn.CrossEntropyLoss(weight=weight_t, ignore_index=cfg.params.get("ignore_index", -100))

    def criterion(logits: Any, targets: Any) -> Any:
        return ce(logits, targets)

    return criterion


def _dice(cfg: LossConfig) -> Criterion:
    torch, _ = require_torch()
    smooth = cfg.params.get("smooth", _DICE_SMOOTH)

    def criterion(logits: Any, targets: Any) -> Any:
        num_classes = logits.shape[1]
        probs = torch.softmax(logits, dim=1)
        # (B, H, W) int targets -> (B, C, H, W) one-hot
        one_hot = torch.nn.functional.one_hot(targets.long(), num_classes)
        one_hot = one_hot.permute(0, 3, 1, 2).float()
        dims = (0, 2, 3)
        intersection = torch.sum(probs * one_hot, dims)
        cardinality = torch.sum(probs + one_hot, dims)
        dice = (2.0 * intersection + smooth) / (cardinality + smooth)
        return 1.0 - dice.mean()

    return criterion


def _dice_ce(cfg: LossConfig) -> Criterion:
    ce = _cross_entropy(cfg)
    dice = _dice(cfg)
    ce_weight = cfg.params.get("ce_weight", 0.5)
    dice_weight = cfg.params.get("dice_weight", 0.5)

    def criterion(logits: Any, targets: Any) -> Any:
        return ce_weight * ce(logits, targets) + dice_weight * dice(logits, targets)

    return criterion


_CRITERIA: dict[str, Callable[[LossConfig], Criterion]] = {
    "cross_entropy": _cross_entropy,
    "dice": _dice,
    "dice_ce": _dice_ce,
}


def list_losses() -> list[str]:
    return sorted(_CRITERIA)


def build_criterion(config: LossConfig) -> Criterion:
    """Build the training criterion from ``config`` (requires PyTorch)."""
    if config.name not in _CRITERIA:
        raise TrainingError(f"Unknown loss {config.name!r}; expected one of {list_losses()}.")
    return _CRITERIA[config.name](config)
