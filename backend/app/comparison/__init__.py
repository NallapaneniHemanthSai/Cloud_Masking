"""Controlled model comparison (Milestone 11).

A **controlled, honest** baseline-vs-improved comparison (U-Net vs Attention U-Net). Both arms are derived
from a single :class:`ComparisonConfig` so every control (dataset / preprocessing / split / seed / loss /
optimizer / scheduler / batch size / budget / augmentation / normalization) is identical — the model
architecture is the *only* intentional difference — and the fairness guardrails then re-verify this. The
runner **reuses** the M7 training engine, the M8 evaluation framework, and the M9 failure analyzer (no
second engine of any kind). Quality is separated from compute cost, thin-cloud behaviour is the primary
signal (never hidden by an aggregate), and every quantity keeps an honest measurement status:
``MEASURED`` / ``SYNTHETIC`` / ``NOT_MEASURED`` / ``NOT_YET_MEASURED``. Without real controlled results the
decision is always INCONCLUSIVE — no winner is fabricated. Standard-library only (torch guarded in the
runner).

Public surface:

* Config: :class:`ComparisonConfig`, :class:`ExperimentPlan`.
* Guardrails: :func:`check_fairness`, :func:`check_config_fairness`, :class:`FairnessReport`.
* Records: :class:`ComputeMeasurement`, :class:`ComputeComparison`, :class:`MetricComparison`,
  :class:`ThinCloudComparison`, :class:`ClassMetricDelta`, :class:`FailureComparison`,
  :class:`FailureArmSummary`, :class:`ExperimentRecord`, :class:`ModelComparisonArtifact`.
* Compare: :func:`compare_metrics`, :func:`extract_thin_cloud`, :func:`compare_failures`,
  :func:`summarize_arm`.
* Decision: :class:`DecisionOutcome`, :class:`ComparisonDecision`, :class:`DecisionThresholds`,
  :func:`decide`.
* Runner: :class:`ComparisonRunner`, :func:`run_synthetic_comparison`, :func:`real_data_available`,
  :class:`ComparisonResult`.
* Report/viz/serialization: :func:`build_comparison_report`, :func:`export_comparison_report`,
  :func:`comparison_viz_specs`, :func:`save_comparison_artifact`, :func:`load_comparison_artifact`.
"""

from app.comparison.config import DEFAULT_SEEDS, ComparisonConfig, ExperimentPlan
from app.comparison.decision import ComparisonDecision, DecisionOutcome, DecisionThresholds, decide
from app.comparison.failures import compare_failures, summarize_arm
from app.comparison.guardrails import (
    FairnessReport,
    FieldComparison,
    check_config_fairness,
    check_fairness,
)
from app.comparison.metrics import compare_metrics, extract_thin_cloud
from app.comparison.records import (
    DEFERRED,
    MEASURED,
    NOT_MEASURED,
    NOT_YET_MEASURED,
    SYNTHETIC,
    ClassMetricDelta,
    ComputeComparison,
    ComputeMeasurement,
    ExperimentRecord,
    FailureArmSummary,
    FailureComparison,
    MetricComparison,
    ModelComparisonArtifact,
    ThinCloudComparison,
)
from app.comparison.report import build_comparison_report, export_comparison_report
from app.comparison.runner import (
    ComparisonResult,
    ComparisonRunner,
    real_data_available,
    run_synthetic_comparison,
)
from app.comparison.serialization import load_comparison_artifact, save_comparison_artifact
from app.comparison.viz_specs import comparison_viz_specs

__all__ = [
    "ComparisonConfig",
    "ExperimentPlan",
    "DEFAULT_SEEDS",
    "check_fairness",
    "check_config_fairness",
    "FairnessReport",
    "FieldComparison",
    "ComputeMeasurement",
    "ComputeComparison",
    "MetricComparison",
    "ThinCloudComparison",
    "ClassMetricDelta",
    "FailureComparison",
    "FailureArmSummary",
    "ExperimentRecord",
    "ModelComparisonArtifact",
    "MEASURED",
    "NOT_MEASURED",
    "DEFERRED",
    "NOT_YET_MEASURED",
    "SYNTHETIC",
    "compare_metrics",
    "extract_thin_cloud",
    "compare_failures",
    "summarize_arm",
    "DecisionOutcome",
    "ComparisonDecision",
    "DecisionThresholds",
    "decide",
    "ComparisonRunner",
    "ComparisonResult",
    "run_synthetic_comparison",
    "real_data_available",
    "build_comparison_report",
    "export_comparison_report",
    "comparison_viz_specs",
    "save_comparison_artifact",
    "load_comparison_artifact",
]
