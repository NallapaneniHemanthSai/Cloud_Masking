"""Dataset loading / sample discovery (Milestone 4).

Reusable, dependency-free utilities to discover samples on disk for CloudSEN12 and On Cloud N. This
module does **no** array reading or preprocessing — it only enumerates samples and their file paths so
downstream validation/patching can act on them. Reading raster pixels/metadata is delegated to
``app.preprocessing.raster_io`` (guarded rasterio).

Two layout modes cover both datasets without duplicated logic:

* ``paired_band_dirs`` — each sample is a sub-directory containing one file per band, with labels in a
  parallel directory (On Cloud N: ``train_features/<id>/{B02,B03,B04,B08}.tif`` + ``train_labels/<id>.tif``).
* ``paired_files`` — images and labels are single files named by id in parallel directories
  (a generic layout usable for CloudSEN12 exports: ``images/<id>.tif`` + ``labels/<id>.tif``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.core.constants import SUPPORTED_RASTER_EXTENSIONS, Dataset
from app.preprocessing.records import SampleRecord

logger = logging.getLogger(__name__)

# Backwards-compatible alias: the canonical type is SampleRecord (in records.py).
Sample = SampleRecord

MODE_PAIRED_BAND_DIRS = "paired_band_dirs"
MODE_PAIRED_FILES = "paired_files"


@dataclass(frozen=True)
class DatasetLayout:
    """Describes how to find samples for a dataset on disk."""

    dataset_id: str
    mode: str
    images_subdir: str
    labels_subdir: str
    band_filenames: tuple[str, ...] = ()   # for MODE_PAIRED_BAND_DIRS
    label_extension: str = ".tif"


#: Default layouts for the project's datasets. Overridable by callers.
DEFAULT_LAYOUTS: dict[str, DatasetLayout] = {
    Dataset.ON_CLOUD_N.value: DatasetLayout(
        dataset_id=Dataset.ON_CLOUD_N.value,
        mode=MODE_PAIRED_BAND_DIRS,
        images_subdir="train_features",
        labels_subdir="train_labels",
        band_filenames=("B02.tif", "B03.tif", "B04.tif", "B08.tif"),
        label_extension=".tif",
    ),
    Dataset.CLOUDSEN12.value: DatasetLayout(
        dataset_id=Dataset.CLOUDSEN12.value,
        mode=MODE_PAIRED_FILES,
        images_subdir="images",
        labels_subdir="labels",
        label_extension=".tif",
    ),
}


@dataclass
class DiscoveryResult:
    """Structured outcome of sample discovery (never raises for a missing dataset)."""

    dataset_id: str
    root: Path
    samples: list[SampleRecord] = field(default_factory=list)
    missing: bool = False
    messages: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.samples)


def _is_supported_raster(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_RASTER_EXTENSIONS


def get_layout(dataset_id: str) -> DatasetLayout:
    """Return the default layout for a dataset id, or raise KeyError if unknown."""
    return DEFAULT_LAYOUTS[dataset_id]


def discover_samples(root: Path, layout: DatasetLayout) -> DiscoveryResult:
    """Discover samples under ``root`` using ``layout``.

    Gracefully reports (rather than raising) when the dataset or its expected subdirectories are absent.
    """
    root = Path(root)
    result = DiscoveryResult(dataset_id=layout.dataset_id, root=root)

    images_dir = root / layout.images_subdir
    labels_dir = root / layout.labels_subdir
    if not images_dir.is_dir():
        result.missing = True
        result.messages.append(f"Images directory not found: {images_dir} (dataset not downloaded?)")
        logger.warning("%s: %s", layout.dataset_id, result.messages[-1])
        return result

    if layout.mode == MODE_PAIRED_BAND_DIRS:
        _discover_paired_band_dirs(images_dir, labels_dir, layout, result)
    elif layout.mode == MODE_PAIRED_FILES:
        _discover_paired_files(images_dir, labels_dir, layout, result)
    else:  # pragma: no cover - guarded by construction
        result.messages.append(f"Unknown layout mode: {layout.mode}")

    logger.info("%s: discovered %d sample(s) under %s", layout.dataset_id, result.count, images_dir)
    return result


def _discover_paired_band_dirs(images_dir: Path, labels_dir: Path,
                               layout: DatasetLayout, result: DiscoveryResult) -> None:
    """On Cloud N style: per-sample sub-directory of band files + parallel labels dir."""
    for chip_dir in sorted(p for p in images_dir.iterdir() if p.is_dir()):
        sample_id = chip_dir.name
        image_paths = [chip_dir / band for band in layout.band_filenames]
        label_path = labels_dir / f"{sample_id}{layout.label_extension}"
        result.samples.append(SampleRecord(
            sample_id=sample_id,
            dataset=layout.dataset_id,
            image_paths=image_paths,
            label_path=label_path if label_path.exists() else None,
        ))


def _discover_paired_files(images_dir: Path, labels_dir: Path,
                           layout: DatasetLayout, result: DiscoveryResult) -> None:
    """Generic style: images/<id>.ext + labels/<id>.ext."""
    for image_path in sorted(p for p in images_dir.iterdir()
                             if p.is_file() and _is_supported_raster(p)):
        sample_id = image_path.stem
        label_path = labels_dir / f"{sample_id}{layout.label_extension}"
        result.samples.append(SampleRecord(
            sample_id=sample_id,
            dataset=layout.dataset_id,
            image_paths=[image_path],
            label_path=label_path if label_path.exists() else None,
        ))
