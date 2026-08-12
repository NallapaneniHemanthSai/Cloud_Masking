"""Binary cloud evaluation helpers (Milestone 8).

Binary evaluation (``non_cloud`` / ``cloud``) is a **separate mode** from CloudSEN12's four-class
evaluation and is **never mixed** with it (ADR-0008, §5). On Cloud N labels are already binary
(``0 = no_cloud``, ``1 = cloud``, verified in M3), so no mapping is needed there.

This module provides a **documented, opt-in** mapping for deliberately viewing CloudSEN12 as cloud-vs-clear.
It is never applied automatically. numpy is guarded.
"""

from __future__ import annotations

from typing import Any

from app.core.constants import CloudClass
from app.core.exceptions import EvaluationError

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None  # type: ignore

# Documented mapping for an opt-in cloud-vs-clear view of CloudSEN12:
#   cloud (1)      = {thick_cloud, thin_cloud}
#   non_cloud (0)  = {clear, cloud_shadow}   (cloud shadow is a cloud-caused artifact, not cloud itself)
# This is a deliberate choice; alternative mappings are possible and must be stated when used.
CLOUDSEN12_CLOUD_CLASSES: tuple[int, ...] = (
    CloudClass.THICK_CLOUD.value, CloudClass.THIN_CLOUD.value,
)
BINARY_CLASS_NAMES: tuple[str, str] = ("no_cloud", "cloud")


def collapse_to_binary(labels: Any, cloud_classes: tuple[int, ...] = CLOUDSEN12_CLOUD_CLASSES) -> Any:
    """Map multiclass labels to binary (1 = cloud if label in ``cloud_classes``, else 0).

    This is an explicit, opt-in transformation — apply it only when a cloud-vs-clear view is intended,
    and document the mapping used alongside any reported binary metrics.
    """
    if np is None:
        raise EvaluationError("numpy is required to collapse labels to binary.")
    arr = np.asarray(labels)
    return np.isin(arr, list(cloud_classes)).astype(arr.dtype if arr.dtype.kind in "iu" else "int64")
