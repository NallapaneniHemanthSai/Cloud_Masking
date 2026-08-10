"""Patch manifest generation (Milestone 4, revised).

Records metadata for every generated patch as typed :class:`PatchRecord` objects and exports them to
**JSONL** and **CSV**. Contains no model information — only preprocessing metadata. Patch coordinates come
from the deterministic grid in :mod:`app.preprocessing.patching`.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.constants import PREPROCESSING_VERSION
from app.preprocessing.patching import generate_patch_grid
from app.preprocessing.records import PatchRecord, SampleRecord

logger = logging.getLogger(__name__)


def build_patch_records(
    sample: SampleRecord,
    split: str,
    patch_size: int,
    overlap: int,
    image_size: tuple[int, int],
    *,
    preprocessing_version: str = PREPROCESSING_VERSION,
    created_utc: str | None = None,
) -> list[PatchRecord]:
    """Build patch records for one sample from the deterministic patch grid.

    Args:
        sample: The source sample.
        split: The split this sample belongs to ("train"/"val"/"test").
        patch_size: Patch edge length.
        overlap: Patch overlap.
        image_size: ``(height, width)`` of the source image (from raster metadata).
        preprocessing_version: Version stamp for reproducibility.
        created_utc: Optional fixed timestamp (defaults to now, UTC) — pass a fixed value for
            deterministic tests.

    Returns:
        Ordered list of :class:`PatchRecord`.
    """
    height, width = image_size
    grid = generate_patch_grid(height, width, patch_size, overlap)
    timestamp = created_utc or datetime.now(timezone.utc).isoformat()
    source_image = str(sample.image_paths[0]) if sample.image_paths else ""
    label_path = str(sample.label_path) if sample.label_path else None

    return [
        PatchRecord(
            sample_id=sample.sample_id,
            dataset=sample.dataset,
            split=split,
            patch_index=idx,
            row_off=w.row_off,
            col_off=w.col_off,
            height=w.height,
            width=w.width,
            overlap=overlap,
            patch_size=patch_size,
            source_image=source_image,
            label_path=label_path,
            created_utc=timestamp,
            preprocessing_version=preprocessing_version,
        )
        for idx, w in enumerate(grid)
    ]


@dataclass
class PatchManifest:
    """A collection of :class:`PatchRecord` with JSONL/CSV export."""

    records: list[PatchRecord] = field(default_factory=list)

    def add(self, record: PatchRecord) -> None:
        self.records.append(record)

    def extend(self, records: list[PatchRecord]) -> None:
        self.records.extend(records)

    def __len__(self) -> int:
        return len(self.records)

    # --- Serialisation ----------------------------------------------------------------------------
    def to_jsonl(self) -> str:
        """Serialise as JSON Lines (one JSON object per line)."""
        return "\n".join(json.dumps(r.to_dict()) for r in self.records)

    def to_csv(self) -> str:
        """Serialise as CSV with the canonical :attr:`PatchRecord.COLUMNS` header."""
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(PatchRecord.COLUMNS))
        writer.writeheader()
        for r in self.records:
            writer.writerow(r.to_dict())
        return buffer.getvalue()

    def save_jsonl(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Trailing newline so the file is valid JSONL even when appended to.
        content = self.to_jsonl()
        path.write_text(content + ("\n" if content else ""), encoding="utf-8")
        logger.info("Wrote patch manifest (JSONL, %d records): %s", len(self.records), path)
        return path

    def save_csv(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_csv(), encoding="utf-8")
        logger.info("Wrote patch manifest (CSV, %d records): %s", len(self.records), path)
        return path
