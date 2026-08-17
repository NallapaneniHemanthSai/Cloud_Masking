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

    VERIFIED (2026-08-06) against the CloudSEN12 paper (Sci Data 9:782, 2022) and the CloudSEN12+
    dataset card (Hugging Face ``tacofoundation/cloudsen12``). See data/metadata/cloudsen12_classes.md.
    """

    CLEAR = 0
    THICK_CLOUD = 1
    THIN_CLOUD = 2       # haze is approximated within this class (Charter §3.1)
    CLOUD_SHADOW = 3


class OnCloudNLabel(enum.IntEnum):
    """On Cloud N (reference benchmark) binary labels.

    VERIFIED (2026-08-06) as binary cloud/no-cloud against the DrivenData competition + benchmark
    write-up. Exact pixel encoding beyond {0,1} to be confirmed at download.
    """

    NO_CLOUD = 0
    CLOUD = 1


# --------------------------------------------------------------------------------------------------
# Dataset management constants (Milestone 3). Folder names, manifest defaults, and download tunables
# are centralised here to avoid magic numbers/strings in scripts.
# --------------------------------------------------------------------------------------------------
DATASET_DIRNAMES: dict[Dataset, str] = {
    Dataset.CLOUDSEN12: "cloudsen12",
    Dataset.ON_CLOUD_N: "on_cloud_n",
}
DEFAULT_MANIFEST_FILENAME: str = "datasets.yaml"
DEFAULT_CHECKSUM_ALGORITHM: str = "sha256"
DOWNLOAD_CHUNK_SIZE: int = 1 << 20     # 1 MiB streaming chunk for downloads/hashing
HTTP_TIMEOUT_SECONDS: int = 60         # network timeout for download requests
PARTIAL_DOWNLOAD_SUFFIX: str = ".part"  # temp suffix for resumable downloads


# --------------------------------------------------------------------------------------------------
# Preprocessing constants (Milestone 4). Centralised to avoid magic numbers in the pipeline; all are
# overridable via PreprocessingConfig / YAML — never hardcode these in modules.
# --------------------------------------------------------------------------------------------------
SUPPORTED_RASTER_EXTENSIONS: frozenset[str] = frozenset({".tif", ".tiff"})
#: Version stamped onto generated preprocessing artifacts (patch manifests, normalization stats).
PREPROCESSING_VERSION: str = "0.4.0"
#: Version stamped onto generated visualization/EDA reports.
VISUALIZATION_VERSION: str = "0.5.0"
#: Version stamped onto the baseline model architecture (U-Net) artifacts.
MODEL_VERSION: str = "0.6.0"
#: Separate version for the improved architecture (Attention U-Net) — does not overwrite the baseline.
IMPROVED_MODEL_VERSION: str = "0.10.0"
#: Version stamped onto training artifacts (training/checkpoint/experiment metadata).
TRAINING_VERSION: str = "0.7.0"
#: Version stamped onto evaluation results/reports.
EVALUATION_VERSION: str = "0.8.0"
#: Version stamped onto failure-analysis results/reports.
FAILURE_ANALYSIS_VERSION: str = "0.9.0"
#: Version stamped onto controlled model-comparison records/artifacts (baseline vs improved).
COMPARISON_VERSION: str = "0.11.0"
#: Version stamped onto experimental-dataset records/manifests/artifacts (dataset readiness pipeline).
DATASET_MANIFEST_VERSION: str = "0.12.0"
DEFAULT_PATCH_SIZE: int = 512          # capped further for the MPS envelope in profiles (ADR-0002)
DEFAULT_PATCH_OVERLAP: int = 0         # pixels of overlap between adjacent patches
DEFAULT_RANDOM_SEED: int = 42          # global reproducibility seed
DEFAULT_SPLIT_RATIOS: tuple[float, float, float] = (0.7, 0.15, 0.15)  # train / val / test
SPLIT_RATIO_TOLERANCE: float = 1e-6    # allowed deviation of ratio sum from 1.0
DEFAULT_MANIFESTS_SPLIT_FILENAME: str = "splits.yaml"
DEFAULT_PROCESSED_DIRNAME: str = "processed"


class NormalizationMode(str, enum.Enum):
    """Supported per-band normalization strategies."""

    NONE = "none"            # pass-through (only nodata/clip handling)
    MINMAX = "minmax"        # scale each band to [0, 1] using per-band min/max
    ZSCORE = "zscore"        # (x - mean) / std per band
    PERCENTILE = "percentile"  # clip to [p_low, p_high] per band, then scale to [0, 1]


DEFAULT_NORMALIZATION_MODE: str = NormalizationMode.MINMAX.value
DEFAULT_PERCENTILE_RANGE: tuple[float, float] = (2.0, 98.0)  # for PERCENTILE mode


class AugmentationOp(str, enum.Enum):
    """Names of the built-in augmentation operations exposed by the framework."""

    FLIP = "flip"
    ROTATE = "rotate"
    CROP = "crop"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"


class DatasetSplit(str, enum.Enum):
    """Canonical dataset partition names."""

    TRAIN = "train"
    VAL = "val"
    TEST = "test"
