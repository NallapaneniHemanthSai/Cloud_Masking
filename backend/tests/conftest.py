"""Pytest fixtures and path setup for the backend test suite.

Ensures the ``backend`` directory is importable as the package root (so ``import app`` works) regardless
of the directory pytest is invoked from. This mirrors the ``pythonpath`` setting in ``pyproject.toml``
and makes the tests robust when run from the repository root.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# <root>/backend  (this file is <root>/backend/tests/conftest.py)
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Absolute path to the repository root."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def backend_dir() -> Path:
    """Absolute path to the backend package root."""
    return BACKEND_DIR
