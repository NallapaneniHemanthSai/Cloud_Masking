"""Deterministic hashing utilities (shared).

A single, canonical ``stable_hash`` used across the project (visualization figure/session hashing, model
config hashing) so the logic is not duplicated. Standard-library only; deterministic and order-independent.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(obj: Any) -> str:
    """Return a deterministic sha256 hex digest of a JSON-serialisable object.

    Keys are sorted and separators normalised so equal content always yields the same digest, regardless
    of insertion order. Non-JSON values fall back to ``str``.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
