"""Evaluation framework (Milestone 8).

Confusion-matrix-based, **per-class-first** segmentation evaluation — designed so a strong overall score
can never conceal poor per-class (especially thin-cloud) performance (ADR-0008). Reports overall,
per-class, macro, micro, and weighted metrics + confusion matrix + stratified results, with **explicit
undefined values** (never misleading zeros). No model/training/inference/deployment/API code. numpy is a
guarded optional dependency (needed only to accumulate/argmax arrays; the metric math is pure-stdlib).

Public surface:

* Config: :class:`EvaluationConfig`, :class:`EvaluationMode`.
* Records: :class:`MetricValue`, :class:`ClassMetrics`, :class:`ConfusionMatrix`,
  :class:`EvaluationResult`, :class:`EvaluationSummary`, :class:`StratifiedResult`, :class:`EvaluationRun`.
* Compute: :class:`EvaluationRunner`, :func:`build_result`, metric functions, :func:`compute_aggregates`.
* Stratified: :func:`stratified_evaluation`, :func:`class_view`.
* Binary (opt-in): :func:`collapse_to_binary`.
* Reporting/serialization/summary: :func:`build_evaluation_report`, :func:`export_evaluation_report`,
  :func:`save_evaluation_run`, :func:`load_evaluation_run`, :func:`build_summary`.
"""

from app.evaluation.aggregation import compute_aggregates, macro_average, micro_metrics, weighted_average
from app.evaluation.binary import collapse_to_binary
from app.evaluation.config import (
    CLOUDSEN12_CLASS_NAMES,
    ON_CLOUD_N_CLASS_NAMES,
    EvaluationConfig,
    EvaluationMode,
)
from app.evaluation.confusion import ConfusionMatrix
from app.evaluation.metrics import compute_class_metrics, pixel_accuracy
from app.evaluation.records import (
    METRIC_NAMES,
    ClassMetrics,
    EvaluationResult,
    EvaluationRun,
    EvaluationSummary,
    MetricValue,
    StratifiedResult,
)
from app.evaluation.report import build_evaluation_report, export_evaluation_report
from app.evaluation.runner import EvaluationRunner, argmax_labels, build_result
from app.evaluation.serialization import load_evaluation_run, save_evaluation_run
from app.evaluation.stratification import class_view, stratified_evaluation, stratified_from_confusions
from app.evaluation.summary import build_summary

__all__ = [
    "EvaluationConfig",
    "EvaluationMode",
    "CLOUDSEN12_CLASS_NAMES",
    "ON_CLOUD_N_CLASS_NAMES",
    "MetricValue",
    "ClassMetrics",
    "ConfusionMatrix",
    "EvaluationResult",
    "EvaluationSummary",
    "StratifiedResult",
    "EvaluationRun",
    "METRIC_NAMES",
    "EvaluationRunner",
    "build_result",
    "argmax_labels",
    "compute_class_metrics",
    "pixel_accuracy",
    "compute_aggregates",
    "macro_average",
    "micro_metrics",
    "weighted_average",
    "stratified_evaluation",
    "stratified_from_confusions",
    "class_view",
    "collapse_to_binary",
    "build_evaluation_report",
    "export_evaluation_report",
    "save_evaluation_run",
    "load_evaluation_run",
    "build_summary",
]
