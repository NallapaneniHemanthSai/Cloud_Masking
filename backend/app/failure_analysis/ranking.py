"""Deterministic ranking, deduplication, and top-K selection (Milestone 9).

Ranking total order (ADR-0009): **1) severity (desc), 2) error_rate (desc), 3) error_count (desc),
4) sample_id (asc)**. Deduplication by ``sample_id`` keeps the worst entry per sample (so a sample never
occupies multiple ranked slots). Standard-library only; fully deterministic.
"""

from __future__ import annotations

from typing import Callable

from app.failure_analysis.records import HardExample, SampleFailure


def _canonical_key(sf: SampleFailure):
    """The documented total-order key (higher severity/rate/count first, then sample_id ascending)."""
    return (-sf.severity_rank, -sf.error_rate, -sf.error_count, sf.sample_id)


def dedup_by_sample(failures: list[SampleFailure]) -> list[SampleFailure]:
    """Keep the worst (canonical-order) failure per ``sample_id``. Deterministic."""
    best: dict[str, SampleFailure] = {}
    for sf in failures:
        current = best.get(sf.sample_id)
        if current is None or _canonical_key(sf) < _canonical_key(current):
            best[sf.sample_id] = sf
    return sorted(best.values(), key=_canonical_key)


def rank_samples(failures: list[SampleFailure]) -> list[SampleFailure]:
    """Deduplicate + sort by the canonical order, assigning 1-based ``rank`` in place."""
    ranked = dedup_by_sample(failures)
    for i, sf in enumerate(ranked):
        sf.rank = i + 1
    return ranked


def top_k(failures: list[SampleFailure], k: int, *, criterion: str = "error_rate",
          class_name: str | None = None, error_type: str | None = None) -> list[HardExample]:
    """Deterministic top-K hard examples.

    Args:
        failures: Sample failures (deduplicated internally).
        k: Number of examples.
        criterion: Primary metric — ``"error_rate"`` or ``"error_count"``.
        class_name: If set, restrict to samples with that (true) class among their errors.
        error_type: If set, restrict to samples whose categories include this error type.
    """
    pool = dedup_by_sample(failures)
    if class_name is not None:
        pool = [f for f in pool
                if class_name in f.per_class_errors or f.dominant_true_class == class_name]
    if error_type is not None:
        pool = [f for f in pool if error_type in f.categories]

    primary: Callable[[SampleFailure], float]
    primary = (lambda f: f.error_count) if criterion == "error_count" else (lambda f: f.error_rate)
    # Primary criterion first, then the canonical tie-break order.
    pool.sort(key=lambda f: (-primary(f), -f.severity_rank, -f.error_rate, -f.error_count, f.sample_id))

    label = class_name or error_type or criterion
    return [
        HardExample(sample_id=f.sample_id, criterion=label, value=float(primary(f)), rank=i + 1,
                    severity=f.severity, category=(error_type or ""), source_reference=f.source_reference)
        for i, f in enumerate(pool[:k])
    ]
