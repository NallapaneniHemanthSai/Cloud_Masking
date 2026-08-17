"""Experimental-dataset configuration (Milestone 12).

Strongly-typed, validated, serialisable configuration for building **one reproducible experimental
dataset** (curated subset + split + normalization + patching), with a deterministic config hash. Standard-
library only — importable without numpy/rasterio. It encodes the ADR-0012 decisions (primary dataset,
required classes incl. thin cloud, group-aware splitting, subset strategy) as data, never as magic numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import (
    DATASET_MANIFEST_VERSION,
    DEFAULT_NORMALIZATION_MODE,
    DEFAULT_PATCH_OVERLAP,
    DEFAULT_PATCH_SIZE,
    DEFAULT_RANDOM_SEED,
    DEFAULT_SPLIT_RATIOS,
    PREPROCESSING_VERSION,
    CloudClass,
)
from app.core.exceptions import ConfigurationError
from app.utils.hashing import stable_hash

#: Canonical CloudSEN12 class mapping (index -> name), from the verified constants.
CLOUDSEN12_CLASS_MAPPING: dict[int, str] = {int(c): c.name.lower() for c in CloudClass}
#: Class the pipeline must be able to evaluate separately (O2/O3). Never collapsed away.
THIN_CLOUD_NAME: str = CloudClass.THIN_CLOUD.name.lower()
#: Required classes for a valid multiclass experimental dataset.
REQUIRED_CLOUDSEN12_CLASSES: tuple[str, ...] = tuple(CLOUDSEN12_CLASS_MAPPING[i] for i in sorted(CLOUDSEN12_CLASS_MAPPING))


@dataclass(frozen=True)
class ExperimentalDatasetConfig:
    """Validated configuration for a reproducible experimental dataset."""

    dataset_id: str = "cloudsen12"
    dataset_version: str = ""                       # e.g. "cloudsen12plus-1.1.2" (+subset hash at build)
    preprocessing_version: str = PREPROCESSING_VERSION
    manifest_version: str = DATASET_MANIFEST_VERSION
    patch_size: int = DEFAULT_PATCH_SIZE
    overlap: int = DEFAULT_PATCH_OVERLAP
    normalization_mode: str = DEFAULT_NORMALIZATION_MODE
    band_count: int = 13
    class_count: int = 4
    class_mapping: dict[int, str] = field(default_factory=lambda: dict(CLOUDSEN12_CLASS_MAPPING))
    required_classes: tuple[str, ...] = REQUIRED_CLOUDSEN12_CLASSES
    thin_cloud_required: bool = True
    subset_size: int = 24                           # curated subset target (bounded by ADR-0002 / R-03)
    subset_strategy: str = "stratified_grouped"
    seed: int = DEFAULT_RANDOM_SEED
    split_ratios: tuple[float, float, float] = DEFAULT_SPLIT_RATIOS
    group_by: str = "scene"                         # group-aware splitting key (leakage prevention)
    spatial_resolution: str = "10 m (Sentinel-2)"
    nodata_value: float | None = None
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.patch_size <= 0:
            raise ConfigurationError(f"patch_size must be > 0, got {self.patch_size}.")
        if not (0 <= self.overlap < self.patch_size):
            raise ConfigurationError(
                f"overlap must satisfy 0 <= overlap < patch_size ({self.patch_size}), got {self.overlap}.")
        if self.class_count < 2:
            raise ConfigurationError(f"class_count must be >= 2, got {self.class_count}.")
        if self.subset_size <= 0:
            raise ConfigurationError(f"subset_size must be > 0, got {self.subset_size}.")
        if abs(sum(self.split_ratios) - 1.0) > 1e-6:
            raise ConfigurationError(f"split_ratios must sum to 1.0, got {self.split_ratios}.")
        if self.thin_cloud_required and THIN_CLOUD_NAME not in self.required_classes:
            raise ConfigurationError("thin_cloud_required=True but thin_cloud is not in required_classes.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id, "dataset_version": self.dataset_version,
            "preprocessing_version": self.preprocessing_version, "manifest_version": self.manifest_version,
            "patch_size": self.patch_size, "overlap": self.overlap,
            "normalization_mode": self.normalization_mode, "band_count": self.band_count,
            "class_count": self.class_count,
            "class_mapping": {str(k): v for k, v in self.class_mapping.items()},
            "required_classes": list(self.required_classes),
            "thin_cloud_required": self.thin_cloud_required, "subset_size": self.subset_size,
            "subset_strategy": self.subset_strategy, "seed": self.seed,
            "split_ratios": list(self.split_ratios), "group_by": self.group_by,
            "spatial_resolution": self.spatial_resolution, "nodata_value": self.nodata_value,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentalDatasetConfig":
        data = dict(data or {})
        cm = data.get("class_mapping")
        ratios = data.get("split_ratios")
        req = data.get("required_classes")
        return cls(
            dataset_id=data.get("dataset_id", "cloudsen12"),
            dataset_version=data.get("dataset_version", ""),
            preprocessing_version=data.get("preprocessing_version", PREPROCESSING_VERSION),
            manifest_version=data.get("manifest_version", DATASET_MANIFEST_VERSION),
            patch_size=int(data.get("patch_size", DEFAULT_PATCH_SIZE)),
            overlap=int(data.get("overlap", DEFAULT_PATCH_OVERLAP)),
            normalization_mode=data.get("normalization_mode", DEFAULT_NORMALIZATION_MODE),
            band_count=int(data.get("band_count", 13)), class_count=int(data.get("class_count", 4)),
            class_mapping={int(k): v for k, v in cm.items()} if cm else dict(CLOUDSEN12_CLASS_MAPPING),
            required_classes=tuple(req) if req else REQUIRED_CLOUDSEN12_CLASSES,
            thin_cloud_required=bool(data.get("thin_cloud_required", True)),
            subset_size=int(data.get("subset_size", 24)),
            subset_strategy=data.get("subset_strategy", "stratified_grouped"),
            seed=int(data.get("seed", DEFAULT_RANDOM_SEED)),
            split_ratios=tuple(ratios) if ratios else DEFAULT_SPLIT_RATIOS,
            group_by=data.get("group_by", "scene"),
            spatial_resolution=data.get("spatial_resolution", "10 m (Sentinel-2)"),
            nodata_value=data.get("nodata_value"),
            params=dict(data.get("params", {}) or {}),
        )

    def config_hash(self) -> str:
        """Deterministic hash of the configuration."""
        return stable_hash(self.to_dict())
