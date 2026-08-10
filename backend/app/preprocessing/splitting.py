"""Reproducible dataset splitting (Milestone 4).

Deterministic train/validation/test partitioning driven by a seed and configurable ratios. Supports
**group-aware** splitting (all samples sharing a group key land in the same split) to prevent spatial
leakage (NFR-4). Guarantees the three splits are disjoint. Standard-library only; produces a structured
split manifest. No training code.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.core.constants import DEFAULT_RANDOM_SEED, DatasetSplit
from app.core.exceptions import PreprocessingError
from app.preprocessing.config import SplitRatios
from app.preprocessing.records import SplitRecord

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class SplitManifest:
    """Structured, serialisable split result."""

    train: list[str] = field(default_factory=list)
    val: list[str] = field(default_factory=list)
    test: list[str] = field(default_factory=list)
    seed: int = DEFAULT_RANDOM_SEED
    ratios: tuple[float, float, float] = (0.7, 0.15, 0.15)
    grouped: bool = False
    created_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "ratios": {"train": self.ratios[0], "val": self.ratios[1], "test": self.ratios[2]},
            "grouped": self.grouped,
            "created_utc": self.created_utc,
            "counts": {"train": len(self.train), "val": len(self.val), "test": len(self.test)},
            "splits": {"train": self.train, "val": self.val, "test": self.test},
        }

    def to_records(self) -> list[SplitRecord]:
        """Return per-sample :class:`SplitRecord` assignments."""
        records: list[SplitRecord] = []
        for split_name, ids in (
            (DatasetSplit.TRAIN.value, self.train),
            (DatasetSplit.VAL.value, self.val),
            (DatasetSplit.TEST.value, self.test),
        ):
            records.extend(SplitRecord(sample_id=sid, split=split_name) for sid in ids)
        return records

    def split_lookup(self) -> dict[str, str]:
        """Return a mapping of ``sample_id -> split`` for convenient joins."""
        return {r.sample_id: r.split for r in self.to_records()}

    def save_yaml(self, path: Path) -> Path:
        """Write the manifest to YAML (requires PyYAML)."""
        if yaml is None:
            raise PreprocessingError("PyYAML is required to write a split manifest but is not installed.")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8")
        logger.info("Wrote split manifest: %s", path)
        return path


def split_samples(
    sample_ids: Sequence[str],
    ratios: SplitRatios | None = None,
    seed: int = DEFAULT_RANDOM_SEED,
    groups: Mapping[str, str] | None = None,
) -> SplitManifest:
    """Partition ``sample_ids`` into train/val/test deterministically.

    Args:
        sample_ids: All sample identifiers.
        ratios: Split ratios (defaults to project defaults).
        seed: Deterministic seed — the same inputs + seed always yield the same split.
        groups: Optional mapping ``sample_id -> group_key``. When given, whole groups are assigned to a
            single split (leakage-resistant); ratios then apply to *groups*.

    Returns:
        A :class:`SplitManifest` with disjoint train/val/test lists.

    Raises:
        PreprocessingError: On invalid ratios or duplicate sample ids.
    """
    ratios = ratios or SplitRatios()
    ratios.validate()

    ids = list(sample_ids)
    if len(set(ids)) != len(ids):
        raise PreprocessingError("Duplicate sample ids provided to split_samples.")

    if groups:
        assignment = _assign_by_group(ids, ratios, seed, groups)
    else:
        assignment = _assign_flat(ids, ratios, seed)

    manifest = SplitManifest(
        train=assignment[DatasetSplit.TRAIN.value],
        val=assignment[DatasetSplit.VAL.value],
        test=assignment[DatasetSplit.TEST.value],
        seed=seed,
        ratios=ratios.as_tuple(),
        grouped=bool(groups),
        created_utc=datetime.now(timezone.utc).isoformat(),
    )
    _assert_disjoint(manifest)
    logger.info("Split %d sample(s) -> train=%d val=%d test=%d (seed=%d, grouped=%s).",
                len(ids), len(manifest.train), len(manifest.val), len(manifest.test), seed, bool(groups))
    return manifest


def _partition(items: list[str], ratios: SplitRatios) -> dict[str, list[str]]:
    """Partition an already-shuffled list by ratio, giving remainder to train."""
    n = len(items)
    n_val = int(n * ratios.val)
    n_test = int(n * ratios.test)
    n_train = n - n_val - n_test
    return {
        DatasetSplit.TRAIN.value: items[:n_train],
        DatasetSplit.VAL.value: items[n_train:n_train + n_val],
        DatasetSplit.TEST.value: items[n_train + n_val:],
    }


def _assign_flat(ids: list[str], ratios: SplitRatios, seed: int) -> dict[str, list[str]]:
    shuffled = sorted(ids)  # canonical order first -> deterministic regardless of input order
    random.Random(seed).shuffle(shuffled)
    return _partition(shuffled, ratios)


def _assign_by_group(ids: list[str], ratios: SplitRatios, seed: int,
                     groups: Mapping[str, str]) -> dict[str, list[str]]:
    # Map each group to its member sample ids.
    group_members: dict[str, list[str]] = {}
    for sid in ids:
        group_members.setdefault(groups.get(sid, sid), []).append(sid)
    group_keys = sorted(group_members)
    random.Random(seed).shuffle(group_keys)
    grouped_partition = _partition(group_keys, ratios)
    # Expand groups back to sample ids (sorted for determinism).
    return {
        split: sorted(sid for g in keys for sid in group_members[g])
        for split, keys in grouped_partition.items()
    }


def _assert_disjoint(manifest: SplitManifest) -> None:
    sets = {"train": set(manifest.train), "val": set(manifest.val), "test": set(manifest.test)}
    if sets["train"] & sets["val"] or sets["train"] & sets["test"] or sets["val"] & sets["test"]:
        raise PreprocessingError("Splits are not disjoint — duplicate sample across partitions.")
