"""Improvement decision framework (Milestone 11).

Turns the quality / failure / compute comparisons into an **explicit, defensible verdict** — never
"higher overall accuracy wins". Thin-cloud behaviour is the primary signal; a stronger aggregate that hides
thin-cloud degradation is a REGRESSION, and a small thin-cloud gain that costs a lot of compute is
COMPUTE_UNJUSTIFIED. Without real controlled results the verdict is always INCONCLUSIVE (section 21).
Standard-library only.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from app.comparison.records import MEASURED, NOT_MEASURED

# Data-regime labels (a comparison is either on REAL data or SYNTHETIC / VALIDATION ONLY data).
REAL_DATA = "REAL"
SYNTHETIC_DATA = "SYNTHETIC"


class DecisionOutcome(str, enum.Enum):
    """Possible controlled-comparison verdicts."""

    IMPROVED = "IMPROVED"
    NO_SIGNIFICANT_IMPROVEMENT = "NO_SIGNIFICANT_IMPROVEMENT"
    REGRESSION = "REGRESSION"
    INCONCLUSIVE = "INCONCLUSIVE"
    COMPUTE_UNJUSTIFIED = "COMPUTE_UNJUSTIFIED"


@dataclass(frozen=True)
class DecisionThresholds:
    """Tolerances for calling a change meaningful (IoU points, compute cost factor)."""

    thin_cloud_min_delta: float = 0.01       # min thin-cloud IoU gain to count as an improvement
    macro_min_delta: float = 0.01            # min macro IoU gain to count as an improvement
    regression_delta: float = 0.01           # thin-cloud/worst-class drop beyond this = regression
    compute_cost_factor: float = 1.5         # improved costs > factor x baseline = "substantial"
    small_gain_delta: float = 0.03           # a thin-cloud gain below this is "slight"
    min_seeds_for_significance: int = 2      # fewer seeds => uncertainty NOT MEASURED

    def to_dict(self) -> dict[str, Any]:
        return {
            "thin_cloud_min_delta": self.thin_cloud_min_delta, "macro_min_delta": self.macro_min_delta,
            "regression_delta": self.regression_delta, "compute_cost_factor": self.compute_cost_factor,
            "small_gain_delta": self.small_gain_delta,
            "min_seeds_for_significance": self.min_seeds_for_significance,
        }


@dataclass
class ComparisonDecision:
    """The verdict + the evidence that produced it."""

    outcome: str
    rationale: list[str] = field(default_factory=list)
    thin_cloud_iou_delta: float | None = None
    macro_iou_delta: float | None = None
    worst_class_iou_delta: float | None = None
    parameter_ratio: float | None = None
    training_time_ratio: float | None = None
    seeds_executed: int = 0
    uncertainty_status: str = NOT_MEASURED
    data_regime: str = SYNTHETIC_DATA
    thresholds: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome, "rationale": list(self.rationale),
            "thin_cloud_iou_delta": self.thin_cloud_iou_delta, "macro_iou_delta": self.macro_iou_delta,
            "worst_class_iou_delta": self.worst_class_iou_delta,
            "parameter_ratio": self.parameter_ratio, "training_time_ratio": self.training_time_ratio,
            "seeds_executed": self.seeds_executed, "uncertainty_status": self.uncertainty_status,
            "data_regime": self.data_regime, "thresholds": self.thresholds,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ComparisonDecision":
        return cls(
            outcome=d.get("outcome", DecisionOutcome.INCONCLUSIVE.value),
            rationale=list(d.get("rationale", []) or []),
            thin_cloud_iou_delta=d.get("thin_cloud_iou_delta"),
            macro_iou_delta=d.get("macro_iou_delta"),
            worst_class_iou_delta=d.get("worst_class_iou_delta"),
            parameter_ratio=d.get("parameter_ratio"), training_time_ratio=d.get("training_time_ratio"),
            seeds_executed=int(d.get("seeds_executed", 0)),
            uncertainty_status=d.get("uncertainty_status", NOT_MEASURED),
            data_regime=d.get("data_regime", SYNTHETIC_DATA), thresholds=dict(d.get("thresholds", {}) or {}))


def _worst_class_delta(metric: Any) -> float | None:
    """IoU delta of the baseline's worst class (does the weakest class get better or worse?)."""
    worst = getattr(metric, "worst_class_baseline", None)
    if not worst:
        return None
    for c in metric.per_class:
        if c.class_name == worst:
            return c.delta.get("iou")
    return None


def decide(metric: Any, failure: Any, compute: Any, *, data_regime: str = SYNTHETIC_DATA,
           seeds_executed: int = 0, thresholds: DecisionThresholds | None = None) -> ComparisonDecision:
    """Produce a :class:`ComparisonDecision` from the three comparison records.

    Args:
        metric: :class:`~app.comparison.records.MetricComparison`.
        failure: :class:`~app.comparison.records.FailureComparison`.
        compute: :class:`~app.comparison.records.ComputeComparison`.
        data_regime: ``"REAL"`` or ``"SYNTHETIC"``.
        seeds_executed: number of seed rows actually run (for uncertainty).
        thresholds: decision tolerances.
    """
    th = thresholds or DecisionThresholds()
    thin = metric.thin_cloud
    thin_delta = thin.iou_delta
    macro_delta = (metric.macro_delta or {}).get("iou")
    worst_delta = _worst_class_delta(metric)
    param_ratio = compute.parameter_ratio if compute else None
    time_ratio = compute.training_time_ratio if compute else None
    uncertainty = MEASURED if seeds_executed >= th.min_seeds_for_significance else NOT_MEASURED

    base = ComparisonDecision(
        outcome=DecisionOutcome.INCONCLUSIVE.value, thin_cloud_iou_delta=thin_delta,
        macro_iou_delta=macro_delta, worst_class_iou_delta=worst_delta, parameter_ratio=param_ratio,
        training_time_ratio=time_ratio, seeds_executed=seeds_executed, uncertainty_status=uncertainty,
        data_regime=data_regime, thresholds=th.to_dict())

    # 1) No real controlled results -> INCONCLUSIVE (never a guessed winner). Section 21.
    if data_regime != REAL_DATA or metric.status != MEASURED:
        base.rationale = [
            "Real controlled training + evaluation NOT YET MEASURED (real dataset unavailable / "
            "results are SYNTHETIC / VALIDATION ONLY).",
            "Per section 21 the verdict must be INCONCLUSIVE — no winner is inferred from synthetic runs.",
        ]
        return base

    # 2) Not enough evidence to compare thin-cloud (the primary metric) -> INCONCLUSIVE.
    if thin_delta is None or macro_delta is None:
        base.rationale = ["Thin-cloud or macro IoU is undefined for one arm — cannot compare."]
        return base

    if seeds_executed < 1:
        base.rationale = ["No seed rows executed — nothing to decide."]
        return base

    rationale: list[str] = [f"Thin-cloud IoU delta (improved-baseline) = {thin_delta:+.4f}.",
                            f"Macro IoU delta = {macro_delta:+.4f}."]
    if uncertainty == NOT_MEASURED:
        rationale.append(f"Only {seeds_executed} seed(s) run — statistical significance NOT MEASURED.")

    # 3) Thin-cloud regressed materially -> REGRESSION even if the aggregate improved (thin-cloud primary).
    thin_regressed = thin_delta <= -th.regression_delta or bool(thin.regressed)
    worst_regressed = worst_delta is not None and worst_delta <= -th.regression_delta
    if thin_regressed or worst_regressed:
        if macro_delta > 0:
            rationale.append(
                "Aggregate improved but the primary thin-cloud (or worst) class regressed — "
                "this is NOT an improvement (section 10).")
        rationale.append("Verdict: REGRESSION on the primary difficult class.")
        base.outcome = DecisionOutcome.REGRESSION.value
        base.rationale = rationale
        return base

    # 4) Thin-cloud improved beyond tolerance.
    if thin_delta >= th.thin_cloud_min_delta and macro_delta >= -th.macro_min_delta:
        substantial_cost = ((param_ratio is not None and param_ratio > th.compute_cost_factor)
                            or (time_ratio is not None and time_ratio > th.compute_cost_factor))
        slight_gain = thin_delta < th.small_gain_delta
        if substantial_cost and slight_gain:
            rationale.append(
                f"Thin-cloud gain is slight ({thin_delta:+.4f}) but compute cost is substantial "
                f"(param x{param_ratio}, time x{time_ratio}) — trade-off not justified.")
            base.outcome = DecisionOutcome.COMPUTE_UNJUSTIFIED.value
            base.rationale = rationale
            return base
        rationale.append("Thin-cloud and aggregate both improved at acceptable compute cost.")
        base.outcome = DecisionOutcome.IMPROVED.value
        base.rationale = rationale
        return base

    # 5) Everything roughly flat -> no significant improvement.
    rationale.append("Neither thin-cloud nor aggregate improved beyond tolerance.")
    base.outcome = DecisionOutcome.NO_SIGNIFICANT_IMPROVEMENT.value
    base.rationale = rationale
    return base
