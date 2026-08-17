"""Failure-behaviour comparison (Milestone 11).

Summarises each arm's M9 :class:`FailureAnalysisResult` into a compact :class:`FailureArmSummary` and
compares them — reusing M9 outputs, **never re-implementing failure analysis**. The architectural
hypothesis ("attention gates improve difficult thin-cloud discrimination") is only marked *supported* when
the evidence is real (MEASURED); on synthetic data it stays ``None`` (NOT YET MEASURED). Standard-lib only.
"""

from __future__ import annotations

from collections import Counter

from app.comparison.records import (
    MEASURED,
    NOT_YET_MEASURED,
    FailureArmSummary,
    FailureComparison,
)
from app.core.constants import CloudClass
from app.failure_analysis.records import FailureAnalysisResult
from app.failure_analysis.taxonomy import FailureCategory

_THIN_CLOUD = CloudClass.THIN_CLOUD.name.lower()


def _error_type_total(result: FailureAnalysisResult, etype: str) -> int:
    for s in result.error_type_summaries:
        if s.key == etype:
            return s.total_errors
    return 0


def _thin_cloud_failures(result: FailureAnalysisResult) -> int:
    """Thin-cloud failures = thin-cloud false-negative pixels (from the class summary)."""
    for s in result.class_summaries:
        if s.key == _THIN_CLOUD:
            return s.total_errors
    return 0


def _top_categories(result: FailureAnalysisResult, k: int = 5) -> list[dict]:
    """Top-K failure categories by total error count (error-type + per-class strata)."""
    rows = [{"category": s.key, "type": s.stratum_type, "total_errors": s.total_errors}
            for s in (list(result.error_type_summaries) + list(result.class_summaries))
            if s.total_errors > 0]
    rows.sort(key=lambda r: (-r["total_errors"], r["category"]))
    return rows[:k]


def summarize_arm(result: FailureAnalysisResult, *, top_k: int = 5,
                  status: str = NOT_YET_MEASURED) -> FailureArmSummary:
    """Extract a compact :class:`FailureArmSummary` from a full M9 result."""
    fn = _error_type_total(result, FailureCategory.FALSE_NEGATIVE.value)
    fp = _error_type_total(result, FailureCategory.FALSE_POSITIVE.value)
    cc = _error_type_total(result, FailureCategory.CLASS_CONFUSION.value)

    if result.sample_failures:
        total = len(result.sample_failures)
        severity = dict(Counter(s.severity for s in result.sample_failures))
    else:
        total = fn                                   # pixel-level: total misclassified (FN) pixels
        severity = dict(Counter(e.severity for e in result.pixel_errors))

    return FailureArmSummary(
        total_failures=total, thin_cloud_failures=_thin_cloud_failures(result),
        false_positives=fp, false_negatives=fn, class_confusion=cc,
        severity_distribution=severity, top_categories=_top_categories(result, top_k), status=status)


def compare_failures(baseline: FailureAnalysisResult, improved: FailureAnalysisResult, *,
                     top_k: int = 5, status: str = NOT_YET_MEASURED,
                     hypothesis: str = "Attention gates improve difficult thin-cloud discrimination.",
                     ) -> FailureComparison:
    """Compare both arms' failure behaviour and (only when MEASURED) rule on the hypothesis."""
    b = summarize_arm(baseline, top_k=top_k, status=status)
    i = summarize_arm(improved, top_k=top_k, status=status)

    thin_delta = i.thin_cloud_failures - b.thin_cloud_failures
    total_delta = i.total_failures - b.total_failures

    # The hypothesis is only ruled on with real evidence; on synthetic data it is NOT YET MEASURED.
    supported: bool | None = None
    if status == MEASURED:
        supported = (thin_delta < 0) and (i.false_negatives <= b.false_negatives)

    return FailureComparison(
        baseline=b, improved=i, hypothesis=hypothesis, hypothesis_supported=supported,
        thin_cloud_failure_delta=thin_delta, total_failure_delta=total_delta, status=status)
