"""Preprocessing configuration (Milestone 4).

Declares the tunable preprocessing parameters (patch size, overlap, normalization mode, augmentation
toggle, random seed, split ratios) with validation. Standard-library only; defaults come from
``app.core.constants`` so no magic numbers are hardcoded in the modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.constants import (
    DEFAULT_NORMALIZATION_MODE,
    DEFAULT_PATCH_OVERLAP,
    DEFAULT_PATCH_SIZE,
    DEFAULT_RANDOM_SEED,
    DEFAULT_SPLIT_RATIOS,
    SPLIT_RATIO_TOLERANCE,
    NormalizationMode,
)
from app.core.exceptions import ConfigurationError

try:  # PyYAML is declared in requirements.in but may not be installed on a bare interpreter.
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


@dataclass(frozen=True)
class SplitRatios:
    """Train / validation / test split ratios (must sum to ~1.0)."""

    train: float = DEFAULT_SPLIT_RATIOS[0]
    val: float = DEFAULT_SPLIT_RATIOS[1]
    test: float = DEFAULT_SPLIT_RATIOS[2]

    def validate(self) -> None:
        """Raise :class:`ConfigurationError` if the ratios are invalid."""
        for name, value in (("train", self.train), ("val", self.val), ("test", self.test)):
            if value < 0:
                raise ConfigurationError(f"Split ratio '{name}' must be non-negative, got {value}.")
        total = self.train + self.val + self.test
        if abs(total - 1.0) > SPLIT_RATIO_TOLERANCE:
            raise ConfigurationError(f"Split ratios must sum to 1.0, got {total}.")

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.train, self.val, self.test)


@dataclass(frozen=True)
class PreprocessingConfig:
    """Validated preprocessing parameters.

    Attributes:
        patch_size: Square patch edge length in pixels (> 0).
        overlap: Overlap between adjacent patches in pixels (0 <= overlap < patch_size).
        normalization_mode: One of :class:`NormalizationMode` values.
        augmentation_enabled: Whether the augmentation framework is active downstream.
        random_seed: Deterministic seed for splitting/shuffling.
        split_ratios: Train/val/test ratios.
        group_by: Optional grouping key name for leakage-resistant (spatial) splitting.
        nodata_value: Optional sentinel value treated as missing during normalization.
    """

    patch_size: int = DEFAULT_PATCH_SIZE
    overlap: int = DEFAULT_PATCH_OVERLAP
    normalization_mode: str = DEFAULT_NORMALIZATION_MODE
    augmentation_enabled: bool = False
    random_seed: int = DEFAULT_RANDOM_SEED
    split_ratios: SplitRatios = field(default_factory=SplitRatios)
    group_by: str | None = None
    nodata_value: float | None = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.patch_size <= 0:
            raise ConfigurationError(f"patch_size must be > 0, got {self.patch_size}.")
        if not (0 <= self.overlap < self.patch_size):
            raise ConfigurationError(
                f"overlap must satisfy 0 <= overlap < patch_size ({self.patch_size}), got {self.overlap}."
            )
        valid_modes = {m.value for m in NormalizationMode}
        if self.normalization_mode not in valid_modes:
            raise ConfigurationError(
                f"normalization_mode must be one of {sorted(valid_modes)}, got {self.normalization_mode!r}."
            )
        self.split_ratios.validate()

    @property
    def stride(self) -> int:
        """Patch step size (patch_size minus overlap)."""
        return self.patch_size - self.overlap

    # --- Construction ------------------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PreprocessingConfig":
        """Build from a plain mapping (e.g. parsed YAML ``preprocessing`` section)."""
        data = dict(data or {})
        ratios_data = data.pop("split_ratios", None)
        if isinstance(ratios_data, dict):
            ratios = SplitRatios(
                train=float(ratios_data.get("train", DEFAULT_SPLIT_RATIOS[0])),
                val=float(ratios_data.get("val", DEFAULT_SPLIT_RATIOS[1])),
                test=float(ratios_data.get("test", DEFAULT_SPLIT_RATIOS[2])),
            )
        else:
            ratios = SplitRatios()
        allowed = {
            "patch_size", "overlap", "normalization_mode", "augmentation_enabled",
            "random_seed", "group_by", "nodata_value",
        }
        kwargs = {k: v for k, v in data.items() if k in allowed}
        return cls(split_ratios=ratios, **kwargs)

    @classmethod
    def from_yaml(cls, path: Path, section: str = "preprocessing") -> "PreprocessingConfig":
        """Load the ``preprocessing`` section from a YAML config file."""
        if yaml is None:
            raise ConfigurationError(
                "PyYAML is required to load preprocessing config from YAML but is not installed."
            )
        path = Path(path)
        if not path.is_file():
            raise ConfigurationError(f"Config file not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.from_dict(raw.get(section, {}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "patch_size": self.patch_size,
            "overlap": self.overlap,
            "normalization_mode": self.normalization_mode,
            "augmentation_enabled": self.augmentation_enabled,
            "random_seed": self.random_seed,
            "group_by": self.group_by,
            "nodata_value": self.nodata_value,
            "split_ratios": {
                "train": self.split_ratios.train,
                "val": self.split_ratios.val,
                "test": self.split_ratios.test,
            },
        }
