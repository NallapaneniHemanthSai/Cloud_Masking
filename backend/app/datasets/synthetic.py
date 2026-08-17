"""Synthetic raster-like fixture (Milestone 12) — PIPELINE VALIDATION ONLY.

Generates a tiny, deterministic, **synthetic** dataset (numpy ``.npy`` band + label files) so the whole
experimental-dataset pipeline can be exercised **without rasterio and without any real data**. It is
loudly labelled and is **never** merged into the real provenance manifest.

    SYNTHETIC / PIPELINE VALIDATION ONLY / NOT REAL DATA / NOT A BENCHMARK

Each patch deliberately contains all four CloudSEN12 classes (with thin cloud a rare stripe) so the
readiness gate's required-class / thin-cloud checks and the class-imbalance reporting are exercised.
numpy is required (guarded).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.constants import DEFAULT_RANDOM_SEED, CloudClass
from app.core.exceptions import PreprocessingError
from app.datasets.integrity import compute_checksum
from app.preprocessing.records import SampleRecord

logger = logging.getLogger(__name__)

SYNTHETIC_BANNER = "SYNTHETIC / PIPELINE VALIDATION ONLY / NOT REAL DATA / NOT A BENCHMARK"


def read_npy_array(path: Path) -> Any:
    """Read a ``.npy`` array (the synthetic fixture's raster substitute)."""
    import numpy as np  # guarded local import
    return np.load(Path(path))


@dataclass
class SyntheticDataset:
    """A generated synthetic dataset + the readers/metadata the pipeline needs."""

    root: Path
    samples: list[SampleRecord]
    groups: dict[str, str]
    sample_classes: dict[str, set[str]]
    checksums: dict[str, str]
    band_count: int
    num_classes: int
    image_size: tuple[int, int]
    class_names: list[str]
    banner: str = SYNTHETIC_BANNER
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def sample_ids(self) -> list[str]:
        return [s.sample_id for s in self.samples]


def _synthetic_label(size: int, num_classes: int):
    """A deterministic label with all classes present; thin cloud is a rare stripe (imbalance)."""
    import numpy as np
    lab = np.zeros((size, size), dtype="int64")           # clear (0) background
    lab[: size // 3, : size // 3] = CloudClass.THICK_CLOUD.value          # thick block
    lab[-size // 3:, -size // 3:] = CloudClass.CLOUD_SHADOW.value         # shadow block
    lab[size // 2, :] = CloudClass.THIN_CLOUD.value                       # thin stripe (1 row => rare)
    if num_classes < 4:                                    # collapse for smaller schemas
        lab = np.clip(lab, 0, num_classes - 1)
    return lab


def generate_synthetic_dataset(
    root: Path,
    *,
    num_scenes: int = 8,
    patches_per_scene: int = 3,
    size: int = 16,
    band_count: int = 13,
    num_classes: int = 4,
    seed: int = DEFAULT_RANDOM_SEED,
) -> SyntheticDataset:
    """Write a deterministic synthetic dataset under ``root`` and return its handles."""
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise PreprocessingError("numpy is required to generate the synthetic fixture.") from exc

    root = Path(root)
    images_dir = root / "images"
    labels_dir = root / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.RandomState(seed)
    class_names = [c.name.lower() for c in CloudClass][:num_classes]
    samples: list[SampleRecord] = []
    groups: dict[str, str] = {}
    sample_classes: dict[str, set[str]] = {}
    checksums: dict[str, str] = {}

    for s in range(num_scenes):
        group = f"scene_{s:02d}"
        for p in range(patches_per_scene):
            sid = f"{group}_p{p}"
            image = rng.rand(band_count, size, size).astype("float32")
            label = _synthetic_label(size, num_classes)

            img_path = images_dir / f"{sid}.npy"
            lab_path = labels_dir / f"{sid}.npy"
            np.save(img_path, image)
            np.save(lab_path, label)
            checksums[str(img_path)] = compute_checksum(img_path)
            checksums[str(lab_path)] = compute_checksum(lab_path)

            samples.append(SampleRecord(sample_id=sid, dataset="cloudsen12_synthetic",
                                        image_paths=[img_path], label_path=lab_path, group=group))
            groups[sid] = group
            present = {class_names[int(v)] for v in np.unique(label) if int(v) < num_classes}
            sample_classes[sid] = present

    # Write a checksums sidecar (real sha256s over the synthetic files).
    sidecar = root / "checksums.sha256"
    sidecar.write_text("\n".join(f"{h}  {p}" for p, h in sorted(checksums.items())), encoding="utf-8")

    logger.info("Generated SYNTHETIC dataset: %d sample(s), %d scene(s) under %s (%s).",
                len(samples), num_scenes, root, SYNTHETIC_BANNER)
    return SyntheticDataset(
        root=root, samples=samples, groups=groups, sample_classes=sample_classes, checksums=checksums,
        band_count=band_count, num_classes=num_classes, image_size=(size, size), class_names=class_names,
        extras={"checksums_sidecar": str(sidecar)})
