"""Milestone 5 (revised) verification: FigureManifest + VisualizationSession.

Covers manifest/session serialization + export/import, metadata integrity, and deterministic config
hashing. Synthetic data only; no plotting-library objects.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.visualization.exporters import render_figure_manifested
from app.visualization.inspection import inspect_dataset
from app.visualization.manifest import FigureManifest, stable_hash
from app.visualization.qc import build_qc_report
from app.visualization.records import FigureKind, FigureSpec
from app.visualization.session import ReportRef, VisualizationSession, build_session
from app.preprocessing.records import SampleRecord
from app.preprocessing.validation import ValidationReport, DUPLICATE_ID


# ---------------------------------------------------------------------------------------------------
# Deterministic config hash
# ---------------------------------------------------------------------------------------------------

def test_stable_hash_is_deterministic_and_order_independent() -> None:
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})
    assert stable_hash({"a": 1}) != stable_hash({"a": 2})
    assert len(stable_hash({"x": 1})) == 64  # sha256 hex


# ---------------------------------------------------------------------------------------------------
# FigureManifest
# ---------------------------------------------------------------------------------------------------

def _spec() -> FigureSpec:
    return FigureSpec(kind=FigureKind.BAR.value, title="Class distribution",
                      payload={"labels": ["0", "1"], "values": [8, 2]})


def test_figure_manifest_from_render_and_fields(tmp_path: Path) -> None:
    result, manifest = render_figure_manifested(
        _spec(), tmp_path / "fig.png", backend_name="null",
        created_at="2026-01-01T00:00:00+00:00")
    assert manifest.figure_type == "bar"
    assert manifest.backend == "null"
    assert manifest.config_hash == stable_hash(_spec().to_dict())
    assert manifest.figure_id.startswith("class-distribution-")
    # the null backend wrote a sidecar -> recorded as an output file
    assert manifest.output_files and result.sidecar_path in manifest.output_files


def test_figure_manifest_json_roundtrip_and_export(tmp_path: Path) -> None:
    _, manifest = render_figure_manifested(_spec(), tmp_path / "f.png", backend_name="null",
                                           created_at="2026-01-01T00:00:00+00:00")
    # dict/json roundtrip
    assert FigureManifest.from_dict(manifest.to_dict()).to_dict() == manifest.to_dict()
    assert FigureManifest.from_json(manifest.to_json()).figure_id == manifest.figure_id
    # file export/import
    path = manifest.save_json(tmp_path / "m.json")
    loaded = FigureManifest.load_json(path)
    assert loaded.to_dict() == manifest.to_dict()


def test_figure_manifest_id_is_deterministic(tmp_path: Path) -> None:
    _, a = render_figure_manifested(_spec(), tmp_path / "a.png", backend_name="null", created_at="t")
    _, b = render_figure_manifested(_spec(), tmp_path / "b.png", backend_name="null", created_at="t")
    assert a.figure_id == b.figure_id and a.config_hash == b.config_hash


# ---------------------------------------------------------------------------------------------------
# VisualizationSession
# ---------------------------------------------------------------------------------------------------

def _session(tmp_path: Path) -> VisualizationSession:
    samples = [SampleRecord(f"s{i}", "demo", [Path(f"{i}.tif")], Path(f"l{i}.tif")) for i in range(3)]
    inspection = inspect_dataset("demo", samples)
    vr = ValidationReport(samples_checked=3)
    vr.add("s1", DUPLICATE_ID, "dup")
    qc = build_qc_report("demo", vr)
    session = build_session("demo", inspection, output_dir=str(tmp_path),
                            config={"dataset": "demo"}, qc_report=qc.to_dict(),
                            timestamp="2026-01-01T00:00:00+00:00")
    _, manifest = render_figure_manifested(_spec(), tmp_path / "fig.png", backend_name="null",
                                           created_at="2026-01-01T00:00:00+00:00")
    session.add_figure(manifest)
    session.add_report("Dataset EDA", {"json": tmp_path / "eda.json", "md": tmp_path / "eda.md"})
    return session


def test_session_build_is_deterministic(tmp_path: Path) -> None:
    s = _session(tmp_path)
    assert s.config_hash == stable_hash({"dataset": "demo"})
    assert s.session_id == f"demo-{s.config_hash[:8]}"


def test_session_json_roundtrip_and_export(tmp_path: Path) -> None:
    session = _session(tmp_path)
    # dict/json roundtrip preserves nested manifests/reports/qc
    restored = VisualizationSession.from_dict(session.to_dict())
    assert restored.to_dict() == session.to_dict()
    assert VisualizationSession.from_json(session.to_json()).session_id == session.session_id
    # file export/import
    path = session.save_json(tmp_path / "session.json")
    loaded = VisualizationSession.load_json(path)
    assert loaded.to_dict() == session.to_dict()


def test_session_metadata_integrity(tmp_path: Path) -> None:
    session = _session(tmp_path)
    d = session.to_dict()
    assert d["dataset_summary"]["dataset"] == "demo"
    assert len(d["figures"]) == 1 and d["figures"][0]["figure_type"] == "bar"
    assert d["qc_report"]["duplicate_identifiers"] == 1
    assert d["reports"][0]["title"] == "Dataset EDA"
    # ReportRef roundtrip
    assert ReportRef.from_dict(d["reports"][0]).files == session.reports[0].files
