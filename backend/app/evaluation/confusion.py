"""Pixel-level multiclass confusion matrix (Milestone 8).

Deterministic integer confusion accumulation. **Row = ground truth (true), column = predicted.**
Configurable class count + ignore label. numpy is guarded (accumulation from arrays needs it; the matrix
itself is a plain nested-int list, so tests can build one without numpy). Serialisable; no tensors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import EvaluationError

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None  # type: ignore


@dataclass
class ConfusionMatrix:
    """A K×K confusion matrix (rows = true class, cols = predicted class)."""

    num_classes: int
    matrix: list[list[int]]
    class_names: list[str] = field(default_factory=list)
    ignore_index: int | None = None

    @classmethod
    def zeros(cls, num_classes: int, class_names: list[str] | tuple[str, ...] | None = None,
              ignore_index: int | None = None) -> "ConfusionMatrix":
        names = list(class_names) if class_names else [f"class_{i}" for i in range(num_classes)]
        matrix = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
        return cls(num_classes=num_classes, matrix=matrix, class_names=names, ignore_index=ignore_index)

    # --- accumulation -----------------------------------------------------------------------------
    def accumulate(self, targets: Any, predictions: Any) -> "ConfusionMatrix":
        """Add counts from a batch of integer label arrays (rows=true=targets, cols=pred).

        Ignored pixels (``ignore_index``) are excluded. Raises on shape mismatch or out-of-range labels.
        """
        if np is None:
            raise EvaluationError("numpy is required to accumulate a confusion matrix from arrays.")
        t = np.asarray(targets).reshape(-1)
        p = np.asarray(predictions).reshape(-1)
        if t.shape != p.shape:
            raise EvaluationError(f"targets/predictions shape mismatch: {t.shape} vs {p.shape}.")
        if self.ignore_index is not None:
            keep = t != self.ignore_index
            t, p = t[keep], p[keep]
        if t.size:
            if t.min() < 0 or t.max() >= self.num_classes or p.min() < 0 or p.max() >= self.num_classes:
                raise EvaluationError(
                    f"labels out of range [0, {self.num_classes - 1}] in confusion accumulation.")
            index = t.astype(np.int64) * self.num_classes + p.astype(np.int64)
            counts = np.bincount(index, minlength=self.num_classes ** 2).reshape(
                self.num_classes, self.num_classes)
            self.matrix = (np.asarray(self.matrix, dtype=np.int64) + counts).tolist()
        return self

    def add(self, other: "ConfusionMatrix") -> "ConfusionMatrix":
        """Return the element-wise sum of two matrices (must have the same class count)."""
        if other.num_classes != self.num_classes:
            raise EvaluationError("Cannot add confusion matrices with different class counts.")
        summed = [[self.matrix[r][c] + other.matrix[r][c] for c in range(self.num_classes)]
                  for r in range(self.num_classes)]
        return ConfusionMatrix(self.num_classes, summed, list(self.class_names), self.ignore_index)

    # --- derived counts (per class) ---------------------------------------------------------------
    def total(self) -> int:
        return sum(sum(row) for row in self.matrix)

    def diagonal_sum(self) -> int:
        return sum(self.matrix[c][c] for c in range(self.num_classes))

    def tp(self, c: int) -> int:
        return self.matrix[c][c]

    def fp(self, c: int) -> int:  # predicted c but true other = column sum − diagonal
        return sum(self.matrix[r][c] for r in range(self.num_classes)) - self.matrix[c][c]

    def fn(self, c: int) -> int:  # true c but predicted other = row sum − diagonal
        return sum(self.matrix[c]) - self.matrix[c][c]

    def tn(self, c: int) -> int:
        return self.total() - self.tp(c) - self.fp(c) - self.fn(c)

    def support(self, c: int) -> int:   # number of true pixels of class c
        return sum(self.matrix[c])

    def predicted(self, c: int) -> int:  # number of pixels predicted as class c
        return sum(self.matrix[r][c] for r in range(self.num_classes))

    # --- serialisation ----------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "num_classes": self.num_classes,
            "matrix": self.matrix,
            "class_names": list(self.class_names),
            "ignore_index": self.ignore_index,
            "row_semantics": "true_class",
            "col_semantics": "predicted_class",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfusionMatrix":
        return cls(
            num_classes=int(data["num_classes"]),
            matrix=[[int(x) for x in row] for row in data["matrix"]],
            class_names=list(data.get("class_names", [])),
            ignore_index=data.get("ignore_index"),
        )
