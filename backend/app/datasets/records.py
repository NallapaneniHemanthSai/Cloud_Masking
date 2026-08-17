"""Typed experimental-dataset records (Milestone 12).

Strongly-typed, deterministically-serialisable records for the experimental-dataset pipeline: the dataset
manifest record (observed vs provenance), the structured validation report, the deterministic subset
selection, the group-aware split manifest, and the class-distribution report. **No raw pixels are stored**
— only counts, ids, paths, and hashes. Unknown values stay explicit (``UNKNOWN`` / ``NOT_VERIFIED`` /
``NOT_AVAILABLE``); nothing is invented. Standard-library only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.constants import DATASET_MANIFEST_VERSION, PREPROCESSING_VERSION
from app.utils.hashing import stable_hash

# --- honest placeholders (never invent values) ----------------------------------------------------
UNKNOWN = "UNKNOWN"
NOT_VERIFIED = "NOT_VERIFIED"
NOT_AVAILABLE = "NOT_AVAILABLE"

# --- overall validation statuses (section 6) ------------------------------------------------------
READY = "READY"
READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
INCOMPLETE = "INCOMPLETE"
INVALID = "INVALID"
NOT_PRESENT = "NOT_PRESENT"

# --- per-check statuses ---------------------------------------------------------------------------
CHECK_PASS = "PASS"
CHECK_FAIL = "FAIL"
CHECK_WARN = "WARN"
CHECK_NA = "N/A"
CHECK_NOT_VERIFIED = "NOT_VERIFIED"

# --- data regime ----------------------------------------------------------------------------------
REGIME_REAL = "REAL"
REGIME_SYNTHETIC = "SYNTHETIC"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------------------------------
# Section 4 — experimental dataset manifest record (observed values alongside provenance).
# --------------------------------------------------------------------------------------------------
@dataclass
class ExperimentalDatasetRecord:
    """A dataset record for an experiment: provenance (from datasets.yaml) + observed values."""

    dataset_id: str
    dataset_name: str = UNKNOWN
    version: str = UNKNOWN
    source: str = UNKNOWN
    source_url: str = UNKNOWN
    license: str = UNKNOWN
    access_status: str = UNKNOWN
    download_date: str = NOT_AVAILABLE
    local_path: str = ""
    expected_files: list[str] = field(default_factory=list)
    observed_files: list[str] = field(default_factory=list)
    checksum: str = NOT_VERIFIED
    checksum_algorithm: str = "sha256"
    patch_count: int | None = None
    band_count: int | None = None
    class_count: int | None = None
    class_mapping: dict[str, str] = field(default_factory=dict)
    patch_dimensions: str = UNKNOWN
    spatial_resolution: str = UNKNOWN
    preprocessing_version: str = PREPROCESSING_VERSION
    manifest_version: str = DATASET_MANIFEST_VERSION
    data_regime: str = REGIME_REAL
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id, "dataset_name": self.dataset_name, "version": self.version,
            "source": self.source, "source_url": self.source_url, "license": self.license,
            "access_status": self.access_status, "download_date": self.download_date,
            "local_path": self.local_path, "expected_files": list(self.expected_files),
            "observed_files": list(self.observed_files), "checksum": self.checksum,
            "checksum_algorithm": self.checksum_algorithm, "patch_count": self.patch_count,
            "band_count": self.band_count, "class_count": self.class_count,
            "class_mapping": self.class_mapping, "patch_dimensions": self.patch_dimensions,
            "spatial_resolution": self.spatial_resolution,
            "preprocessing_version": self.preprocessing_version,
            "manifest_version": self.manifest_version, "data_regime": self.data_regime,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ExperimentalDatasetRecord":
        return cls(
            dataset_id=d["dataset_id"], dataset_name=d.get("dataset_name", UNKNOWN),
            version=d.get("version", UNKNOWN), source=d.get("source", UNKNOWN),
            source_url=d.get("source_url", UNKNOWN), license=d.get("license", UNKNOWN),
            access_status=d.get("access_status", UNKNOWN), download_date=d.get("download_date", NOT_AVAILABLE),
            local_path=d.get("local_path", ""), expected_files=list(d.get("expected_files", []) or []),
            observed_files=list(d.get("observed_files", []) or []), checksum=d.get("checksum", NOT_VERIFIED),
            checksum_algorithm=d.get("checksum_algorithm", "sha256"), patch_count=d.get("patch_count"),
            band_count=d.get("band_count"), class_count=d.get("class_count"),
            class_mapping=dict(d.get("class_mapping", {}) or {}),
            patch_dimensions=d.get("patch_dimensions", UNKNOWN),
            spatial_resolution=d.get("spatial_resolution", UNKNOWN),
            preprocessing_version=d.get("preprocessing_version", PREPROCESSING_VERSION),
            manifest_version=d.get("manifest_version", DATASET_MANIFEST_VERSION),
            data_regime=d.get("data_regime", REGIME_REAL), notes=d.get("notes", ""))


# --------------------------------------------------------------------------------------------------
# Section 6 — structured validation report.
# --------------------------------------------------------------------------------------------------
@dataclass
class DatasetValidationReport:
    """Structured integrity/consistency validation result for an experimental dataset."""

    dataset_id: str
    validation_timestamp: str = field(default_factory=_now)
    manifest_status: str = CHECK_NA
    file_status: str = CHECK_NA
    checksum_status: str = CHECK_NA
    metadata_status: str = CHECK_NA
    label_status: str = CHECK_NA
    dimension_status: str = CHECK_NA
    completeness_status: str = CHECK_NA
    overall_status: str = NOT_PRESENT
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data_regime: str = REGIME_REAL

    @property
    def is_ready(self) -> bool:
        return self.overall_status in (READY, READY_WITH_WARNINGS)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id, "validation_timestamp": self.validation_timestamp,
            "manifest_status": self.manifest_status, "file_status": self.file_status,
            "checksum_status": self.checksum_status, "metadata_status": self.metadata_status,
            "label_status": self.label_status, "dimension_status": self.dimension_status,
            "completeness_status": self.completeness_status, "overall_status": self.overall_status,
            "failures": list(self.failures), "warnings": list(self.warnings),
            "data_regime": self.data_regime,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DatasetValidationReport":
        return cls(
            dataset_id=d["dataset_id"], validation_timestamp=d.get("validation_timestamp", ""),
            manifest_status=d.get("manifest_status", CHECK_NA), file_status=d.get("file_status", CHECK_NA),
            checksum_status=d.get("checksum_status", CHECK_NA),
            metadata_status=d.get("metadata_status", CHECK_NA),
            label_status=d.get("label_status", CHECK_NA), dimension_status=d.get("dimension_status", CHECK_NA),
            completeness_status=d.get("completeness_status", CHECK_NA),
            overall_status=d.get("overall_status", NOT_PRESENT),
            failures=list(d.get("failures", []) or []), warnings=list(d.get("warnings", []) or []),
            data_regime=d.get("data_regime", REGIME_REAL))


# --------------------------------------------------------------------------------------------------
# Section 7 — deterministic curated subset selection.
# --------------------------------------------------------------------------------------------------
@dataclass
class SubsetSelection:
    """A reproducible curated-subset selection over a candidate pool."""

    strategy: str
    seed: int
    requested_size: int
    selected_ids: list[str] = field(default_factory=list)
    group_ids: dict[str, str] = field(default_factory=dict)          # sample_id -> group/scene id
    class_presence: dict[str, bool] = field(default_factory=dict)    # class_name -> present in subset
    pool_size: int = 0
    data_regime: str = REGIME_REAL
    notes: str = ""

    @property
    def size(self) -> int:
        return len(self.selected_ids)

    def selection_hash(self) -> str:
        """Deterministic hash of the selection (order-independent, ignores notes)."""
        return stable_hash({
            "strategy": self.strategy, "seed": self.seed, "requested_size": self.requested_size,
            "selected_ids": sorted(self.selected_ids),
            "group_ids": {k: self.group_ids[k] for k in sorted(self.group_ids)},
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy, "seed": self.seed, "requested_size": self.requested_size,
            "selected_ids": list(self.selected_ids), "group_ids": self.group_ids,
            "class_presence": self.class_presence, "pool_size": self.pool_size, "size": self.size,
            "data_regime": self.data_regime, "selection_hash": self.selection_hash(), "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SubsetSelection":
        return cls(
            strategy=d["strategy"], seed=int(d["seed"]), requested_size=int(d["requested_size"]),
            selected_ids=list(d.get("selected_ids", []) or []), group_ids=dict(d.get("group_ids", {}) or {}),
            class_presence=dict(d.get("class_presence", {}) or {}), pool_size=int(d.get("pool_size", 0)),
            data_regime=d.get("data_regime", REGIME_REAL), notes=d.get("notes", ""))


# --------------------------------------------------------------------------------------------------
# Section 8 — group-aware split manifest (persisted JSON).
# --------------------------------------------------------------------------------------------------
@dataclass
class SplitEntry:
    """One sample's split assignment with its group id (scene)."""

    sample_id: str
    group_id: str
    split: str

    def to_dict(self) -> dict[str, Any]:
        return {"sample_id": self.sample_id, "group_id": self.group_id, "split": self.split}


@dataclass
class ExperimentalSplitManifest:
    """Persistent, leakage-checked train/val/test split manifest (section 8)."""

    entries: list[SplitEntry] = field(default_factory=list)
    seed: int = 0
    dataset_version: str = ""
    preprocessing_version: str = PREPROCESSING_VERSION
    ratios: tuple[float, float, float] = (0.7, 0.15, 0.15)
    grouped: bool = True
    created_utc: str = field(default_factory=_now)

    def ids_for(self, split: str) -> list[str]:
        return [e.sample_id for e in self.entries if e.split == split]

    def groups_for(self, split: str) -> set[str]:
        return {e.group_id for e in self.entries if e.split == split}

    def counts(self) -> dict[str, int]:
        return {s: len(self.ids_for(s)) for s in ("train", "val", "test")}

    def leakage_ok(self) -> bool:
        """No sample AND no group is shared across splits."""
        for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
            if set(self.ids_for(a)) & set(self.ids_for(b)):
                return False
            if self.grouped and (self.groups_for(a) & self.groups_for(b)):
                return False
        return True

    def split_config_hash(self) -> str:
        """Deterministic hash of the split assignment + configuration (ignores timestamp)."""
        return stable_hash({
            "seed": self.seed, "dataset_version": self.dataset_version,
            "preprocessing_version": self.preprocessing_version, "ratios": list(self.ratios),
            "grouped": self.grouped,
            "assignment": sorted((e.sample_id, e.group_id, e.split) for e in self.entries),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed, "dataset_version": self.dataset_version,
            "preprocessing_version": self.preprocessing_version, "ratios": list(self.ratios),
            "grouped": self.grouped, "created_utc": self.created_utc, "counts": self.counts(),
            "leakage_ok": self.leakage_ok(), "split_config_hash": self.split_config_hash(),
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ExperimentalSplitManifest":
        ratios = d.get("ratios") or [0.7, 0.15, 0.15]
        return cls(
            entries=[SplitEntry(e["sample_id"], e["group_id"], e["split"]) for e in d.get("entries", [])],
            seed=int(d.get("seed", 0)), dataset_version=d.get("dataset_version", ""),
            preprocessing_version=d.get("preprocessing_version", PREPROCESSING_VERSION),
            ratios=tuple(ratios), grouped=bool(d.get("grouped", True)),
            created_utc=d.get("created_utc", ""))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def save_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "ExperimentalSplitManifest":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


# --------------------------------------------------------------------------------------------------
# Section 11 — class distribution report (thin cloud surfaced).
# --------------------------------------------------------------------------------------------------
@dataclass
class ClassDistributionReport:
    """Real per-class distribution (pixel + sample counts) overall and per split."""

    class_names: list[str]
    pixel_counts: dict[str, int] = field(default_factory=dict)
    sample_counts: dict[str, int] = field(default_factory=dict)     # samples containing the class
    per_split_pixels: dict[str, dict[str, int]] = field(default_factory=dict)  # split -> class -> pixels
    total_pixels: int = 0
    interventions: list[str] = field(default_factory=list)          # any data-level rebalancing (recorded)
    data_regime: str = REGIME_REAL

    def percentages(self) -> dict[str, float]:
        if self.total_pixels == 0:
            return {c: 0.0 for c in self.class_names}
        return {c: round(self.pixel_counts.get(c, 0) / self.total_pixels, 6) for c in self.class_names}

    def thin_cloud_fraction(self) -> float | None:
        return self.percentages().get("thin_cloud")

    def balance_ratio(self) -> float:
        vals = [self.pixel_counts.get(c, 0) for c in self.class_names]
        if not vals or max(vals) == 0:
            return 0.0
        return round(min(vals) / max(vals), 6)

    def imbalance_severe(self, threshold: float = 0.05) -> bool:
        return self.balance_ratio() < threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_names": list(self.class_names), "pixel_counts": self.pixel_counts,
            "sample_counts": self.sample_counts, "per_split_pixels": self.per_split_pixels,
            "total_pixels": self.total_pixels, "percentages": self.percentages(),
            "thin_cloud_fraction": self.thin_cloud_fraction(), "balance_ratio": self.balance_ratio(),
            "imbalance_severe": self.imbalance_severe(), "interventions": list(self.interventions),
            "data_regime": self.data_regime,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ClassDistributionReport":
        return cls(
            class_names=list(d.get("class_names", [])),
            pixel_counts=dict(d.get("pixel_counts", {}) or {}),
            sample_counts=dict(d.get("sample_counts", {}) or {}),
            per_split_pixels={k: dict(v) for k, v in (d.get("per_split_pixels", {}) or {}).items()},
            total_pixels=int(d.get("total_pixels", 0)),
            interventions=list(d.get("interventions", []) or []),
            data_regime=d.get("data_regime", REGIME_REAL))
