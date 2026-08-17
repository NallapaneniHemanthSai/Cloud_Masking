"""Dataset layer.

Milestone 3 (dataset management) adds provenance/integrity/download helpers:

* :mod:`app.datasets.manifest` — load & validate the provenance manifest (``datasets.yaml``).
* :mod:`app.datasets.integrity` — checksums and file/directory existence checks.
* :mod:`app.datasets.download` — resumable, dependency-free file downloader.

Milestone 12 (experimental-dataset readiness pipeline) adds — **reusing M3/M4/M5**, never duplicating a
downloader/validator/splitter — the modules that turn *"dataset infrastructure exists"* into a *"verified,
reproducible, legally usable, locally available experimental dataset"* (or an honest ``NOT_PRESENT``):

* :mod:`app.datasets.experimental_config` — :class:`ExperimentalDatasetConfig` (+ deterministic hash).
* :mod:`app.datasets.availability` — local-filesystem availability (PRESENT / PARTIAL / NOT_PRESENT).
* :mod:`app.datasets.records` — typed records (validation report, subset, split manifest, class dist.).
* :mod:`app.datasets.validation_gates` — structured :class:`DatasetValidationReport` (reuses M3 integrity).
* :mod:`app.datasets.sampling` — deterministic subset + group-aware split manifest (reuses M4 splitting).
* :mod:`app.datasets.dataset_statistics` — real class distribution + train-only normalization (reuses M4).
* :mod:`app.datasets.artifact` — canonical :class:`DatasetArtifact` (deterministic content hash).
* :mod:`app.datasets.readiness` — :func:`is_experiment_ready` gate + M11 :class:`ExperimentHandoff`.
* :mod:`app.datasets.pipeline` — :func:`prepare_experimental_dataset` orchestration (synthetic / real).
* :mod:`app.datasets.synthetic` — labelled synthetic fixture (PIPELINE VALIDATION ONLY, no rasterio).

numpy is guarded (needed only when real/synthetic arrays are read); the package imports on a bare
interpreter. No real data is ever downloaded automatically; access controls are respected (ADR-0001/0012).
"""

from app.datasets.artifact import DatasetArtifact
from app.datasets.availability import (
    NOT_PRESENT,
    PARTIAL,
    PRESENT,
    AvailabilityReport,
    DatasetAvailability,
    check_availability,
)
from app.datasets.dataset_statistics import (
    class_distribution_report,
    fit_normalization,
    normalization_stats_hash,
)
from app.datasets.experimental_config import (
    CLOUDSEN12_CLASS_MAPPING,
    REQUIRED_CLOUDSEN12_CLASSES,
    THIN_CLOUD_NAME,
    ExperimentalDatasetConfig,
)
from app.datasets.pipeline import (
    PreparedDataset,
    default_processed_dir,
    prepare_experimental_dataset,
)
from app.datasets.readiness import (
    ExperimentHandoff,
    ExperimentReadiness,
    build_handoff,
    is_experiment_ready,
)
from app.datasets.records import (
    ClassDistributionReport,
    DatasetValidationReport,
    ExperimentalDatasetRecord,
    ExperimentalSplitManifest,
    SplitEntry,
    SubsetSelection,
)
from app.datasets.sampling import build_split_manifest, select_subset
from app.datasets.synthetic import (
    SYNTHETIC_BANNER,
    SyntheticDataset,
    generate_synthetic_dataset,
    read_npy_array,
)
from app.datasets.validation_gates import validate_experimental_dataset

__all__ = [
    # config
    "ExperimentalDatasetConfig",
    "CLOUDSEN12_CLASS_MAPPING",
    "REQUIRED_CLOUDSEN12_CLASSES",
    "THIN_CLOUD_NAME",
    # availability
    "check_availability",
    "AvailabilityReport",
    "DatasetAvailability",
    "PRESENT",
    "PARTIAL",
    "NOT_PRESENT",
    # records
    "DatasetValidationReport",
    "ExperimentalDatasetRecord",
    "SubsetSelection",
    "ExperimentalSplitManifest",
    "SplitEntry",
    "ClassDistributionReport",
    # validation
    "validate_experimental_dataset",
    # sampling
    "select_subset",
    "build_split_manifest",
    # statistics
    "class_distribution_report",
    "fit_normalization",
    "normalization_stats_hash",
    # artifact
    "DatasetArtifact",
    # readiness / handoff
    "is_experiment_ready",
    "build_handoff",
    "ExperimentReadiness",
    "ExperimentHandoff",
    # pipeline
    "prepare_experimental_dataset",
    "PreparedDataset",
    "default_processed_dir",
    # synthetic
    "generate_synthetic_dataset",
    "SyntheticDataset",
    "read_npy_array",
    "SYNTHETIC_BANNER",
]
