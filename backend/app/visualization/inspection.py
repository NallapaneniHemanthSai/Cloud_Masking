"""Dataset inspection (Milestone 5).

Combines discovery + validation + statistics into a single structured, serialisable
:class:`DatasetInspectionReport`. Uses preprocessing records (``SampleRecord``, ``ValidationReport``) — no
raw dictionaries as interfaces. Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.preprocessing.records import SampleRecord
from app.preprocessing.validation import ValidationReport, ValidationSummary, validate_samples
from app.visualization.statistics import (
    ClassDistribution,
    DatasetStatistics,
    compute_dataset_statistics,
)


@dataclass
class DatasetInspectionReport:
    """A structured dataset inspection result."""

    dataset: str
    statistics: DatasetStatistics
    validation_summary: ValidationSummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "statistics": self.statistics.to_dict(),
            "validation_summary": self.validation_summary.to_dict(),
        }


def inspect_dataset(
    dataset: str,
    samples: Iterable[SampleRecord],
    *,
    validation_report: ValidationReport | None = None,
    image_sizes: dict[str, tuple[int, int]] | None = None,
    class_counts: dict[int, int] | None = None,
) -> DatasetInspectionReport:
    """Inspect a dataset from discovered samples.

    Args:
        dataset: Dataset id.
        samples: Discovered :class:`SampleRecord`s.
        validation_report: Optional precomputed report; otherwise a path/type/id validation is run.
        image_sizes: Optional ``sample_id -> (H, W)`` for a size histogram.
        class_counts: Optional class counts for a class distribution (framework only).

    Returns:
        A :class:`DatasetInspectionReport`.
    """
    samples = list(samples)
    report = validation_report if validation_report is not None else validate_samples(samples)
    summary = report.summary()
    stats = compute_dataset_statistics(
        dataset, samples,
        validation_summary=summary, image_sizes=image_sizes, class_counts=class_counts,
    )
    return DatasetInspectionReport(dataset=dataset, statistics=stats, validation_summary=summary)


def class_distribution_from_counts(counts: dict[int, int]) -> ClassDistribution:
    """Convenience re-export used by callers that only need a class distribution."""
    return ClassDistribution.from_counts(counts)
