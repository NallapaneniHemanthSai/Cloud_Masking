"""Failure analysis / confusing-case evaluation (Milestone 9).

Explains model failures on top of the M8 evaluation primitives — **it does not recompute M8 metrics**. It
categorises errors (typed taxonomy with measurability), computes pixel- and sample-level error statistics,
ranks the hardest cases deterministically, stratifies failures (thin cloud always visible), and emits
reports + backend-independent visualization specs. Categories needing unavailable data (confidence, spatial
masks) are marked **DEFERRED / NOT MEASURABLE**, never fabricated (ADR-0009). No model/training/inference/
deployment/API/frontend code. numpy is guarded (needed only for sample-level array analysis).

Public surface:

* Taxonomy/severity: :class:`FailureCategory`, :class:`Measurability`, :class:`Severity`,
  :data:`CATEGORY_MEASURABILITY`, :func:`taxonomy_table`.
* Config: :class:`FailureAnalysisConfig`, :class:`SeverityThresholds`.
* Records: :class:`ErrorRecord`, :class:`SampleFailure`, :class:`HardExample`, :class:`FailureSummary`,
  :class:`FailureGroup`, :class:`FailureAnalysisResult`.
* Analysis: :func:`analyze_failures`, :func:`analyze_pixels`, :func:`analyze_samples`,
  :func:`rank_samples`, :func:`top_k`, :func:`dedup_by_sample`.
* Stratification/report/viz: :func:`class_summaries`, :func:`build_failure_report`,
  :func:`export_failure_report`, :func:`confusing_case_specs`.
"""

from app.failure_analysis.analyzer import analyze_failures
from app.failure_analysis.config import FailureAnalysisConfig, SeverityThresholds
from app.failure_analysis.pixel_analysis import analyze_pixels
from app.failure_analysis.ranking import dedup_by_sample, rank_samples, top_k
from app.failure_analysis.records import (
    ErrorRecord,
    FailureAnalysisResult,
    FailureGroup,
    FailureSummary,
    HardExample,
    SampleFailure,
)
from app.failure_analysis.report import build_failure_report, export_failure_report
from app.failure_analysis.sample_analysis import analyze_sample, analyze_samples
from app.failure_analysis.stratification import (
    class_summaries,
    error_type_summaries,
    group_summaries,
)
from app.failure_analysis.taxonomy import (
    CATEGORY_MEASURABILITY,
    FailureCategory,
    Measurability,
    Severity,
    taxonomy_table,
)
from app.failure_analysis.viz_specs import confusing_case_specs

__all__ = [
    "FailureCategory",
    "Measurability",
    "Severity",
    "CATEGORY_MEASURABILITY",
    "taxonomy_table",
    "FailureAnalysisConfig",
    "SeverityThresholds",
    "ErrorRecord",
    "SampleFailure",
    "HardExample",
    "FailureSummary",
    "FailureGroup",
    "FailureAnalysisResult",
    "analyze_failures",
    "analyze_pixels",
    "analyze_sample",
    "analyze_samples",
    "rank_samples",
    "dedup_by_sample",
    "top_k",
    "class_summaries",
    "error_type_summaries",
    "group_summaries",
    "build_failure_report",
    "export_failure_report",
    "confusing_case_specs",
]
