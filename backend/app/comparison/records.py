"""Typed comparison records (Milestone 11).

Strongly-typed, deterministically-serialisable records that separate **quality** from **compute cost** and
keep **honest measurement status** on every quantity. No raw tensors, no metric recomputation (metrics come
from M8, failures from M9, params from M6/M10). Standard-library only. The canonical
:class:`ModelComparisonArtifact` links both arms' model/training artifacts, evaluation/failure references,
compute measurements, and the decision, with deterministic content hashing (timestamps/notes ignored).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import COMPARISON_VERSION
from app.utils.hashing import stable_hash

# --- honest measurement-status labels (section 21) ------------------------------------------------
MEASURED = "MEASURED"
NOT_MEASURED = "NOT_MEASURED"
DEFERRED = "DEFERRED"
NOT_YET_MEASURED = "NOT_YET_MEASURED"          # awaiting real controlled experiments
SYNTHETIC = "SYNTHETIC"                         # produced, but on synthetic data — VALIDATION ONLY


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _delta(a: float | None, b: float | None) -> float | None:
    """improved - baseline, or None when either side is undefined."""
    if a is None or b is None:
        return None
    return round(b - a, 6)


# --------------------------------------------------------------------------------------------------
# Compute cost (section 8/9): actual measurements only — never inferred from parameter count.
# --------------------------------------------------------------------------------------------------
@dataclass
class ComputeMeasurement:
    """Per-arm computational-cost record. Parameters are MEASURED; timings MEASURED/SYNTHETIC; memory
    NOT_MEASURED unless reliably captured (never inferred)."""

    architecture: str
    device: str
    batch_size: int
    parameter_count: int | None = None
    trainable_parameter_count: int | None = None
    epochs_run: int = 0
    total_training_seconds: float | None = None
    avg_epoch_seconds: float | None = None
    inference_seconds: float | None = None
    peak_memory: str = NOT_MEASURED             # not inferred from params
    measurement_status: str = NOT_MEASURED
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "architecture": self.architecture, "device": self.device, "batch_size": self.batch_size,
            "parameter_count": self.parameter_count,
            "trainable_parameter_count": self.trainable_parameter_count,
            "epochs_run": self.epochs_run, "total_training_seconds": self.total_training_seconds,
            "avg_epoch_seconds": self.avg_epoch_seconds, "inference_seconds": self.inference_seconds,
            "peak_memory": self.peak_memory, "measurement_status": self.measurement_status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ComputeMeasurement":
        return cls(
            architecture=d.get("architecture", ""), device=d.get("device", ""),
            batch_size=int(d.get("batch_size", 0)), parameter_count=d.get("parameter_count"),
            trainable_parameter_count=d.get("trainable_parameter_count"),
            epochs_run=int(d.get("epochs_run", 0)),
            total_training_seconds=d.get("total_training_seconds"),
            avg_epoch_seconds=d.get("avg_epoch_seconds"), inference_seconds=d.get("inference_seconds"),
            peak_memory=d.get("peak_memory", NOT_MEASURED),
            measurement_status=d.get("measurement_status", NOT_MEASURED), notes=d.get("notes", ""))


@dataclass
class ComputeComparison:
    """Compute cost of ``improved`` relative to ``baseline`` (ratios/deltas; honest status)."""

    baseline: ComputeMeasurement
    improved: ComputeMeasurement
    parameter_ratio: float | None = None
    parameter_delta: int | None = None
    training_time_ratio: float | None = None
    inference_time_ratio: float | None = None
    status: str = NOT_MEASURED

    @classmethod
    def of(cls, baseline: ComputeMeasurement, improved: ComputeMeasurement) -> "ComputeComparison":
        def ratio(a: float | None, b: float | None) -> float | None:
            if a in (None, 0) or b is None:
                return None
            return round(b / a, 6)
        pdelta = (None if baseline.parameter_count is None or improved.parameter_count is None
                  else improved.parameter_count - baseline.parameter_count)
        status = MEASURED if MEASURED in (baseline.measurement_status, improved.measurement_status) else (
            SYNTHETIC if SYNTHETIC in (baseline.measurement_status, improved.measurement_status)
            else NOT_MEASURED)
        return cls(
            baseline=baseline, improved=improved,
            parameter_ratio=ratio(baseline.parameter_count, improved.parameter_count),
            parameter_delta=pdelta,
            training_time_ratio=ratio(baseline.total_training_seconds, improved.total_training_seconds),
            inference_time_ratio=ratio(baseline.inference_seconds, improved.inference_seconds),
            status=status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline": self.baseline.to_dict(), "improved": self.improved.to_dict(),
            "parameter_ratio": self.parameter_ratio, "parameter_delta": self.parameter_delta,
            "training_time_ratio": self.training_time_ratio,
            "inference_time_ratio": self.inference_time_ratio, "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ComputeComparison":
        return cls(
            baseline=ComputeMeasurement.from_dict(d.get("baseline", {})),
            improved=ComputeMeasurement.from_dict(d.get("improved", {})),
            parameter_ratio=d.get("parameter_ratio"), parameter_delta=d.get("parameter_delta"),
            training_time_ratio=d.get("training_time_ratio"),
            inference_time_ratio=d.get("inference_time_ratio"),
            status=d.get("status", NOT_MEASURED))


# --------------------------------------------------------------------------------------------------
# Quality comparison (section 6): per-class deltas + thin-cloud emphasis (never hidden by aggregates).
# --------------------------------------------------------------------------------------------------
@dataclass
class ClassMetricDelta:
    """Per-class metric values for both arms + improved-minus-baseline deltas."""

    class_name: str
    baseline: dict[str, float | None] = field(default_factory=dict)
    improved: dict[str, float | None] = field(default_factory=dict)
    delta: dict[str, float | None] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"class_name": self.class_name, "baseline": self.baseline,
                "improved": self.improved, "delta": self.delta}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ClassMetricDelta":
        return cls(class_name=d["class_name"], baseline=dict(d.get("baseline", {})),
                   improved=dict(d.get("improved", {})), delta=dict(d.get("delta", {})))


@dataclass
class ThinCloudComparison:
    """PRIMARY comparison target: thin-cloud IoU/Dice/Recall + false-negative behaviour."""

    baseline_iou: float | None = None
    improved_iou: float | None = None
    iou_delta: float | None = None
    baseline_dice: float | None = None
    improved_dice: float | None = None
    dice_delta: float | None = None
    baseline_recall: float | None = None
    improved_recall: float | None = None
    recall_delta: float | None = None
    baseline_false_negatives: int | None = None
    improved_false_negatives: int | None = None
    false_negative_delta: int | None = None
    regressed: bool | None = None                 # True if thin-cloud got worse (IoU/Dice down)
    status: str = NOT_YET_MEASURED

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_iou": self.baseline_iou, "improved_iou": self.improved_iou,
            "iou_delta": self.iou_delta, "baseline_dice": self.baseline_dice,
            "improved_dice": self.improved_dice, "dice_delta": self.dice_delta,
            "baseline_recall": self.baseline_recall, "improved_recall": self.improved_recall,
            "recall_delta": self.recall_delta,
            "baseline_false_negatives": self.baseline_false_negatives,
            "improved_false_negatives": self.improved_false_negatives,
            "false_negative_delta": self.false_negative_delta,
            "regressed": self.regressed, "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ThinCloudComparison":
        return cls(**{k: d.get(k) for k in (
            "baseline_iou", "improved_iou", "iou_delta", "baseline_dice", "improved_dice", "dice_delta",
            "baseline_recall", "improved_recall", "recall_delta", "baseline_false_negatives",
            "improved_false_negatives", "false_negative_delta", "regressed")},
            status=d.get("status", NOT_YET_MEASURED))


@dataclass
class MetricComparison:
    """Quality comparison of two M8 evaluation results (per-class + aggregate + thin-cloud + worst)."""

    baseline_summary: dict[str, Any] = field(default_factory=dict)   # EvaluationSummary.to_dict()
    improved_summary: dict[str, Any] = field(default_factory=dict)
    per_class: list[ClassMetricDelta] = field(default_factory=list)
    macro_delta: dict[str, float | None] = field(default_factory=dict)
    micro_delta: dict[str, float | None] = field(default_factory=dict)
    weighted_delta: dict[str, float | None] = field(default_factory=dict)
    thin_cloud: ThinCloudComparison = field(default_factory=ThinCloudComparison)
    worst_class_baseline: str | None = None
    worst_class_improved: str | None = None
    status: str = NOT_YET_MEASURED

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_summary": self.baseline_summary, "improved_summary": self.improved_summary,
            "per_class": [c.to_dict() for c in self.per_class],
            "macro_delta": self.macro_delta, "micro_delta": self.micro_delta,
            "weighted_delta": self.weighted_delta, "thin_cloud": self.thin_cloud.to_dict(),
            "worst_class_baseline": self.worst_class_baseline,
            "worst_class_improved": self.worst_class_improved, "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MetricComparison":
        return cls(
            baseline_summary=dict(d.get("baseline_summary", {}) or {}),
            improved_summary=dict(d.get("improved_summary", {}) or {}),
            per_class=[ClassMetricDelta.from_dict(c) for c in d.get("per_class", [])],
            macro_delta=dict(d.get("macro_delta", {}) or {}),
            micro_delta=dict(d.get("micro_delta", {}) or {}),
            weighted_delta=dict(d.get("weighted_delta", {}) or {}),
            thin_cloud=ThinCloudComparison.from_dict(d.get("thin_cloud", {}) or {}),
            worst_class_baseline=d.get("worst_class_baseline"),
            worst_class_improved=d.get("worst_class_improved"),
            status=d.get("status", NOT_YET_MEASURED))


# --------------------------------------------------------------------------------------------------
# Failure comparison (section 11): reuse M9 outputs; compare, do not re-implement.
# --------------------------------------------------------------------------------------------------
@dataclass
class FailureArmSummary:
    """Compact per-arm failure summary extracted from an M9 result."""

    total_failures: int = 0
    thin_cloud_failures: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    class_confusion: int = 0
    severity_distribution: dict[str, int] = field(default_factory=dict)
    top_categories: list[dict[str, Any]] = field(default_factory=list)
    status: str = NOT_YET_MEASURED

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_failures": self.total_failures, "thin_cloud_failures": self.thin_cloud_failures,
            "false_positives": self.false_positives, "false_negatives": self.false_negatives,
            "class_confusion": self.class_confusion,
            "severity_distribution": self.severity_distribution,
            "top_categories": self.top_categories, "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FailureArmSummary":
        return cls(
            total_failures=int(d.get("total_failures", 0)),
            thin_cloud_failures=int(d.get("thin_cloud_failures", 0)),
            false_positives=int(d.get("false_positives", 0)),
            false_negatives=int(d.get("false_negatives", 0)),
            class_confusion=int(d.get("class_confusion", 0)),
            severity_distribution=dict(d.get("severity_distribution", {}) or {}),
            top_categories=list(d.get("top_categories", []) or []),
            status=d.get("status", NOT_YET_MEASURED))


@dataclass
class FailureComparison:
    """Failure behaviour of both arms + the architectural-hypothesis verdict (thin-cloud focus)."""

    baseline: FailureArmSummary = field(default_factory=FailureArmSummary)
    improved: FailureArmSummary = field(default_factory=FailureArmSummary)
    hypothesis: str = "Attention gates improve difficult thin-cloud discrimination."
    hypothesis_supported: bool | None = None       # None = NOT YET MEASURED
    thin_cloud_failure_delta: int | None = None
    total_failure_delta: int | None = None
    status: str = NOT_YET_MEASURED

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline": self.baseline.to_dict(), "improved": self.improved.to_dict(),
            "hypothesis": self.hypothesis, "hypothesis_supported": self.hypothesis_supported,
            "thin_cloud_failure_delta": self.thin_cloud_failure_delta,
            "total_failure_delta": self.total_failure_delta, "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FailureComparison":
        return cls(
            baseline=FailureArmSummary.from_dict(d.get("baseline", {}) or {}),
            improved=FailureArmSummary.from_dict(d.get("improved", {}) or {}),
            hypothesis=d.get("hypothesis", ""), hypothesis_supported=d.get("hypothesis_supported"),
            thin_cloud_failure_delta=d.get("thin_cloud_failure_delta"),
            total_failure_delta=d.get("total_failure_delta"),
            status=d.get("status", NOT_YET_MEASURED))


# --------------------------------------------------------------------------------------------------
# Per-arm experiment record (section 5): one reproducible arm of one seed row.
# --------------------------------------------------------------------------------------------------
@dataclass
class ExperimentRecord:
    """A reproducible record of one arm: identifiers + artifact/eval/failure refs + compute + quality."""

    label: str
    seed: int
    architecture: str
    experiment_id: str
    model_id: str
    model_config_hash: str
    training_config_hash: str
    evaluation_config_hash: str = ""
    failure_config_hash: str = ""
    model_artifact: dict[str, Any] | None = None
    training_artifact: dict[str, Any] | None = None
    evaluation_summary: dict[str, Any] | None = None      # EvaluationSummary.to_dict() (may be SYNTHETIC)
    failure_summary: dict[str, Any] | None = None
    compute: ComputeMeasurement | None = None
    quality_status: str = NOT_YET_MEASURED
    source_references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label, "seed": self.seed, "architecture": self.architecture,
            "experiment_id": self.experiment_id, "model_id": self.model_id,
            "model_config_hash": self.model_config_hash,
            "training_config_hash": self.training_config_hash,
            "evaluation_config_hash": self.evaluation_config_hash,
            "failure_config_hash": self.failure_config_hash,
            "model_artifact": self.model_artifact, "training_artifact": self.training_artifact,
            "evaluation_summary": self.evaluation_summary, "failure_summary": self.failure_summary,
            "compute": self.compute.to_dict() if self.compute else None,
            "quality_status": self.quality_status, "source_references": list(self.source_references),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ExperimentRecord":
        comp = d.get("compute")
        return cls(
            label=d.get("label", ""), seed=int(d.get("seed", 0)),
            architecture=d.get("architecture", ""), experiment_id=d.get("experiment_id", ""),
            model_id=d.get("model_id", ""), model_config_hash=d.get("model_config_hash", ""),
            training_config_hash=d.get("training_config_hash", ""),
            evaluation_config_hash=d.get("evaluation_config_hash", ""),
            failure_config_hash=d.get("failure_config_hash", ""),
            model_artifact=d.get("model_artifact"), training_artifact=d.get("training_artifact"),
            evaluation_summary=d.get("evaluation_summary"), failure_summary=d.get("failure_summary"),
            compute=ComputeMeasurement.from_dict(comp) if comp else None,
            quality_status=d.get("quality_status", NOT_YET_MEASURED),
            source_references=list(d.get("source_references", []) or []))


# --------------------------------------------------------------------------------------------------
# Canonical artifact (section 14).
# --------------------------------------------------------------------------------------------------
@dataclass
class ModelComparisonArtifact:
    """Canonical metadata for one controlled comparison (deterministic content hash)."""

    comparison_id: str
    comparison_config_hash: str
    fairness_hash: str
    baseline: ExperimentRecord | None = None
    improved: ExperimentRecord | None = None
    fairness_report: dict[str, Any] = field(default_factory=dict)
    metric_comparison: dict[str, Any] = field(default_factory=dict)
    failure_comparison: dict[str, Any] = field(default_factory=dict)
    compute_comparison: dict[str, Any] = field(default_factory=dict)
    decision: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    seeds_intended: list[int] = field(default_factory=list)
    seeds_executed: list[int] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    data_regime: str = SYNTHETIC                    # SYNTHETIC | REAL
    comparison_version: str = COMPARISON_VERSION
    created_at: str = field(default_factory=_now)
    notes: str = ""

    # --- deterministic content hashing (ignores created_at/notes/timestamps) ----------------------
    def _identity(self) -> dict[str, Any]:
        def arm_identity(rec: ExperimentRecord | None) -> dict[str, Any]:
            if rec is None:
                return {}
            return {
                "architecture": rec.architecture, "model_config_hash": rec.model_config_hash,
                "training_config_hash": rec.training_config_hash,
                "evaluation_config_hash": rec.evaluation_config_hash,
                "failure_config_hash": rec.failure_config_hash, "seed": rec.seed,
                "model_content_hash": (rec.model_artifact or {}).get("content_hash", ""),
                "training_content_hash": (rec.training_artifact or {}).get("content_hash", ""),
            }
        return {
            "comparison_config_hash": self.comparison_config_hash, "fairness_hash": self.fairness_hash,
            "baseline": arm_identity(self.baseline), "improved": arm_identity(self.improved),
            "decision_outcome": (self.decision or {}).get("outcome", ""),
            "data_regime": self.data_regime, "comparison_version": self.comparison_version,
            "seeds_executed": sorted(self.seeds_executed),
        }

    def content_hash(self) -> str:
        """Deterministic hash of identity fields (stable across time; ignores created_at/notes)."""
        return stable_hash(self._identity())

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "comparison_config_hash": self.comparison_config_hash, "fairness_hash": self.fairness_hash,
            "baseline_model_artifact": (self.baseline.model_artifact if self.baseline else None),
            "improved_model_artifact": (self.improved.model_artifact if self.improved else None),
            "baseline_training_artifact": (self.baseline.training_artifact if self.baseline else None),
            "improved_training_artifact": (self.improved.training_artifact if self.improved else None),
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "improved": self.improved.to_dict() if self.improved else None,
            "fairness_report": self.fairness_report,
            "metric_comparison": self.metric_comparison,
            "failure_comparison": self.failure_comparison,
            "compute_comparison": self.compute_comparison,
            "decision": self.decision, "environment": self.environment,
            "seeds_intended": list(self.seeds_intended), "seeds_executed": list(self.seeds_executed),
            "limitations": list(self.limitations), "data_regime": self.data_regime,
            "comparison_version": self.comparison_version, "created_at": self.created_at,
            "notes": self.notes, "content_hash": self.content_hash(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ModelComparisonArtifact":
        base = d.get("baseline")
        impr = d.get("improved")
        return cls(
            comparison_id=str(d.get("comparison_id", "")),
            comparison_config_hash=str(d.get("comparison_config_hash", "")),
            fairness_hash=str(d.get("fairness_hash", "")),
            baseline=ExperimentRecord.from_dict(base) if base else None,
            improved=ExperimentRecord.from_dict(impr) if impr else None,
            fairness_report=dict(d.get("fairness_report", {}) or {}),
            metric_comparison=dict(d.get("metric_comparison", {}) or {}),
            failure_comparison=dict(d.get("failure_comparison", {}) or {}),
            compute_comparison=dict(d.get("compute_comparison", {}) or {}),
            decision=dict(d.get("decision", {}) or {}), environment=dict(d.get("environment", {}) or {}),
            seeds_intended=list(d.get("seeds_intended", []) or []),
            seeds_executed=list(d.get("seeds_executed", []) or []),
            limitations=list(d.get("limitations", []) or []),
            data_regime=str(d.get("data_regime", SYNTHETIC)),
            comparison_version=str(d.get("comparison_version", COMPARISON_VERSION)),
            created_at=str(d.get("created_at", "")), notes=str(d.get("notes", "")))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "ModelComparisonArtifact":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "ModelComparisonArtifact":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def create(cls, *, comparison_config_hash: str, fairness_hash: str,
               baseline: ExperimentRecord | None = None, improved: ExperimentRecord | None = None,
               data_regime: str = SYNTHETIC, created_at: str | None = None,
               **kwargs: Any) -> "ModelComparisonArtifact":
        """Assemble an artifact, deriving ``comparison_id`` from its deterministic content hash."""
        artifact = cls(
            comparison_id="", comparison_config_hash=comparison_config_hash,
            fairness_hash=fairness_hash, baseline=baseline, improved=improved,
            data_regime=data_regime, created_at=created_at or _now(), **kwargs)
        artifact.comparison_id = f"cmp-{artifact.content_hash()[:12]}"
        return artifact
