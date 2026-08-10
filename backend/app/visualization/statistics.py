"""Exploratory statistics (Milestone 5).

Deterministic, serialisable statistics computed from **preprocessing records** (not raw dicts). Standard-
library only — no numpy/plotting required. Covers class distribution, dataset, patch, and split summaries.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

from app.preprocessing.records import PatchRecord, SampleRecord


@dataclass
class ClassDistribution:
    """Per-class pixel/sample counts with frequencies and a balance ratio."""

    counts: dict[int, int] = field(default_factory=dict)

    @classmethod
    def from_counts(cls, counts: dict[int, int]) -> "ClassDistribution":
        # Normalise keys to int and order deterministically.
        return cls(counts={int(k): int(v) for k, v in sorted(counts.items())})

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def frequencies(self) -> dict[int, float]:
        total = self.total
        if total == 0:
            return {k: 0.0 for k in self.counts}
        return {k: v / total for k, v in self.counts.items()}

    def balance_ratio(self) -> float:
        """min/max class count in [0, 1]; 1.0 = perfectly balanced, 0.0 = a class is absent."""
        values = list(self.counts.values())
        if not values or max(values) == 0:
            return 0.0
        return min(values) / max(values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "counts": self.counts,
            "frequencies": self.frequencies(),
            "total": self.total,
            "balance_ratio": self.balance_ratio(),
        }


@dataclass
class DatasetStatistics:
    """Summary statistics for a dataset."""

    dataset: str
    num_samples: int = 0
    num_missing_labels: int = 0
    num_invalid_files: int = 0
    num_duplicate_ids: int = 0
    num_unsupported_files: int = 0
    image_size_counts: dict[str, int] = field(default_factory=dict)   # "HxW" -> count
    class_distribution: ClassDistribution | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "num_samples": self.num_samples,
            "num_missing_labels": self.num_missing_labels,
            "num_invalid_files": self.num_invalid_files,
            "num_duplicate_ids": self.num_duplicate_ids,
            "num_unsupported_files": self.num_unsupported_files,
            "image_size_counts": self.image_size_counts,
            "class_distribution": self.class_distribution.to_dict() if self.class_distribution else None,
        }


def compute_dataset_statistics(
    dataset: str,
    samples: Iterable[SampleRecord],
    *,
    validation_summary: Any | None = None,
    image_sizes: dict[str, tuple[int, int]] | None = None,
    class_counts: dict[int, int] | None = None,
) -> DatasetStatistics:
    """Compute deterministic dataset statistics from records.

    Args:
        dataset: Dataset id.
        samples: Discovered samples.
        validation_summary: Optional ``ValidationSummary`` to source invalid/missing/duplicate counts.
        image_sizes: Optional mapping ``sample_id -> (H, W)`` (from raster metadata) for a size histogram.
        class_counts: Optional pre-computed class pixel/sample counts (framework — not computed over real
            data in this milestone).
    """
    samples = list(samples)
    stats = DatasetStatistics(dataset=dataset, num_samples=len(samples))

    if validation_summary is not None:
        stats.num_missing_labels = getattr(validation_summary, "missing_labels", 0)
        stats.num_invalid_files = getattr(validation_summary, "missing_files", 0)
        stats.num_duplicate_ids = getattr(validation_summary, "duplicate_ids", 0)
        stats.num_unsupported_files = getattr(validation_summary, "unsupported_files", 0)
    else:
        stats.num_missing_labels = sum(1 for s in samples if s.label_path is None)

    if image_sizes:
        counter: Counter[str] = Counter(f"{h}x{w}" for (h, w) in image_sizes.values())
        stats.image_size_counts = dict(sorted(counter.items()))

    if class_counts:
        stats.class_distribution = ClassDistribution.from_counts(class_counts)

    return stats


@dataclass
class PatchStatistics:
    """Summary statistics for generated patches (from a patch manifest)."""

    num_patches: int = 0
    patch_size: int | None = None
    overlap: int | None = None
    per_split: dict[str, int] = field(default_factory=dict)
    per_sample: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_records(cls, records: Iterable[PatchRecord]) -> "PatchStatistics":
        records = list(records)
        per_split = Counter(r.split for r in records)
        per_sample = Counter(r.sample_id for r in records)
        patch_size = records[0].patch_size if records else None
        overlap = records[0].overlap if records else None
        return cls(
            num_patches=len(records),
            patch_size=patch_size,
            overlap=overlap,
            per_split=dict(sorted(per_split.items())),
            per_sample=dict(sorted(per_sample.items())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_patches": self.num_patches,
            "patch_size": self.patch_size,
            "overlap": self.overlap,
            "per_split": self.per_split,
            "per_sample": self.per_sample,
        }


@dataclass
class SplitStatistics:
    """Summary statistics for a train/val/test split."""

    counts: dict[str, int] = field(default_factory=dict)
    ratios: dict[str, float] = field(default_factory=dict)
    seed: int | None = None
    grouped: bool = False

    @classmethod
    def from_manifest(cls, manifest: Any) -> "SplitStatistics":
        """Build from a :class:`app.preprocessing.splitting.SplitManifest`."""
        d = manifest.to_dict()
        return cls(counts=d["counts"], ratios=d["ratios"], seed=d.get("seed"), grouped=d.get("grouped", False))

    def to_dict(self) -> dict[str, Any]:
        return {"counts": self.counts, "ratios": self.ratios, "seed": self.seed, "grouped": self.grouped}
