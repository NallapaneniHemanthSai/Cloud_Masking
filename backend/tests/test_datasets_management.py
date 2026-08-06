"""Milestone 3 verification: dataset-management helpers, manifest, and structured verification.

Dataset-management only (no preprocessing/ML, no network, no real downloads). Covers:
manifest parsing, invalid-manifest detection, checksum verification, missing-directory detection, and
download-status detection.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.core.exceptions import ConfigurationError
from app.datasets import manifest as manifest_mod
from app.datasets.integrity import check_paths_exist, compute_checksum, verify_checksum
from app.datasets.manifest import DatasetRecord
from app.datasets.verification import (
    DL_DOWNLOADED,
    DL_NOT_DOWNLOADED,
    DIR_MISSING,
    DIR_PRESENT,
    OVERALL_PASS,
    OVERALL_PENDING,
    render_table,
    verify_all,
    verify_dataset,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "datasets.yaml"

EXPECTED_DATASETS = {"cloudsen12": "raw/cloudsen12", "on_cloud_n": "raw/on_cloud_n"}

# Minimal valid manifest text used for parsing tests (mirrors the required expanded schema).
_VALID_ENTRY = """
datasets:
  demo:
    dataset_id: demo
    name: Demo
    version: "1.0"
    homepage: https://example.org
    source: https://example.org/data
    official_paper: https://example.org/paper
    citation: "Demo et al. (2026)"
    license: "CC0-1.0"
    redistribution: "Permitted"
    download_required: true
    manual_steps: ["step one"]
    expected_directory: "raw/demo"
    expected_size: "small"
    checksum_algorithm: "sha256"
    checksum: "TBD"
    download_date: ""
    bands: {level: "demo"}
    label_schema: {type: binary, classes: {0: no_cloud, 1: cloud}}
    intended_use: "testing"
    notes: "none"
"""


def _record(dataset_id: str = "demo", expected_directory: str = "raw/demo",
            checksum: str = "TBD", expected_files: list[str] | None = None) -> DatasetRecord:
    """Construct a DatasetRecord directly (no YAML) for network-free verification tests."""
    return DatasetRecord(
        dataset_id=dataset_id, name="Demo", version="1.0", homepage="h", source="s",
        official_paper="p", citation="c", license="CC0-1.0", redistribution="Permitted",
        download_required=True, manual_steps=["s1"], expected_directory=expected_directory,
        expected_size="small", checksum_algorithm="sha256", checksum=checksum,
        download_date="", bands={}, label_schema={}, intended_use="u", notes="n",
        expected_files=expected_files or [],
    )


# ---------------------------------------------------------------------------------------------------
# Checksum verification
# ---------------------------------------------------------------------------------------------------

def test_compute_and_verify_checksum(tmp_path: Path) -> None:
    payload = b"cloud-masking milestone 3"
    target = tmp_path / "sample.bin"
    target.write_bytes(payload)
    assert compute_checksum(target) == hashlib.sha256(payload).hexdigest()
    assert verify_checksum(target, hashlib.sha256(payload).hexdigest()) is True
    assert verify_checksum(target, "deadbeef") is False
    assert verify_checksum(target, "") is False  # unverified, not corrupt


def test_check_paths_exist_reports_missing(tmp_path: Path) -> None:
    (tmp_path / "there.txt").write_text("x", encoding="utf-8")
    result = check_paths_exist(tmp_path, ["there.txt", "absent.txt"])
    assert result.present == ["there.txt"] and result.missing == ["absent.txt"]
    assert result.ok is False


# ---------------------------------------------------------------------------------------------------
# Missing-directory & download-status detection (no YAML needed)
# ---------------------------------------------------------------------------------------------------

def test_missing_directory_detection(tmp_path: Path) -> None:
    """A nonexistent expected folder -> MISSING/NOT_DOWNLOADED/PENDING (not a failure)."""
    result = verify_dataset(_record(), data_root=tmp_path)
    assert result.directory_status == DIR_MISSING
    assert result.download_status == DL_NOT_DOWNLOADED
    assert result.overall == OVERALL_PENDING


def test_download_status_ignores_scaffolding(tmp_path: Path) -> None:
    """A folder with only README/.gitkeep still reads as NOT_DOWNLOADED."""
    folder = tmp_path / "raw" / "demo"
    folder.mkdir(parents=True)
    (folder / "README.md").write_text("doc", encoding="utf-8")
    (folder / ".gitkeep").write_text("", encoding="utf-8")
    result = verify_dataset(_record(), data_root=tmp_path)
    assert result.directory_status == DIR_PRESENT
    assert result.download_status == DL_NOT_DOWNLOADED
    assert result.overall == OVERALL_PENDING


def test_download_status_detects_data(tmp_path: Path) -> None:
    """A folder with a real data file reads as DOWNLOADED and PASS (no expected_files/checksum -> not FAIL)."""
    folder = tmp_path / "raw" / "demo"
    folder.mkdir(parents=True)
    (folder / "chip_0001.tif").write_bytes(b"\x00\x01\x02")
    result = verify_dataset(_record(), data_root=tmp_path)
    assert result.download_status == DL_DOWNLOADED
    assert result.overall == OVERALL_PASS


def test_render_table_contains_headers(tmp_path: Path) -> None:
    report = verify_all({"demo": _record()}, data_root=tmp_path)
    table = render_table(report)
    for header in ("Dataset", "Manifest", "Directory", "Download", "Checksum", "Overall"):
        assert header in table
    assert report.passed is True  # PENDING passes without --require-present


# ---------------------------------------------------------------------------------------------------
# Manifest parsing / invalid-manifest detection (require PyYAML)
# ---------------------------------------------------------------------------------------------------

@pytest.mark.skipif(manifest_mod.yaml is None, reason="PyYAML not installed")
def test_manifest_parses_valid(tmp_path: Path) -> None:
    path = tmp_path / "datasets.yaml"
    path.write_text(_VALID_ENTRY, encoding="utf-8")
    records = manifest_mod.load_manifest(path)
    assert "demo" in records
    assert records["demo"].license == "CC0-1.0"
    assert records["demo"].checksum_available is False  # "TBD" placeholder


@pytest.mark.skipif(manifest_mod.yaml is None, reason="PyYAML not installed")
def test_manifest_rejects_missing_field(tmp_path: Path) -> None:
    bad = _VALID_ENTRY.replace('    license: "CC0-1.0"\n', "")  # drop a required field
    path = tmp_path / "bad.yaml"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(ConfigurationError):
        manifest_mod.load_manifest(path)


@pytest.mark.skipif(manifest_mod.yaml is None, reason="PyYAML not installed")
def test_project_manifest_is_consistent() -> None:
    """The real project manifest validates and declares both datasets with correct folders."""
    records = manifest_mod.load_manifest(MANIFEST_PATH)
    for key, expected_dir in EXPECTED_DATASETS.items():
        assert key in records, f"Manifest missing dataset '{key}'"
        assert records[key].expected_directory == expected_dir
        assert records[key].citation.strip() and records[key].license.strip()
