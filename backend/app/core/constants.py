"""Project-wide constants and enumerations (SCAFFOLD).

Centralises values that would otherwise become "magic numbers/strings" scattered across the codebase,
satisfying the "avoid magic numbers" coding standard. Standard-library only.
"""

from __future__ import annotations

import enum
from pathlib import Path

# --------------------------------------------------------------------------------------------------
# Filesystem anchors — every other path derives from these (never hardcode absolute paths elsewhere).
# constants.py lives at: <PROJECT_ROOT>/backend/app/core/constants.py  ->  parents[3] == PROJECT_ROOT.
# --------------------------------------------------------------------------------------------------
CORE_DIR: Path = Path(__file__).resolve().parent
BACKEND_DIR: Path = CORE_DIR.parents[1]        # <root>/backend
PROJECT_ROOT: Path = CORE_DIR.parents[2]       # <root>

# --------------------------------------------------------------------------------------------------
# Network defaults.
# --------------------------------------------------------------------------------------------------
DEFAULT_API_HOST: str = "127.0.0.1"
DEFAULT_API_PORT: int = 8000
DEFAULT_LOG_LEVEL: str = "INFO"


class RunProfile(str, enum.Enum):
    """Frozen-resource-envelope profiles (see ADR-0002).

    ``SMOKE`` — tiny subset / few steps, runs anywhere and in CI.
    ``FULL``  — the AC-4 frozen envelope used for all reported baseline-vs-candidate comparisons.
    """

    SMOKE = "smoke"
    FULL = "full"


class Dataset(str, enum.Enum):
    """Datasets used by the project (see ADR-0001)."""

    CLOUDSEN12 = "cloudsen12"      # primary, 13-band, multi-class
    ON_CLOUD_N = "on_cloud_n"      # reference benchmark, binary, 4-band


class CloudClass(enum.IntEnum):
    """CloudSEN12 semantic classes (integer label values).

    NOTE: exact label integers are **NOT YET VERIFIED** against the dataset (source-to-claim C-2);
    verified in Milestone 3. These placeholders document intent only.
    """

    CLEAR = 0
    THICK_CLOUD = 1
    THIN_CLOUD = 2       # haze is approximated within this class (Charter §3.1)
    CLOUD_SHADOW = 3
