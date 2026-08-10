"""Preprocessing pipeline orchestration (Milestone 4).

Ties together discovery, validation, splitting, patching, and normalization. The :meth:`plan` method is a
dry, dependency-light summary (discovery + validation + split manifest + optional patch-count estimate).
The :meth:`process_array` method applies patching + normalization to an in-memory ``(C, H, W)`` numpy
array (deterministic). No model/training/inference code.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.preprocessing.config import PreprocessingConfig
from app.preprocessing.loader import DatasetLayout, DiscoveryResult, discover_samples
from app.preprocessing.normalization import normalize
from app.preprocessing.patch_manifest import PatchManifest, build_patch_records
from app.preprocessing.patching import extract_patches, generate_patch_grid
from app.preprocessing.splitting import SplitManifest, split_samples
from app.preprocessing.validation import ValidationReport, validate_samples

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingPlan:
    """A dry-run summary of what preprocessing would do (no heavy IO)."""

    dataset_id: str
    discovery: DiscoveryResult
    validation: ValidationReport
    split: SplitManifest | None = None
    estimated_patches_per_sample: int | None = None
    messages: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            f"Preprocessing plan — dataset: {self.dataset_id}",
            f"  samples discovered: {self.discovery.count}"
            + (" (dataset MISSING)" if self.discovery.missing else ""),
            "  " + self.validation.render().replace("\n", "\n  "),
        ]
        if self.split is not None:
            c = self.split.to_dict()["counts"]
            lines.append(f"  split: train={c['train']} val={c['val']} test={c['test']} (seed={self.split.seed})")
        if self.estimated_patches_per_sample is not None:
            lines.append(f"  estimated patches/sample: {self.estimated_patches_per_sample}")
        for m in self.messages:
            lines.append(f"  note: {m}")
        return "\n".join(lines)


class PreprocessingPipeline:
    """Coordinates the preprocessing steps for one dataset."""

    def __init__(self, config: PreprocessingConfig, layout: DatasetLayout) -> None:
        self.config = config
        self.layout = layout

    def plan(self, root: Path, sample_image_size: tuple[int, int] | None = None) -> PreprocessingPlan:
        """Produce a dry plan: discovery + validation + deterministic split (+ optional patch estimate)."""
        discovery = discover_samples(root, self.layout)
        validation = validate_samples(discovery.samples)  # path/type/id checks only (no rasterio needed)

        split: SplitManifest | None = None
        if discovery.samples:
            groups = self._groups(discovery)
            split = split_samples(
                [s.sample_id for s in discovery.samples],
                ratios=self.config.split_ratios,
                seed=self.config.random_seed,
                groups=groups,
            )

        estimate: int | None = None
        if sample_image_size is not None:
            h, w = sample_image_size
            estimate = len(generate_patch_grid(h, w, self.config.patch_size, self.config.overlap))

        plan = PreprocessingPlan(
            dataset_id=self.layout.dataset_id,
            discovery=discovery,
            validation=validation,
            split=split,
            estimated_patches_per_sample=estimate,
        )
        if discovery.missing:
            plan.messages.append("Dataset not present — download it first (see docs/datasets/).")
        return plan

    def _groups(self, discovery: DiscoveryResult) -> dict[str, str] | None:
        """Derive a grouping map for leakage-resistant splitting, if a group key is configured."""
        if not self.config.group_by:
            return None
        groups = {s.sample_id: (s.group or s.sample_id) for s in discovery.samples}
        return groups

    def process_array(self, image: Any) -> list[Any]:
        """Patch + normalize an in-memory (C, H, W) numpy array. Deterministic; numpy required.

        Returns:
            A list of normalized patch arrays (numpy).
        """
        patches = extract_patches(image, self.config.patch_size, self.config.overlap)
        return [
            normalize(patch, self.config.normalization_mode, nodata=self.config.nodata_value)
            for patch in patches
        ]

    def build_patch_manifest(
        self,
        discovery: DiscoveryResult,
        split: SplitManifest,
        image_sizes: dict[str, tuple[int, int]] | tuple[int, int],
    ) -> PatchManifest:
        """Build a :class:`PatchManifest` for discovered samples using their split assignment.

        Args:
            discovery: Discovery result with samples.
            split: Split manifest providing the per-sample split assignment.
            image_sizes: Either a single ``(H, W)`` applied to all samples, or a mapping of
                ``sample_id -> (H, W)`` (from raster metadata).

        Returns:
            A populated :class:`PatchManifest` (no pixel data, no model info).
        """
        lookup = split.split_lookup()
        manifest = PatchManifest()
        for sample in discovery.samples:
            size = image_sizes if isinstance(image_sizes, tuple) else image_sizes.get(sample.sample_id)
            if size is None:
                continue
            manifest.extend(build_patch_records(
                sample, lookup.get(sample.sample_id, "train"),
                self.config.patch_size, self.config.overlap, size,
            ))
        return manifest
