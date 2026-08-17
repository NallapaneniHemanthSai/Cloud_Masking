"""Experiment-readiness gate + M11 handoff (Milestone 12).

:func:`is_experiment_ready` evaluates every critical gate for a prepared dataset and refuses to declare a
dataset ready unless all pass (section 15) — so M11 real training can never run against an invalid dataset.
:func:`build_handoff` produces a small, isolated :class:`ExperimentHandoff` that M11 consumes **without any
change to M11 logic** (section 16/17): it carries the dataset artifact, split manifest, normalization
statistics, versions, expected channels/classes, and a ready-to-run M11 ``ComparisonConfig``. The handoff
carries ``data_regime`` so a SYNTHETIC dataset keeps M11's decision INCONCLUSIVE. Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.datasets.artifact import DatasetArtifact
from app.datasets.experimental_config import THIN_CLOUD_NAME, ExperimentalDatasetConfig
from app.datasets.records import (
    CHECK_FAIL,
    CHECK_PASS,
    INVALID,
    READY,
    READY_WITH_WARNINGS,
    REGIME_REAL,
    REGIME_SYNTHETIC,
    ExperimentalSplitManifest,
)

# Gates that, if failed, force READY=false (section 15).
CRITICAL_GATES: tuple[str, ...] = (
    "validation_ok", "required_files_exist", "checksums_not_failed", "labels_valid", "dimensions_valid",
    "splits_disjoint", "required_classes_exist", "thin_cloud_exists", "normalization_stats_exist",
    "patch_manifest_exists", "preprocessing_version_recorded", "dataset_version_recorded",
    "licensing_acceptable",
)


@dataclass
class ExperimentReadiness:
    """Result of the experiment-readiness gate."""

    dataset_artifact_id: str
    ready: bool
    gates: dict[str, bool] = field(default_factory=dict)
    critical_failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data_regime: str = REGIME_REAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_artifact_id": self.dataset_artifact_id, "ready": self.ready, "gates": self.gates,
            "critical_failures": list(self.critical_failures), "warnings": list(self.warnings),
            "data_regime": self.data_regime,
        }


@dataclass
class ExperimentHandoff:
    """A clean handoff bundle M11 can consume to run the real comparison (section 16)."""

    dataset_artifact_id: str
    dataset_version: str
    preprocessing_version: str
    dataset_artifact_path: str
    split_manifest_path: str
    normalization_statistics_path: str
    expected_input_channels: int
    expected_classes: int
    comparison_config: dict[str, Any] = field(default_factory=dict)
    data_regime: str = REGIME_REAL
    ready: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_artifact_id": self.dataset_artifact_id, "dataset_version": self.dataset_version,
            "preprocessing_version": self.preprocessing_version,
            "dataset_artifact_path": self.dataset_artifact_path,
            "split_manifest_path": self.split_manifest_path,
            "normalization_statistics_path": self.normalization_statistics_path,
            "expected_input_channels": self.expected_input_channels,
            "expected_classes": self.expected_classes, "comparison_config": self.comparison_config,
            "data_regime": self.data_regime, "ready": self.ready, "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ExperimentHandoff":
        return cls(
            dataset_artifact_id=d.get("dataset_artifact_id", ""),
            dataset_version=d.get("dataset_version", ""),
            preprocessing_version=d.get("preprocessing_version", ""),
            dataset_artifact_path=d.get("dataset_artifact_path", ""),
            split_manifest_path=d.get("split_manifest_path", ""),
            normalization_statistics_path=d.get("normalization_statistics_path", ""),
            expected_input_channels=int(d.get("expected_input_channels", 0)),
            expected_classes=int(d.get("expected_classes", 0)),
            comparison_config=dict(d.get("comparison_config", {}) or {}),
            data_regime=d.get("data_regime", REGIME_REAL), ready=bool(d.get("ready", False)),
            notes=d.get("notes", ""))


def is_experiment_ready(
    artifact: DatasetArtifact,
    *,
    split_manifest: ExperimentalSplitManifest,
    config: ExperimentalDatasetConfig,
    dataset_record: Any | None = None,
) -> ExperimentReadiness:
    """Evaluate every readiness gate for a prepared dataset (section 15)."""
    validation = artifact.validation_report or {}
    distribution = artifact.class_distribution or {}
    pixel_counts: dict[str, int] = distribution.get("pixel_counts", {})
    percentages: dict[str, float] = distribution.get("percentages", {})

    gates: dict[str, bool] = {
        "validation_ok": validation.get("overall_status") in (READY, READY_WITH_WARNINGS),
        "required_files_exist": validation.get("file_status") == CHECK_PASS,
        "checksums_not_failed": validation.get("checksum_status") != CHECK_FAIL,
        "labels_valid": validation.get("label_status") in (CHECK_PASS,),
        "dimensions_valid": validation.get("dimension_status") != CHECK_FAIL,
        "splits_disjoint": split_manifest.leakage_ok(),
        "required_classes_exist": all(pixel_counts.get(c, 0) > 0 for c in config.required_classes),
        "thin_cloud_exists": (percentages.get(THIN_CLOUD_NAME, 0) or 0) > 0
                             or pixel_counts.get(THIN_CLOUD_NAME, 0) > 0,
        "normalization_stats_exist": bool(artifact.normalization_statistics_hash),
        "patch_manifest_exists": artifact.patch_count > 0,
        "preprocessing_version_recorded": bool(artifact.preprocessing_version),
        "dataset_version_recorded": bool(artifact.dataset_version),
        "licensing_acceptable": _licensing_ok(dataset_record),
        "provenance_complete": _provenance_ok(dataset_record),
    }

    critical_failures = [g for g in CRITICAL_GATES if not gates.get(g, False)]
    warnings: list[str] = []
    if validation.get("checksum_status") != CHECK_PASS:
        warnings.append("Checksums NOT VERIFIED.")
    if not gates["provenance_complete"]:
        warnings.append("Provenance incomplete (source/license UNKNOWN).")
    if validation.get("overall_status") == INVALID:
        warnings.append("Validation reported INVALID.")

    ready = not critical_failures
    return ExperimentReadiness(
        dataset_artifact_id=artifact.artifact_id, ready=ready, gates=gates,
        critical_failures=critical_failures, warnings=warnings, data_regime=artifact.data_regime)


def _licensing_ok(record: Any | None) -> bool:
    """Acceptable when redistribution is not prohibited (or the record is a synthetic fixture)."""
    if record is None:
        return True
    license_text = str(getattr(record, "license", "")).lower()
    return "prohibit" not in license_text and "prohibited" not in license_text


def _provenance_ok(record: Any | None) -> bool:
    if record is None:
        return False
    return (str(getattr(record, "source", "UNKNOWN")) != "UNKNOWN"
            and str(getattr(record, "license", "UNKNOWN")) != "UNKNOWN")


def build_handoff(
    artifact: DatasetArtifact,
    readiness: ExperimentReadiness,
    config: ExperimentalDatasetConfig,
    *,
    dataset_artifact_path: str,
    split_manifest_path: str,
    normalization_statistics_path: str,
) -> ExperimentHandoff:
    """Build a small, isolated M11 handoff bundle (no change to M11 logic — section 17)."""
    comparison_config: dict[str, Any] = {}
    try:  # lazy import keeps M12 decoupled and import-light
        from app.comparison import ComparisonConfig
        cfg = ComparisonConfig.cloudsen12(
            in_channels=config.band_count, num_classes=config.class_count,
            patch_size=config.patch_size, split=config.params.get("split", "test"))
        data = cfg.to_dict()
        data["dataset"] = config.dataset_id
        data["dataset_version"] = artifact.dataset_version
        data["preprocessing_version"] = config.preprocessing_version
        comparison_config = data
    except Exception:  # noqa: BLE001 - handoff still valid without the optional M11 config
        comparison_config = {}

    return ExperimentHandoff(
        dataset_artifact_id=artifact.artifact_id, dataset_version=artifact.dataset_version,
        preprocessing_version=config.preprocessing_version, dataset_artifact_path=dataset_artifact_path,
        split_manifest_path=split_manifest_path,
        normalization_statistics_path=normalization_statistics_path,
        expected_input_channels=config.band_count, expected_classes=config.class_count,
        comparison_config=comparison_config, data_regime=artifact.data_regime, ready=readiness.ready,
        notes=("SYNTHETIC dataset — M11 will keep the decision INCONCLUSIVE."
               if artifact.data_regime == REGIME_SYNTHETIC else ""))
