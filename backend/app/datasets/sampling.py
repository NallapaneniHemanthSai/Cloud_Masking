"""Deterministic subset selection + group-aware split manifest (Milestone 12).

Builds a **reproducible** curated subset (guaranteeing required-class presence, incl. thin cloud) and a
**leakage-resistant** group-aware train/val/test split by **reusing M4** ``split_samples`` — no second
splitter. Selection uses labels only to *guarantee class presence in the pool*; the split itself is
group-aware and label-agnostic (ADR-0012). Standard-library only; deterministic given ``(seed, subset_size,
strategy)``.
"""

from __future__ import annotations

import logging
import random
from typing import Mapping, Sequence

from app.datasets.experimental_config import ExperimentalDatasetConfig
from app.datasets.records import (
    REGIME_REAL,
    ExperimentalSplitManifest,
    SplitEntry,
    SubsetSelection,
)
from app.preprocessing.config import SplitRatios
from app.preprocessing.splitting import split_samples

logger = logging.getLogger(__name__)


def select_subset(
    sample_ids: Sequence[str],
    *,
    config: ExperimentalDatasetConfig,
    groups: Mapping[str, str],
    sample_classes: Mapping[str, set[str]] | None = None,
    data_regime: str = REGIME_REAL,
) -> SubsetSelection:
    """Select a deterministic curated subset that guarantees required-class presence.

    Args:
        sample_ids: Candidate pool ids.
        config: Experimental config (seed, subset_size, required_classes, strategy).
        groups: ``sample_id -> group/scene id``.
        sample_classes: Optional ``sample_id -> set(class_names present)``. When given, one sample per
            required class is force-included so the subset can never miss thin cloud / cloud shadow.
        data_regime: ``REAL`` or ``SYNTHETIC``.
    """
    pool = sorted(set(sample_ids))                     # canonical order -> deterministic
    rng = random.Random(config.seed)
    selected: list[str] = []
    notes = ""

    # 1) Guarantee each required class appears (deterministic: smallest id covering the class).
    if sample_classes:
        for cls in config.required_classes:
            if any(cls in sample_classes.get(sid, set()) for sid in selected):
                continue
            covering = [sid for sid in pool if cls in sample_classes.get(sid, set())]
            if covering:
                selected.append(covering[0])
        if len(selected) > config.subset_size:
            notes = (f"required-class guarantee needs {len(selected)} samples "
                     f"> subset_size {config.subset_size}; kept all for class coverage.")

    # 2) Fill the remaining budget from a seeded shuffle of the rest.
    remaining = [sid for sid in pool if sid not in selected]
    rng.shuffle(remaining)
    for sid in remaining:
        if len(selected) >= config.subset_size:
            break
        selected.append(sid)

    selected = sorted(selected)
    class_presence: dict[str, bool] = {}
    if sample_classes:
        covered: set[str] = set()
        for sid in selected:
            covered |= sample_classes.get(sid, set())
        class_presence = {c: (c in covered) for c in config.required_classes}

    selection = SubsetSelection(
        strategy=config.subset_strategy, seed=config.seed, requested_size=config.subset_size,
        selected_ids=selected, group_ids={sid: groups.get(sid, sid) for sid in selected},
        class_presence=class_presence, pool_size=len(pool), data_regime=data_regime, notes=notes)
    logger.info("Selected %d/%d sample(s) (strategy=%s, seed=%d).",
                selection.size, len(pool), config.subset_strategy, config.seed)
    return selection


def build_split_manifest(
    selection: SubsetSelection,
    *,
    config: ExperimentalDatasetConfig,
    dataset_version: str,
) -> ExperimentalSplitManifest:
    """Build a leakage-checked group-aware split manifest for a subset (reuses M4 ``split_samples``)."""
    ratios = SplitRatios(train=config.split_ratios[0], val=config.split_ratios[1],
                         test=config.split_ratios[2])
    groups = selection.group_ids
    m4_manifest = split_samples(selection.selected_ids, ratios=ratios, seed=config.seed, groups=groups)
    lookup = m4_manifest.split_lookup()

    entries = [SplitEntry(sample_id=sid, group_id=groups.get(sid, sid), split=lookup[sid])
               for sid in selection.selected_ids if sid in lookup]
    manifest = ExperimentalSplitManifest(
        entries=entries, seed=config.seed, dataset_version=dataset_version,
        preprocessing_version=config.preprocessing_version, ratios=tuple(config.split_ratios),
        grouped=True)

    if not manifest.leakage_ok():
        # Reuse M4's guarantee; this should never trigger, but we assert it explicitly (section 8).
        from app.core.exceptions import PreprocessingError
        raise PreprocessingError("Split leakage detected — samples or groups shared across splits.")
    logger.info("Split manifest: %s (leakage_ok=%s).", manifest.counts(), manifest.leakage_ok())
    return manifest
