"""Canonical dataset artifact (Milestone 12).

:class:`DatasetArtifact` is the canonical, strongly-typed metadata object describing **one prepared
experimental dataset** — it holds **no pixels**, only metadata + deterministic hashes (subset / split /
normalization / config) and references to the validation + class-distribution reports. Deterministic
content hashing (ignoring timestamps/notes) + JSON save/load. Standard-library only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import DATASET_MANIFEST_VERSION, PREPROCESSING_VERSION
from app.datasets.records import REGIME_REAL
from app.utils.hashing import stable_hash


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DatasetArtifact:
    """Canonical metadata for one prepared experimental dataset (deterministic content hash)."""

    artifact_id: str
    dataset_id: str
    dataset_version: str = ""
    manifest_version: str = DATASET_MANIFEST_VERSION
    preprocessing_version: str = PREPROCESSING_VERSION
    config_hash: str = ""
    subset_selection_hash: str = ""
    split_manifest_hash: str = ""
    normalization_statistics_hash: str = ""
    validation_report: dict[str, Any] = field(default_factory=dict)
    class_distribution: dict[str, Any] = field(default_factory=dict)
    dataset_record: dict[str, Any] = field(default_factory=dict)
    sample_count: int = 0
    patch_count: int = 0
    train_count: int = 0
    validation_count: int = 0
    test_count: int = 0
    data_regime: str = REGIME_REAL
    created_at: str = field(default_factory=_now)
    notes: str = ""

    # --- deterministic content hashing (ignores created_at/notes/timestamps) -----------------------
    def _identity(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id, "dataset_version": self.dataset_version,
            "manifest_version": self.manifest_version, "preprocessing_version": self.preprocessing_version,
            "config_hash": self.config_hash, "subset_selection_hash": self.subset_selection_hash,
            "split_manifest_hash": self.split_manifest_hash,
            "normalization_statistics_hash": self.normalization_statistics_hash,
            "validation_overall": (self.validation_report or {}).get("overall_status", ""),
            "class_pixel_counts": (self.class_distribution or {}).get("pixel_counts", {}),
            "counts": {"sample": self.sample_count, "patch": self.patch_count, "train": self.train_count,
                       "val": self.validation_count, "test": self.test_count},
            "data_regime": self.data_regime,
        }

    def content_hash(self) -> str:
        """Deterministic hash of the identity fields (stable across time; ignores created_at/notes)."""
        return stable_hash(self._identity())

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id, "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version, "manifest_version": self.manifest_version,
            "preprocessing_version": self.preprocessing_version, "config_hash": self.config_hash,
            "subset_selection_hash": self.subset_selection_hash,
            "split_manifest_hash": self.split_manifest_hash,
            "normalization_statistics_hash": self.normalization_statistics_hash,
            "validation_report": self.validation_report, "class_distribution": self.class_distribution,
            "dataset_record": self.dataset_record, "sample_count": self.sample_count,
            "patch_count": self.patch_count, "train_count": self.train_count,
            "validation_count": self.validation_count, "test_count": self.test_count,
            "data_regime": self.data_regime, "created_at": self.created_at, "notes": self.notes,
            "content_hash": self.content_hash(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DatasetArtifact":
        return cls(
            artifact_id=str(d.get("artifact_id", "")), dataset_id=str(d.get("dataset_id", "")),
            dataset_version=str(d.get("dataset_version", "")),
            manifest_version=str(d.get("manifest_version", DATASET_MANIFEST_VERSION)),
            preprocessing_version=str(d.get("preprocessing_version", PREPROCESSING_VERSION)),
            config_hash=str(d.get("config_hash", "")),
            subset_selection_hash=str(d.get("subset_selection_hash", "")),
            split_manifest_hash=str(d.get("split_manifest_hash", "")),
            normalization_statistics_hash=str(d.get("normalization_statistics_hash", "")),
            validation_report=dict(d.get("validation_report", {}) or {}),
            class_distribution=dict(d.get("class_distribution", {}) or {}),
            dataset_record=dict(d.get("dataset_record", {}) or {}),
            sample_count=int(d.get("sample_count", 0)), patch_count=int(d.get("patch_count", 0)),
            train_count=int(d.get("train_count", 0)), validation_count=int(d.get("validation_count", 0)),
            test_count=int(d.get("test_count", 0)), data_regime=str(d.get("data_regime", REGIME_REAL)),
            created_at=str(d.get("created_at", "")), notes=str(d.get("notes", "")))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "DatasetArtifact":
        return cls.from_dict(json.loads(text))

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "DatasetArtifact":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def create(cls, *, dataset_id: str, created_at: str | None = None, **kwargs: Any) -> "DatasetArtifact":
        """Assemble an artifact, deriving ``artifact_id`` from its deterministic content hash."""
        artifact = cls(artifact_id="", dataset_id=dataset_id, created_at=created_at or _now(), **kwargs)
        artifact.artifact_id = f"ds-{dataset_id}-{artifact.content_hash()[:12]}"
        return artifact
