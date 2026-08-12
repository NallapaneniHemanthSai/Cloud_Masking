"""Milestone 2 verification: the backend package imports cleanly.

All ``app`` subpackages must import on a bare Python 3.11 interpreter (no third-party dependencies). This
guards the clean-architecture rule that ``core`` (and the package skeleton) depend only on the standard
library at this stage.
"""

from __future__ import annotations

import importlib

import pytest

# Every module here must import with zero third-party packages installed.
IMPORTABLE_MODULES = [
    "app",
    "app.main",
    "app.core",
    "app.core.config",
    "app.core.constants",
    "app.core.exceptions",
    "app.core.logging_config",
    "app.api",
    "app.api.routers",
    "app.models",
    "app.models._torch",
    "app.models.config",
    "app.models.metadata",
    "app.models.artifact",
    "app.models.initialization",
    "app.models.base",
    "app.models.unet",
    "app.models.summary",
    "app.models.registry",
    "app.models.factory",
    "app.utils.hashing",
    "app.services",
    "app.preprocessing",
    "app.inference",
    "app.training",
    "app.training.config",
    "app.training.seed",
    "app.training.optimizer",
    "app.training.scheduler",
    "app.training.loss",
    "app.training.metadata",
    "app.training.logging",
    "app.training.checkpoint",
    "app.training.callbacks",
    "app.training.engine",
    "app.training.experiment",
    "app.training.lifecycle",
    "app.training.artifact",
    "app.training.trainer",
    "app.evaluation",
    "app.evaluation.config",
    "app.evaluation.confusion",
    "app.evaluation.records",
    "app.evaluation.metrics",
    "app.evaluation.aggregation",
    "app.evaluation.runner",
    "app.evaluation.stratification",
    "app.evaluation.summary",
    "app.evaluation.report",
    "app.evaluation.serialization",
    "app.evaluation.binary",
    "app.datasets",
    "app.change_detection",
    "app.db",
    "app.schemas",
    "app.utils",
    "app.datasets.manifest",
    "app.datasets.integrity",
    "app.datasets.download",
    "app.datasets.verification",
    "app.preprocessing.records",
    "app.preprocessing.config",
    "app.preprocessing.loader",
    "app.preprocessing.validation",
    "app.preprocessing.patching",
    "app.preprocessing.patch_manifest",
    "app.preprocessing.normalization",
    "app.preprocessing.splitting",
    "app.preprocessing.augmentation",
    "app.preprocessing.raster_io",
    "app.preprocessing.pipeline",
    "app.visualization",
    "app.visualization.records",
    "app.visualization.backends",
    "app.visualization.colormap",
    "app.visualization.statistics",
    "app.visualization.inspection",
    "app.visualization.bands",
    "app.visualization.overlays",
    "app.visualization.patches",
    "app.visualization.plotting",
    "app.visualization.reports",
    "app.visualization.qc",
    "app.visualization.manifest",
    "app.visualization.session",
    "app.visualization.exporters",
]


@pytest.mark.parametrize("module_name", IMPORTABLE_MODULES)
def test_module_imports(module_name: str) -> None:
    """Importing the module raises no error."""
    module = importlib.import_module(module_name)
    assert module is not None


def test_settings_construct_without_env() -> None:
    """The configuration skeleton constructs with safe defaults and no environment configuration."""
    from app.core.config import Settings, get_settings

    settings = get_settings()
    assert isinstance(settings, Settings)
    # Paths resolve relative to the project root; ports/seeds carry sane defaults.
    assert settings.api_port > 0
    assert settings.random_seed >= 0
    assert settings.run_profile in {"smoke", "full"}


def test_logging_config_builds() -> None:
    """The logging config builder returns a valid dictConfig-shaped mapping."""
    from app.core.logging_config import build_logging_config

    config = build_logging_config("INFO")
    assert config["version"] == 1
    assert "console" in config["handlers"]
    assert config["root"]["level"] == "INFO"
