"""Pixel-level error analysis (Milestone 9).

Derives per-class error records **from the M8 confusion matrix** — reusing ``ConfusionMatrix``'s
``fp``/``fn``/``support``/``predicted`` (no duplicated metric math, ADR-0009). For each class it emits a
false-negative, a false-positive, and the dominant class-confusion record. Standard-library only.
"""

from __future__ import annotations

from app.evaluation.confusion import ConfusionMatrix
from app.failure_analysis.config import FailureAnalysisConfig
from app.failure_analysis.records import ErrorRecord
from app.failure_analysis.taxonomy import FailureCategory


def _dominant_in_row(matrix: list[list[int]], c: int, k: int) -> tuple[int | None, int]:
    """Largest off-diagonal count in row ``c`` (true c → predicted c'); ties break on smaller index."""
    best_idx, best_cnt = None, 0
    for cp in range(k):
        if cp == c:
            continue
        if matrix[c][cp] > best_cnt:
            best_idx, best_cnt = cp, matrix[c][cp]
    return best_idx, best_cnt


def _dominant_in_col(matrix: list[list[int]], c: int, k: int) -> tuple[int | None, int]:
    """Largest off-diagonal count in column ``c`` (true r → predicted c); ties break on smaller index."""
    best_idx, best_cnt = None, 0
    for r in range(k):
        if r == c:
            continue
        if matrix[r][c] > best_cnt:
            best_idx, best_cnt = r, matrix[r][c]
    return best_idx, best_cnt


def _name(names: list[str], idx: int | None) -> str:
    return names[idx] if (idx is not None and idx < len(names)) else ""


def analyze_pixels(confusion: ConfusionMatrix, config: FailureAnalysisConfig) -> list[ErrorRecord]:
    """Produce per-class :class:`ErrorRecord`s (FN, FP, dominant confusion) from a confusion matrix."""
    names = confusion.class_names or [f"class_{i}" for i in range(confusion.num_classes)]
    matrix = confusion.matrix
    k = confusion.num_classes
    thresholds = config.severity_thresholds
    records: list[ErrorRecord] = []

    def make(class_name: str, predicted_class: str, error_type: str, count: int,
             denom: int, notes: str = "") -> ErrorRecord:
        rate = (count / denom) if denom > 0 else None
        return ErrorRecord(
            dataset=config.dataset, split=config.split, class_name=class_name,
            predicted_class=predicted_class, error_type=error_type, error_count=count,
            error_rate=rate, support=denom, severity=thresholds.severity_for(rate).name,
            evaluation_version=config.evaluation_version, analysis_version=config.analysis_version,
            config_hash=config.config_hash(), notes=notes)

    for c in range(k):
        support = confusion.support(c)        # true pixels of class c
        predicted = confusion.predicted(c)    # pixels predicted as c
        fn, fp = confusion.fn(c), confusion.fp(c)

        # False negative (true c predicted otherwise), with the dominant wrong target.
        dom_pred_idx, _ = _dominant_in_row(matrix, c, k)
        records.append(make(names[c], _name(names, dom_pred_idx),
                            FailureCategory.FALSE_NEGATIVE.value, fn, support))

        # False positive (predicted c but true otherwise), noting the dominant confused source.
        dom_src_idx, _ = _dominant_in_col(matrix, c, k)
        records.append(make(names[c], names[c], FailureCategory.FALSE_POSITIVE.value, fp, predicted,
                            notes=f"dominant source true class: {_name(names, dom_src_idx)}"))

        # Dominant class confusion (true c -> predicted c').
        cp_idx, cp_cnt = _dominant_in_row(matrix, c, k)
        if cp_idx is not None and cp_cnt > 0:
            records.append(make(names[c], names[cp_idx], FailureCategory.CLASS_CONFUSION.value,
                                cp_cnt, support))

    # Deterministic rank by severity, error_rate, error_count.
    records.sort(key=lambda e: (-_sev_rank(e.severity), -(e.error_rate or 0.0), -e.error_count,
                                e.class_name, e.error_type))
    for i, rec in enumerate(records):
        rec.rank = i + 1
    return records


def _sev_rank(name: str) -> int:
    from app.failure_analysis.taxonomy import Severity
    return int(Severity[name])
