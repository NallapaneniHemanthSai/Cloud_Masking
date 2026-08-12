"""Typed failure-analysis records (Milestone 9).

Strongly-typed, deterministically-serialisable records. **No raw tensors** are stored — only counts,
rates, ids, class names, and path/id references. Confidence fields are ``None`` (probabilities are not
available in the current pipeline; ADR-0009). Standard-library only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import (
    EVALUATION_VERSION,
    FAILURE_ANALYSIS_VERSION,
)
from app.failure_analysis.taxonomy import Severity


def _sev_name(sev: Severity) -> str:
    return sev.name


def _sev_from(name: str) -> Severity:
    return Severity[name]


@dataclass
class ErrorRecord:
    """A pixel-level, per-class error entry (aggregate over the evaluated data)."""

    dataset: str
    split: str
    class_name: str            # the (true) class this error concerns
    predicted_class: str       # dominant confusion target, or "" (e.g., for FP entries)
    error_type: str            # FailureCategory value
    error_count: int
    error_rate: float | None
    support: int
    severity: str = Severity.NONE.name
    rank: int = 0
    confidence: float | None = None      # unavailable in this pipeline
    source_reference: str = ""
    evaluation_version: str = EVALUATION_VERSION
    analysis_version: str = FAILURE_ANALYSIS_VERSION
    config_hash: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset, "split": self.split, "class_name": self.class_name,
            "predicted_class": self.predicted_class, "error_type": self.error_type,
            "error_count": self.error_count, "error_rate": self.error_rate, "support": self.support,
            "severity": self.severity, "rank": self.rank, "confidence": self.confidence,
            "source_reference": self.source_reference, "evaluation_version": self.evaluation_version,
            "analysis_version": self.analysis_version, "config_hash": self.config_hash, "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ErrorRecord":
        return cls(
            dataset=d["dataset"], split=d["split"], class_name=d["class_name"],
            predicted_class=d.get("predicted_class", ""), error_type=d["error_type"],
            error_count=int(d["error_count"]), error_rate=d.get("error_rate"),
            support=int(d["support"]), severity=d.get("severity", Severity.NONE.name),
            rank=int(d.get("rank", 0)), confidence=d.get("confidence"),
            source_reference=d.get("source_reference", ""),
            evaluation_version=d.get("evaluation_version", EVALUATION_VERSION),
            analysis_version=d.get("analysis_version", FAILURE_ANALYSIS_VERSION),
            config_hash=d.get("config_hash", ""), notes=d.get("notes", ""),
        )


@dataclass
class SampleFailure:
    """A sample-level failure record (requires per-sample predictions)."""

    sample_id: str
    dataset: str
    split: str
    total_pixels: int
    error_count: int
    error_rate: float
    per_class_errors: dict[str, int] = field(default_factory=dict)
    dominant_true_class: str = ""
    dominant_predicted_class: str = ""
    categories: list[str] = field(default_factory=list)   # FailureCategory values
    severity: str = Severity.NONE.name
    rank: int = 0
    group: str = ""
    confidence: float | None = None
    source_reference: str = ""
    evaluation_version: str = EVALUATION_VERSION
    analysis_version: str = FAILURE_ANALYSIS_VERSION
    config_hash: str = ""
    notes: str = ""

    @property
    def severity_rank(self) -> int:
        return int(_sev_from(self.severity))

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id, "dataset": self.dataset, "split": self.split,
            "total_pixels": self.total_pixels, "error_count": self.error_count,
            "error_rate": self.error_rate, "per_class_errors": self.per_class_errors,
            "dominant_true_class": self.dominant_true_class,
            "dominant_predicted_class": self.dominant_predicted_class,
            "categories": list(self.categories), "severity": self.severity, "rank": self.rank,
            "group": self.group, "confidence": self.confidence,
            "source_reference": self.source_reference, "evaluation_version": self.evaluation_version,
            "analysis_version": self.analysis_version, "config_hash": self.config_hash, "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SampleFailure":
        return cls(
            sample_id=str(d["sample_id"]), dataset=d.get("dataset", ""), split=d.get("split", ""),
            total_pixels=int(d["total_pixels"]), error_count=int(d["error_count"]),
            error_rate=float(d["error_rate"]),
            per_class_errors={k: int(v) for k, v in (d.get("per_class_errors") or {}).items()},
            dominant_true_class=d.get("dominant_true_class", ""),
            dominant_predicted_class=d.get("dominant_predicted_class", ""),
            categories=list(d.get("categories", [])), severity=d.get("severity", Severity.NONE.name),
            rank=int(d.get("rank", 0)), group=d.get("group", ""), confidence=d.get("confidence"),
            source_reference=d.get("source_reference", ""),
            evaluation_version=d.get("evaluation_version", EVALUATION_VERSION),
            analysis_version=d.get("analysis_version", FAILURE_ANALYSIS_VERSION),
            config_hash=d.get("config_hash", ""), notes=d.get("notes", ""),
        )


@dataclass
class HardExample:
    """A ranked reference to a hard sample (deterministic)."""

    sample_id: str
    criterion: str            # "error_rate" | "error_count" | class name | error type
    value: float
    rank: int
    severity: str = Severity.NONE.name
    category: str = ""
    source_reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"sample_id": self.sample_id, "criterion": self.criterion, "value": self.value,
                "rank": self.rank, "severity": self.severity, "category": self.category,
                "source_reference": self.source_reference}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "HardExample":
        return cls(sample_id=str(d["sample_id"]), criterion=str(d["criterion"]),
                   value=float(d["value"]), rank=int(d["rank"]),
                   severity=d.get("severity", Severity.NONE.name), category=d.get("category", ""),
                   source_reference=d.get("source_reference", ""))


@dataclass
class FailureSummary:
    """Aggregate failure summary for one stratum (class / error type / group)."""

    key: str
    stratum_type: str          # "class" | "error_type" | "group" | "predicted_class"
    total_errors: int
    sample_count: int = 0
    error_rate: float | None = None
    severity_distribution: dict[str, int] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "stratum_type": self.stratum_type, "total_errors": self.total_errors,
                "sample_count": self.sample_count, "error_rate": self.error_rate,
                "severity_distribution": self.severity_distribution, "notes": self.notes}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FailureSummary":
        return cls(key=str(d["key"]), stratum_type=str(d["stratum_type"]),
                   total_errors=int(d["total_errors"]), sample_count=int(d.get("sample_count", 0)),
                   error_rate=d.get("error_rate"),
                   severity_distribution={k: int(v) for k, v in (d.get("severity_distribution") or {}).items()},
                   notes=d.get("notes", ""))


@dataclass
class FailureGroup:
    """A group of failing sample ids sharing a stratum key."""

    key: str
    stratum_type: str
    sample_ids: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.sample_ids)

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "stratum_type": self.stratum_type,
                "sample_ids": list(self.sample_ids), "count": self.count}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FailureGroup":
        return cls(key=str(d["key"]), stratum_type=str(d["stratum_type"]),
                   sample_ids=list(d.get("sample_ids", [])))


@dataclass
class FailureAnalysisResult:
    """Canonical top-level failure-analysis record."""

    config: dict[str, Any]
    dataset: str
    split: str
    model_id: str
    taxonomy: list[dict[str, str]]
    pixel_errors: list[ErrorRecord] = field(default_factory=list)
    sample_failures: list[SampleFailure] = field(default_factory=list)
    hard_examples: dict[str, list[HardExample]] = field(default_factory=dict)
    class_summaries: list[FailureSummary] = field(default_factory=list)
    error_type_summaries: list[FailureSummary] = field(default_factory=list)
    group_summaries: list[FailureSummary] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    analysis_version: str = FAILURE_ANALYSIS_VERSION
    evaluation_version: str = EVALUATION_VERSION
    config_hash: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config, "dataset": self.dataset, "split": self.split,
            "model_id": self.model_id, "taxonomy": self.taxonomy,
            "pixel_errors": [e.to_dict() for e in self.pixel_errors],
            "sample_failures": [s.to_dict() for s in self.sample_failures],
            "hard_examples": {k: [h.to_dict() for h in v] for k, v in self.hard_examples.items()},
            "class_summaries": [s.to_dict() for s in self.class_summaries],
            "error_type_summaries": [s.to_dict() for s in self.error_type_summaries],
            "group_summaries": [s.to_dict() for s in self.group_summaries],
            "limitations": list(self.limitations),
            "analysis_version": self.analysis_version, "evaluation_version": self.evaluation_version,
            "config_hash": self.config_hash, "timestamp": self.timestamp, "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FailureAnalysisResult":
        return cls(
            config=dict(d.get("config", {}) or {}), dataset=d.get("dataset", ""),
            split=d.get("split", ""), model_id=d.get("model_id", ""),
            taxonomy=list(d.get("taxonomy", [])),
            pixel_errors=[ErrorRecord.from_dict(e) for e in d.get("pixel_errors", [])],
            sample_failures=[SampleFailure.from_dict(s) for s in d.get("sample_failures", [])],
            hard_examples={k: [HardExample.from_dict(h) for h in v]
                           for k, v in (d.get("hard_examples") or {}).items()},
            class_summaries=[FailureSummary.from_dict(s) for s in d.get("class_summaries", [])],
            error_type_summaries=[FailureSummary.from_dict(s) for s in d.get("error_type_summaries", [])],
            group_summaries=[FailureSummary.from_dict(s) for s in d.get("group_summaries", [])],
            limitations=list(d.get("limitations", [])),
            analysis_version=d.get("analysis_version", FAILURE_ANALYSIS_VERSION),
            evaluation_version=d.get("evaluation_version", EVALUATION_VERSION),
            config_hash=d.get("config_hash", ""), timestamp=d.get("timestamp", ""), notes=d.get("notes", ""),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "FailureAnalysisResult":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "FailureAnalysisResult":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
