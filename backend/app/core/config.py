"""Configuration skeleton for the Cloud Masking backend.

Milestone 2 status: **skeleton only** — declares the configuration surface and loads values from
environment variables using the standard library. No application logic.

Design notes
------------
* This skeleton deliberately depends on the **standard library only** so it imports on a bare Python
  3.11 interpreter (Milestone 2 does not install dependencies).
* In **Milestone 13** this will migrate to ``pydantic-settings`` (already pinned in ``requirements.txt``)
  for validation, typed coercion, and ``.env`` parsing. The field names below are chosen to map 1:1 onto
  the future ``BaseSettings`` model so the migration is mechanical.
* **No hardcoded paths.** All paths derive from :data:`app.core.constants.PROJECT_ROOT` or environment
  overrides, satisfying the "never hardcode paths" requirement.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.core.constants import (
    DEFAULT_API_HOST,
    DEFAULT_API_PORT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_RANDOM_SEED,
    PROJECT_ROOT,
    RunProfile,
)


def _env(name: str, default: str) -> str:
    """Read an environment variable with a default. Kept trivial and side-effect free."""
    return os.environ.get(name, default)


def _env_path(name: str, default: Path) -> Path:
    """Read a path-typed environment variable, falling back to a project-relative default."""
    raw = os.environ.get(name)
    return Path(raw).expanduser().resolve() if raw else default


def _data_root() -> Path:
    """Resolve the data root (``DATA_DIR`` env override or ``<project>/data``).

    Kept as a helper so the dataset subdirectory fields below stay consistent with ``data_dir``.
    """
    return _env_path("DATA_DIR", PROJECT_ROOT / "data")


@dataclass(frozen=True)
class Settings:
    """Immutable application settings skeleton.

    Every field has a safe default so the object constructs without any environment configuration.
    Values are populated from environment variables via :meth:`from_env`.
    """

    # --- Runtime / profile ---------------------------------------------------------------------
    environment: str = _env("APP_ENV", "development")
    run_profile: str = _env("RUN_PROFILE", RunProfile.SMOKE.value)  # "smoke" | "full"

    # --- API -----------------------------------------------------------------------------------
    api_host: str = _env("API_HOST", DEFAULT_API_HOST)
    api_port: int = int(_env("API_PORT", str(DEFAULT_API_PORT)))

    # --- Logging -------------------------------------------------------------------------------
    log_level: str = _env("LOG_LEVEL", DEFAULT_LOG_LEVEL)

    # --- Data / artifact locations (never hardcoded; overridable via env) -----------------------
    data_dir: Path = field(default_factory=_data_root)
    models_dir: Path = field(default_factory=lambda: _env_path("MODELS_DIR", PROJECT_ROOT / "models"))
    outputs_dir: Path = field(default_factory=lambda: _env_path("OUTPUTS_DIR", PROJECT_ROOT / "outputs"))

    # --- Dataset subdirectories (Milestone 3; overridable via env) ------------------------------
    data_raw_dir: Path = field(default_factory=lambda: _env_path("DATA_RAW_DIR", _data_root() / "raw"))
    data_external_dir: Path = field(
        default_factory=lambda: _env_path("DATA_EXTERNAL_DIR", _data_root() / "external")
    )
    data_manifests_dir: Path = field(
        default_factory=lambda: _env_path("DATA_MANIFESTS_DIR", _data_root() / "manifests")
    )
    data_metadata_dir: Path = field(
        default_factory=lambda: _env_path("DATA_METADATA_DIR", _data_root() / "metadata")
    )

    # --- Experiment tracking / database (configured, not connected, at M2) ----------------------
    mlflow_tracking_uri: str = _env("MLFLOW_TRACKING_URI", "file:./outputs/mlruns")
    database_url: str = _env("DATABASE_URL", "sqlite:///./outputs/cloud_masking.db")

    # --- Reproducibility -----------------------------------------------------------------------
    random_seed: int = int(_env("RANDOM_SEED", str(DEFAULT_RANDOM_SEED)))

    @classmethod
    def from_env(cls) -> "Settings":
        """Construct settings from the current environment.

        Returns:
            A fully-populated, immutable :class:`Settings` instance.
        """
        return cls()


def get_settings() -> Settings:
    """Return application settings.

    A thin accessor so call sites do not construct :class:`Settings` directly; this is the seam where
    caching / dependency-injection is added in Milestone 13.
    """
    return Settings.from_env()
