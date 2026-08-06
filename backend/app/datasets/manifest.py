"""Dataset provenance manifest loading & validation (Milestone 3, revised).

Reads ``data/manifests/datasets.yaml`` into typed :class:`DatasetRecord` objects and validates that the
required provenance fields (expanded schema) are present. This is the single machine-readable source of
dataset provenance.

PyYAML is an optional import here: the module imports cleanly without it (so structure/import checks pass
on a bare interpreter), but :func:`load_manifest` raises a clear, actionable error if YAML parsing is
requested while PyYAML is not installed. No preprocessing or ML logic lives here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.constants import DEFAULT_MANIFEST_FILENAME
from app.core.exceptions import ConfigurationError

try:  # PyYAML is declared in requirements.in but may not be installed yet.
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - exercised only on a bare interpreter
    yaml = None  # type: ignore

logger = logging.getLogger(__name__)

#: Provenance fields every dataset entry must declare (expanded schema — Milestone 3 review §2).
REQUIRED_FIELDS: tuple[str, ...] = (
    "dataset_id",
    "name",
    "version",
    "homepage",
    "source",
    "official_paper",
    "citation",
    "license",
    "redistribution",
    "download_required",
    "manual_steps",
    "expected_directory",
    "expected_size",
    "checksum_algorithm",
    "checksum",
    "download_date",
    "bands",
    "label_schema",
    "intended_use",
    "notes",
)

#: Values (case-insensitive) treated as "no real checksum recorded yet".
_CHECKSUM_PLACEHOLDERS = {"", "TBD", "PLACEHOLDER", "NONE", "REQUIRES VERIFICATION"}


@dataclass
class DatasetRecord:
    """A single dataset's provenance record (expanded schema)."""

    dataset_id: str
    name: str
    version: str
    homepage: str
    source: str
    official_paper: str
    citation: str
    license: str
    redistribution: str
    download_required: bool
    manual_steps: list[str]
    expected_directory: str
    expected_size: str
    checksum_algorithm: str
    checksum: str
    download_date: str
    bands: Any
    label_schema: Any
    intended_use: str
    notes: str
    # Optional extras (tolerated if absent).
    role: str = "unspecified"
    download_urls: list[dict[str, Any]] = field(default_factory=list)
    expected_files: list[str] = field(default_factory=list)

    @property
    def checksum_available(self) -> bool:
        """True when a real (non-placeholder) checksum is recorded."""
        return (self.checksum or "").strip().upper() not in _CHECKSUM_PLACEHOLDERS

    @property
    def manual_access_required(self) -> bool:
        """True when the dataset needs a manual/authenticated download (no direct URLs)."""
        return bool(self.download_required) and not self.download_urls


def _require_yaml() -> None:
    if yaml is None:
        raise ConfigurationError(
            "PyYAML is required to parse the dataset manifest but is not installed. "
            "Install project dependencies (e.g. `pip install -r requirements.in`) and retry."
        )


def _build_record(key: str, entry: dict[str, Any]) -> DatasetRecord:
    """Validate one entry and construct a :class:`DatasetRecord`."""
    if not isinstance(entry, dict):
        raise ConfigurationError(f"Dataset entry '{key}' must be a mapping.")
    missing = [f for f in REQUIRED_FIELDS if f not in entry]
    if missing:
        raise ConfigurationError(
            f"Dataset '{key}' is missing required provenance fields: {', '.join(missing)}"
        )
    manual_steps = entry["manual_steps"]
    if isinstance(manual_steps, str):
        manual_steps = [manual_steps]
    return DatasetRecord(
        dataset_id=str(entry["dataset_id"]),
        name=str(entry["name"]),
        version=str(entry["version"]),
        homepage=str(entry["homepage"]),
        source=str(entry["source"]),
        official_paper=str(entry["official_paper"]),
        citation=str(entry["citation"]),
        license=str(entry["license"]),
        redistribution=str(entry["redistribution"]),
        download_required=bool(entry["download_required"]),
        manual_steps=list(manual_steps or []),
        expected_directory=str(entry["expected_directory"]),
        expected_size=str(entry["expected_size"]),
        checksum_algorithm=str(entry["checksum_algorithm"]),
        checksum=str(entry["checksum"]),
        download_date=str(entry["download_date"]),
        bands=entry["bands"],
        label_schema=entry["label_schema"],
        intended_use=str(entry["intended_use"]),
        notes=str(entry["notes"]),
        role=str(entry.get("role", "unspecified")),
        download_urls=list(entry.get("download_urls", []) or []),
        expected_files=list(entry.get("expected_files", []) or []),
    )


def load_manifest(path: Path) -> dict[str, DatasetRecord]:
    """Load and validate the dataset manifest.

    Args:
        path: Path to ``datasets.yaml``.

    Returns:
        Mapping of dataset key -> :class:`DatasetRecord`.

    Raises:
        ConfigurationError: If PyYAML is missing, the file is absent/malformed, or a record is missing a
            required provenance field.
    """
    _require_yaml()
    path = Path(path)
    if not path.is_file():
        raise ConfigurationError(f"Dataset manifest not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # type: ignore[union-attr]
        raise ConfigurationError(f"Malformed dataset manifest {path}: {exc}") from exc

    datasets = raw.get("datasets")
    if not isinstance(datasets, dict) or not datasets:
        raise ConfigurationError(f"Manifest {path} must contain a non-empty 'datasets' mapping.")

    records = {key: _build_record(key, entry) for key, entry in datasets.items()}
    logger.info("Loaded %d dataset record(s) from %s", len(records), path)
    return records


def default_manifest_path(manifests_dir: Path) -> Path:
    """Return the conventional manifest path within a manifests directory."""
    return Path(manifests_dir) / DEFAULT_MANIFEST_FILENAME
