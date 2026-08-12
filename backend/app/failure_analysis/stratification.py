"""Stratified failure summaries (Milestone 9).

Aggregates failures by **true class**, **error type**, and **sample group** so failures are directly
visible per stratum (thin cloud always exposed for CloudSEN12). Standard-library only.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from app.failure_analysis.config import FailureAnalysisConfig
from app.failure_analysis.records import ErrorRecord, FailureSummary, SampleFailure
from app.failure_analysis.taxonomy import FailureCategory

_MEASURABLE_ERROR_TYPES = (
    FailureCategory.FALSE_NEGATIVE.value,
    FailureCategory.FALSE_POSITIVE.value,
    FailureCategory.CLASS_CONFUSION.value,
)


def class_summaries(config: FailureAnalysisConfig, pixel_errors: list[ErrorRecord],
                    sample_failures: list[SampleFailure]) -> list[FailureSummary]:
    """Per (true) class failure summary — thin cloud is always present for multiclass."""
    fn_by_class = {e.class_name: e for e in pixel_errors
                   if e.error_type == FailureCategory.FALSE_NEGATIVE.value}
    summaries: list[FailureSummary] = []
    for name in config.class_names:
        fn = fn_by_class.get(name)
        total_errors = fn.error_count if fn else 0
        error_rate = fn.error_rate if fn else None
        samples = [s for s in sample_failures if s.per_class_errors.get(name, 0) > 0]
        sev = Counter(s.severity for s in samples)
        summaries.append(FailureSummary(
            key=name, stratum_type="class", total_errors=total_errors, sample_count=len(samples),
            error_rate=error_rate, severity_distribution=dict(sev)))
    return summaries


def error_type_summaries(pixel_errors: list[ErrorRecord],
                         sample_failures: list[SampleFailure]) -> list[FailureSummary]:
    """Summary per measurable error type (FN / FP / class confusion)."""
    summaries: list[FailureSummary] = []
    for etype in _MEASURABLE_ERROR_TYPES:
        total = sum(e.error_count for e in pixel_errors if e.error_type == etype)
        n_samples = sum(1 for s in sample_failures if etype in s.categories)
        summaries.append(FailureSummary(key=etype, stratum_type="error_type",
                                        total_errors=total, sample_count=n_samples))
    return summaries


def group_summaries(sample_failures: list[SampleFailure]) -> list[FailureSummary]:
    """Summary per sample group (dataset/split/region/season)."""
    by_group: dict[str, list[SampleFailure]] = defaultdict(list)
    for s in sample_failures:
        by_group[s.group or "_ungrouped"].append(s)
    summaries: list[FailureSummary] = []
    for group in sorted(by_group):
        items = by_group[group]
        total_errors = sum(s.error_count for s in items)
        total_pixels = sum(s.total_pixels for s in items)
        rate = (total_errors / total_pixels) if total_pixels > 0 else None
        sev = Counter(s.severity for s in items)
        summaries.append(FailureSummary(key=group, stratum_type="group", total_errors=total_errors,
                                        sample_count=len(items), error_rate=rate,
                                        severity_distribution=dict(sev)))
    return summaries
