"""Failure taxonomy + severity (Milestone 9).

Typed confusing-case categories and their **measurability**, plus an evidence-based severity scale. A
category is only ever reported as measurable when the available prediction/metadata supports it (ADR-0009);
otherwise it is DEFERRED (needs spatial mask analysis) or NOT_MEASURABLE (needs probabilities). Standard-
library only.
"""

from __future__ import annotations

import enum
from typing import Any


class FailureCategory(str, enum.Enum):
    """Confusing-case / failure categories."""

    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"
    CLASS_CONFUSION = "class_confusion"
    THIN_CLOUD_FAILURE = "thin_cloud_failure"
    THICK_CLOUD_FAILURE = "thick_cloud_failure"
    CLOUD_SHADOW_FAILURE = "cloud_shadow_failure"
    CLEAR_SURFACE_FAILURE = "clear_surface_failure"
    EDGE_ERROR = "edge_error"
    SMALL_OBJECT_FAILURE = "small_object_failure"
    HIGH_CONFIDENCE_ERROR = "high_confidence_error"
    LOW_CONFIDENCE_ERROR = "low_confidence_error"


class Measurability(str, enum.Enum):
    """Whether a category can be measured from the currently available data."""

    MEASURABLE = "measurable"
    DEFERRED = "deferred"              # needs spatial mask analysis (edges / connected components)
    NOT_MEASURABLE = "not_measurable"  # needs predicted probabilities (confidence)


#: Measurability of each category (ADR-0009). Never claim measurable beyond what confusion/labels support.
CATEGORY_MEASURABILITY: dict[FailureCategory, Measurability] = {
    FailureCategory.FALSE_POSITIVE: Measurability.MEASURABLE,
    FailureCategory.FALSE_NEGATIVE: Measurability.MEASURABLE,
    FailureCategory.CLASS_CONFUSION: Measurability.MEASURABLE,
    FailureCategory.CLEAR_SURFACE_FAILURE: Measurability.MEASURABLE,
    FailureCategory.THICK_CLOUD_FAILURE: Measurability.MEASURABLE,
    FailureCategory.THIN_CLOUD_FAILURE: Measurability.MEASURABLE,
    FailureCategory.CLOUD_SHADOW_FAILURE: Measurability.MEASURABLE,
    FailureCategory.EDGE_ERROR: Measurability.DEFERRED,
    FailureCategory.SMALL_OBJECT_FAILURE: Measurability.DEFERRED,
    FailureCategory.HIGH_CONFIDENCE_ERROR: Measurability.NOT_MEASURABLE,
    FailureCategory.LOW_CONFIDENCE_ERROR: Measurability.NOT_MEASURABLE,
}

#: Per-class failure category for a given (true) class name (multiclass only).
CLASS_FAILURE_CATEGORY: dict[str, FailureCategory] = {
    "clear": FailureCategory.CLEAR_SURFACE_FAILURE,
    "thick_cloud": FailureCategory.THICK_CLOUD_FAILURE,
    "thin_cloud": FailureCategory.THIN_CLOUD_FAILURE,
    "cloud_shadow": FailureCategory.CLOUD_SHADOW_FAILURE,
}


def measurable_categories() -> list[FailureCategory]:
    return [c for c, m in CATEGORY_MEASURABILITY.items() if m == Measurability.MEASURABLE]


def taxonomy_table() -> list[dict[str, str]]:
    """Return the taxonomy as serialisable rows (category + measurability)."""
    return [{"category": c.value, "measurability": CATEGORY_MEASURABILITY[c].value}
            for c in FailureCategory]


class Severity(enum.IntEnum):
    """Evidence-based severity scale (higher = worse). NONE means no error."""

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    def to_dict(self) -> dict[str, Any]:  # convenience
        return {"name": self.name, "rank": int(self)}
