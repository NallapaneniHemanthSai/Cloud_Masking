"""Milestone 2 verification: project directory structure exists.

These tests assert the scaffold is present and correctly shaped. They must pass on a bare Python 3.11
interpreter with **no third-party packages installed**.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Directories that must exist after Milestone 2.
REQUIRED_DIRS = [
    "backend/app/api/routers",
    "backend/app/core",
    "backend/app/models",
    "backend/app/services",
    "backend/app/preprocessing",
    "backend/app/inference",
    "backend/app/training",
    "backend/app/evaluation",
    "backend/app/datasets",
    "backend/app/change_detection",
    "backend/app/db",
    "backend/app/schemas",
    "backend/app/visualization",
    "backend/app/utils",
    "backend/tests",
    "backend/configs",
    "backend/scripts",
    "frontend/src/components",
    "frontend/src/pages",
    "frontend/src/services",
    "frontend/src/hooks",
    "frontend/src/utils",
    "frontend/src/assets",
    "docker",
    "docs",
    "data/raw",
    "data/processed",
    "data/samples",
    "models",
    "models/checkpoints",
    "notebooks",
    "outputs",
    "experiments",
    "data/raw/cloudsen12",
    "data/raw/on_cloud_n",
    "data/external",
    "data/manifests",
    "data/metadata",
    "docs/datasets",
    ".github/workflows",
]

# Individual files that must exist after Milestone 2.
REQUIRED_FILES = [
    "backend/pyproject.toml",
    "backend/requirements.in",
    "backend/requirements-dev.in",
    "backend/.env.example",
    "backend/README.md",
    "backend/configs/config.template.yaml",
    "backend/configs/logging.yaml",
    "backend/app/__init__.py",
    "backend/app/main.py",
    "backend/app/core/config.py",
    "backend/app/core/constants.py",
    "backend/app/core/exceptions.py",
    "backend/app/core/logging_config.py",
    "backend/app/schemas/__init__.py",
    "backend/app/datasets/manifest.py",
    "backend/app/datasets/integrity.py",
    "backend/app/datasets/download.py",
    "backend/app/datasets/verification.py",
    "backend/app/preprocessing/records.py",
    "backend/app/preprocessing/config.py",
    "backend/app/preprocessing/loader.py",
    "backend/app/preprocessing/validation.py",
    "backend/app/preprocessing/patching.py",
    "backend/app/preprocessing/patch_manifest.py",
    "backend/app/preprocessing/normalization.py",
    "backend/app/preprocessing/splitting.py",
    "backend/app/preprocessing/augmentation.py",
    "backend/app/preprocessing/raster_io.py",
    "backend/app/preprocessing/pipeline.py",
    "backend/app/visualization/__init__.py",
    "backend/app/visualization/records.py",
    "backend/app/visualization/backends.py",
    "backend/app/visualization/colormap.py",
    "backend/app/visualization/statistics.py",
    "backend/app/visualization/inspection.py",
    "backend/app/visualization/bands.py",
    "backend/app/visualization/overlays.py",
    "backend/app/visualization/patches.py",
    "backend/app/visualization/plotting.py",
    "backend/app/visualization/reports.py",
    "backend/app/visualization/qc.py",
    "backend/app/visualization/manifest.py",
    "backend/app/visualization/session.py",
    "backend/app/visualization/exporters.py",
    "backend/scripts/_dataset_cli.py",
    "backend/scripts/download_cloudsen12.py",
    "backend/scripts/download_on_cloud_n.py",
    "backend/scripts/verify_datasets.py",
    "backend/scripts/preprocess.py",
    "backend/scripts/split_dataset.py",
    "backend/scripts/eda_report.py",
    "data/manifests/datasets.yaml",
    "data/metadata/sentinel2_bands.md",
    "docs/datasets/licenses.md",
    "frontend/package.json",
    "docker/docker-compose.yml",
    ".github/workflows/ci-backend.yml",
    ".github/workflows/ci-frontend.yml",
    ".gitignore",
    "README.md",
]


@pytest.mark.parametrize("rel_dir", REQUIRED_DIRS)
def test_required_directory_exists(rel_dir: str) -> None:
    """Each required scaffold directory is present."""
    path = PROJECT_ROOT / rel_dir
    assert path.is_dir(), f"Missing required directory: {rel_dir}"


@pytest.mark.parametrize("rel_file", REQUIRED_FILES)
def test_required_file_exists(rel_file: str) -> None:
    """Each required scaffold file is present."""
    path = PROJECT_ROOT / rel_file
    assert path.is_file(), f"Missing required file: {rel_file}"
