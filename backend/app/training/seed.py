"""Reproducibility: seeding + environment/version capture (Milestone 7).

Deterministic-training support: seed Python/NumPy/PyTorch, optionally request deterministic algorithms,
and capture the environment/versions for the training metadata. PyTorch and NumPy are guarded — seeding
degrades gracefully when they are unavailable. No training loop code here.
"""

from __future__ import annotations

import os
import platform
import random
import sys
from dataclasses import dataclass
from typing import Any

from app.core.constants import DEFAULT_RANDOM_SEED

try:
    import numpy as _np  # type: ignore
except ImportError:  # pragma: no cover
    _np = None  # type: ignore

# Reuse the project's single guarded torch accessor (no duplication).
from app.models._torch import torch as _torch  # type: ignore


def set_seed(seed: int = DEFAULT_RANDOM_SEED, *, deterministic: bool = False) -> int:
    """Seed all RNGs (Python/NumPy/PyTorch) and optionally enable deterministic algorithms.

    Returns the seed used, so it can be recorded in metadata.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    if _np is not None:
        _np.random.seed(seed)
    if _torch is not None:
        _torch.manual_seed(seed)
        if _torch.cuda.is_available():
            _torch.cuda.manual_seed_all(seed)
        if deterministic:
            try:
                _torch.use_deterministic_algorithms(True, warn_only=True)
            except Exception:  # noqa: BLE001 - not all backends support this
                pass
            if hasattr(_torch, "backends") and hasattr(_torch.backends, "cudnn"):
                _torch.backends.cudnn.deterministic = True
                _torch.backends.cudnn.benchmark = False
    return seed


def seed_worker(worker_id: int) -> None:  # pragma: no cover - used by DataLoader workers
    """DataLoader ``worker_init_fn`` for reproducible workers."""
    base = (worker_id + (0 if _torch is None else int(_torch.initial_seed()))) % (2 ** 32)
    random.seed(base)
    if _np is not None:
        _np.random.seed(base)


@dataclass
class EnvironmentInfo:
    """Captured environment/versions for reproducibility metadata."""

    python_version: str
    platform: str
    torch_version: str | None
    numpy_version: str | None
    cuda_available: bool
    mps_available: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "python_version": self.python_version,
            "platform": self.platform,
            "torch_version": self.torch_version,
            "numpy_version": self.numpy_version,
            "cuda_available": self.cuda_available,
            "mps_available": self.mps_available,
        }


def capture_environment() -> EnvironmentInfo:
    """Capture the current Python/torch/numpy environment for reproducibility."""
    cuda = bool(_torch is not None and _torch.cuda.is_available())
    mps = bool(
        _torch is not None
        and hasattr(_torch.backends, "mps")
        and _torch.backends.mps.is_available()
    )
    return EnvironmentInfo(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        torch_version=(_torch.__version__ if _torch is not None else None),
        numpy_version=(_np.__version__ if _np is not None else None),
        cuda_available=cuda,
        mps_available=mps,
    )


def resolve_device(device: str = "auto") -> str:
    """Resolve a device string: ``auto`` -> cuda > mps > cpu (falls back to cpu without torch)."""
    if device != "auto":
        return device
    if _torch is None:
        return "cpu"
    if _torch.cuda.is_available():
        return "cuda"
    if hasattr(_torch.backends, "mps") and _torch.backends.mps.is_available():
        return "mps"
    return "cpu"
