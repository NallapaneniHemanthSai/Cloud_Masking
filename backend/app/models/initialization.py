"""Weight initialization strategies + reporting (Milestone 6, revised).

Reusable, selectable initialization strategies (Xavier, Kaiming, Constant, Identity). The **selection** is
standard-library (returns a callable); **application** uses PyTorch (guarded) and can optionally return a
structured :class:`InitializationReport` describing what was initialized/skipped. No optimizer state, no
weights saved.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.exceptions import ModelError
from app.models._torch import require_torch


class InitStrategy(str, enum.Enum):
    """Supported weight-initialization strategies."""

    XAVIER = "xavier"
    KAIMING = "kaiming"
    CONSTANT = "constant"
    IDENTITY = "identity"


# Layer types (by class name) that carry initialisable weights.
_WEIGHTED_LAYERS = {"Conv1d", "Conv2d", "Conv3d", "ConvTranspose2d", "Linear"}


@dataclass
class InitializationReport:
    """Structured record of an initialization pass (no weights, no optimizer state)."""

    strategy: str
    modules_initialized: list[str] = field(default_factory=list)
    parameter_tensors_initialized: int = 0
    skipped_modules: list[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "modules_initialized": list(self.modules_initialized),
            "parameter_tensors_initialized": self.parameter_tensors_initialized,
            "skipped_modules": list(self.skipped_modules),
            "timestamp": self.timestamp,
        }


def is_initializable(module: Any) -> bool:
    """True when ``module`` is a leaf layer with an initialisable ``weight`` (standard-library check)."""
    return type(module).__name__ in _WEIGHTED_LAYERS and getattr(module, "weight", None) is not None


def get_initializer(strategy: str, **kwargs: Any) -> Callable[[Any], None]:
    """Return a callable ``init_fn(module)`` implementing the requested strategy.

    Selection is dependency-free (returns a closure); the returned callable uses ``torch.nn.init`` only
    when actually invoked on a module.

    Raises:
        ModelError: If the strategy name is unknown.
    """
    valid = {s.value for s in InitStrategy}
    if strategy not in valid:
        raise ModelError(f"Unknown init strategy {strategy!r}; expected one of {sorted(valid)}.")

    def init_fn(module: Any) -> None:
        torch, nn = require_torch()
        if not is_initializable(module):
            return
        weight = module.weight
        if strategy == InitStrategy.XAVIER.value:
            nn.init.xavier_uniform_(weight)
        elif strategy == InitStrategy.KAIMING.value:
            nn.init.kaiming_normal_(weight, a=kwargs.get("a", 0.0),
                                    nonlinearity=kwargs.get("nonlinearity", "relu"))
        elif strategy == InitStrategy.CONSTANT.value:
            nn.init.constant_(weight, kwargs.get("value", 0.0))
        elif strategy == InitStrategy.IDENTITY.value:
            if type(module).__name__ == "Linear" and weight.shape[0] == weight.shape[1]:
                nn.init.eye_(weight)
            elif weight.dim() >= 3:
                nn.init.dirac_(weight)
            else:
                nn.init.xavier_uniform_(weight)
        bias = getattr(module, "bias", None)
        if bias is not None:
            nn.init.zeros_(bias)

    return init_fn


def apply_initialization(model: Any, strategy: str, *, return_report: bool = False, **kwargs: Any):
    """Apply an initialization strategy to every eligible layer in ``model`` (requires PyTorch).

    Args:
        model: A torch ``nn.Module``.
        strategy: One of :class:`InitStrategy` values.
        return_report: If True, return ``(model, InitializationReport)`` instead of just ``model``.
        **kwargs: Strategy parameters (e.g. ``value`` for constant).

    Returns:
        ``model`` (default), or ``(model, InitializationReport)`` when ``return_report`` is True.
    """
    require_torch()
    init_fn = get_initializer(strategy, **kwargs)

    if not return_report:
        model.apply(init_fn)
        return model

    report = InitializationReport(strategy=strategy,
                                  timestamp=datetime.now(timezone.utc).isoformat())
    for name, module in model.named_modules():
        if name == "":  # skip the root container
            continue
        if is_initializable(module):
            init_fn(module)
            report.modules_initialized.append(name)
            report.parameter_tensors_initialized += 1  # weight
            if getattr(module, "bias", None) is not None:
                report.parameter_tensors_initialized += 1  # bias
        elif not list(module.children()):  # a leaf that was not initialised
            report.skipped_modules.append(name)
    return model, report
