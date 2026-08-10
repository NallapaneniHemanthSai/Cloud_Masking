"""Typed preprocessing records (Milestone 4, revised).

Strongly-typed dataclasses exchanged between preprocessing modules, replacing loose dicts/tuples. Each
holds **only preprocessing-related metadata** — no model/training information. Standard-library only.

Records:

* :class:`SampleRecord` — a discovered sample (paths + optional group).
* :class:`SplitRecord` — one sample's train/val/test assignment.
* :class:`PatchRecord` — a single generated patch's metadata (for the patch manifest).
* :class:`ValidationRecord` — a single validation issue.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

# Severities for validation records.
SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"


@dataclass
class SampleRecord:
    """A discovered sample (file paths only; no pixel data loaded)."""

    sample_id: str
    dataset: str
    image_paths: list[Path]
    label_path: Path | None = None
    group: str | None = None   # optional grouping key for leakage-resistant splitting

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "dataset": self.dataset,
            "image_paths": [str(p) for p in self.image_paths],
            "label_path": str(self.label_path) if self.label_path else None,
            "group": self.group,
        }


@dataclass(frozen=True)
class SplitRecord:
    """One sample's split assignment."""

    sample_id: str
    split: str                 # "train" | "val" | "test"
    group: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"sample_id": self.sample_id, "split": self.split, "group": self.group}


@dataclass(frozen=True)
class PatchRecord:
    """Metadata for a single generated patch (no pixel data, no model info)."""

    sample_id: str
    dataset: str
    split: str
    patch_index: int
    row_off: int
    col_off: int
    height: int
    width: int
    overlap: int
    patch_size: int
    source_image: str
    label_path: str | None
    created_utc: str
    preprocessing_version: str

    #: Canonical column order for tabular export (CSV). ClassVar -> not a dataclass field.
    COLUMNS: ClassVar[tuple[str, ...]] = (
        "sample_id", "dataset", "split", "patch_index",
        "row_off", "col_off", "height", "width",
        "overlap", "patch_size", "source_image", "label_path",
        "created_utc", "preprocessing_version",
    )

    def to_dict(self) -> dict[str, Any]:
        return {c: getattr(self, c) for c in self.COLUMNS}


@dataclass(frozen=True)
class ValidationRecord:
    """A single validation issue for a sample."""

    sample_id: str
    category: str
    message: str
    severity: str = SEVERITY_ERROR

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "category": self.category,
            "message": self.message,
            "severity": self.severity,
        }
