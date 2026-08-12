"""Failure-analysis configuration (Milestone 9).

Strongly-typed, validated, serialisable config with a deterministic hash. Configuration-driven top-K and
severity thresholds. Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import (
    EVALUATION_VERSION,
    FAILURE_ANALYSIS_VERSION,
)
from app.core.exceptions import ConfigurationError
from app.failure_analysis.taxonomy import Severity
from app.utils.hashing import stable_hash


@dataclass(frozen=True)
class SeverityThresholds:
    """Error-rate thresholds for evidence-based severity (ADR-0009)."""

    critical: float = 0.75
    high: float = 0.50
    medium: float = 0.25

    def validate(self) -> None:
        if not (0 < self.medium <= self.high <= self.critical <= 1.0):
            raise ConfigurationError(
                "severity thresholds must satisfy 0 < medium <= high <= critical <= 1.")

    def severity_for(self, error_rate: float | None) -> Severity:
        if error_rate is None or error_rate <= 0:
            return Severity.NONE
        if error_rate >= self.critical:
            return Severity.CRITICAL
        if error_rate >= self.high:
            return Severity.HIGH
        if error_rate >= self.medium:
            return Severity.MEDIUM
        return Severity.LOW

    def to_dict(self) -> dict[str, Any]:
        return {"critical": self.critical, "high": self.high, "medium": self.medium}


@dataclass(frozen=True)
class FailureAnalysisConfig:
    """Configuration for a failure-analysis run."""

    dataset: str = ""
    split: str = ""
    mode: str = "multiclass"                 # mirrors the evaluation mode
    class_names: tuple[str, ...] = ()
    model_id: str = ""
    top_k: int = 10
    ignore_index: int | None = None
    severity_thresholds: SeverityThresholds = field(default_factory=SeverityThresholds)
    evaluation_version: str = EVALUATION_VERSION
    analysis_version: str = FAILURE_ANALYSIS_VERSION
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.top_k <= 0:
            raise ConfigurationError(f"top_k must be > 0, got {self.top_k}.")
        if self.mode not in {"multiclass", "binary"}:
            raise ConfigurationError(f"mode must be 'multiclass' or 'binary', got {self.mode!r}.")
        self.severity_thresholds.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "split": self.split,
            "mode": self.mode,
            "class_names": list(self.class_names),
            "model_id": self.model_id,
            "top_k": self.top_k,
            "ignore_index": self.ignore_index,
            "severity_thresholds": self.severity_thresholds.to_dict(),
            "evaluation_version": self.evaluation_version,
            "analysis_version": self.analysis_version,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FailureAnalysisConfig":
        data = dict(data or {})
        st = data.get("severity_thresholds") or {}
        names = data.get("class_names")
        return cls(
            dataset=data.get("dataset", ""), split=data.get("split", ""),
            mode=data.get("mode", "multiclass"),
            class_names=tuple(names) if names else (),
            model_id=data.get("model_id", ""), top_k=int(data.get("top_k", 10)),
            ignore_index=data.get("ignore_index"),
            severity_thresholds=SeverityThresholds(
                critical=float(st.get("critical", 0.75)), high=float(st.get("high", 0.50)),
                medium=float(st.get("medium", 0.25))),
            evaluation_version=data.get("evaluation_version", EVALUATION_VERSION),
            analysis_version=data.get("analysis_version", FAILURE_ANALYSIS_VERSION),
            params=dict(data.get("params", {}) or {}),
        )

    def config_hash(self) -> str:
        return stable_hash(self.to_dict())
