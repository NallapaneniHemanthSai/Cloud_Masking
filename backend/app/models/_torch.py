"""Guarded PyTorch access (Milestone 6).

Centralises the optional PyTorch import so the models package imports cleanly on a bare interpreter and
every entry point gives a meaningful error instead of an ImportError. No training/optimisation code.
"""

from __future__ import annotations

from app.core.exceptions import ModelError

try:  # torch is declared in requirements.in; may be absent on a bare interpreter.
    import torch  # type: ignore
    import torch.nn as nn  # type: ignore
    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without torch
    torch = None  # type: ignore
    nn = None  # type: ignore
    TORCH_AVAILABLE = False

_TORCH_HINT = (
    "PyTorch is required for this operation but is not installed. Install project dependencies "
    "(see backend/requirements.in) in the Python 3.11 environment."
)


def torch_available() -> bool:
    """Return True when PyTorch can be used."""
    return TORCH_AVAILABLE


def require_torch():
    """Return the ``(torch, nn)`` modules, or raise :class:`ModelError` with a clear message.

    Reads the module-level ``torch`` reference at call time so guard behaviour is testable.
    """
    if torch is None:
        raise ModelError(_TORCH_HINT)
    return torch, nn
