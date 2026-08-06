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
