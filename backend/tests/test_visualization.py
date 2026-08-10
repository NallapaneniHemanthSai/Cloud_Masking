"""Milestone 5 verification: visualization & EDA (synthetic data only, no real datasets).

Covers visualization records, statistics, report serialization, QC summaries, colour mapping, patch
visualization metadata, and graceful backend degradation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.exceptions import CloudMaskingError
from app.preprocessing.patch_manifest import build_patch_records
from app.preprocessing.records import SampleRecord
from app.preprocessing.splitting import split_samples
from app.preprocessing.validation import (
    CORRUPTED_METADATA,
    DUPLICATE_ID,
    MISSING_LABEL,
    ValidationReport,
)
from app.visualization.backends import (
    MatplotlibBackend,
    NullBackend,
    get_backend,
    matplotlib_available,
)
from app.visualization.bands import default_rgb_bands, rgb_composite_spec, single_band_spec
from app.visualization.colormap import ClassColor, ColorMap, get_colormap
from app.visualization.exporters import export_report, render_figure
from app.visualization.inspection import inspect_dataset
from app.visualization.overlays import legend_for, overlay_spec
from app.visualization.patches import patch_grid_metadata, patch_grid_spec
from app.visualization.plotting import class_distribution_chart
from app.visualization.qc import build_qc_report
from app.visualization.records import FigureKind, FigureSpec, RenderStatus
from app.visualization.reports import (
    Report,
    ReportSection,
    build_dataset_report,
    build_patch_report,
    build_split_report,
)
from app.visualization.statistics import (
    ClassDistribution,
    PatchStatistics,
    SplitStatistics,
    compute_dataset_statistics,
)

HAS_MPL = matplotlib_available()


def _samples(n: int, with_labels: bool = True) -> list[SampleRecord]:
    return [SampleRecord(f"s{i}", "demo", [Path(f"img/{i}.tif")],
                         Path(f"lbl/{i}.tif") if with_labels else None) for i in range(n)]


# ---------------------------------------------------------------------------------------------------
# Records / colormap
# ---------------------------------------------------------------------------------------------------

def test_figure_spec_and_render_result() -> None:
    spec = FigureSpec(kind=FigureKind.BAR.value, title="t", payload={"labels": [1], "values": [2]})
    assert spec.to_dict()["kind"] == "bar"


def test_colormap_lookup_legend_and_hexlist() -> None:
    cmap = get_colormap("cloudsen12")
    assert cmap.get(0).name == "clear"
    assert len(cmap.hex_list()) == 4
    legend = cmap.legend()
    assert legend.labels()[0] == "clear" and legend.colors()[0].startswith("#")


def test_colormap_rejects_duplicate_index() -> None:
    with pytest.raises(CloudMaskingError):
        ColorMap([ClassColor(0, "a", "#000000"), ClassColor(0, "b", "#ffffff")])


def test_get_colormap_unknown_raises() -> None:
    with pytest.raises(CloudMaskingError):
        get_colormap("nope")


# ---------------------------------------------------------------------------------------------------
# Statistics (deterministic)
# ---------------------------------------------------------------------------------------------------

def test_class_distribution_frequencies_and_balance() -> None:
    dist = ClassDistribution.from_counts({0: 80, 1: 20})
    assert dist.total == 100
    assert dist.frequencies()[0] == 0.8
    assert dist.balance_ratio() == 0.25


def test_compute_dataset_statistics_from_records() -> None:
    samples = _samples(5, with_labels=False)
    stats = compute_dataset_statistics("demo", samples)
    assert stats.num_samples == 5 and stats.num_missing_labels == 5
    # deterministic serialisation
    assert stats.to_dict() == compute_dataset_statistics("demo", samples).to_dict()


def test_patch_statistics_from_records() -> None:
    sample = SampleRecord("chip1", "demo", [Path("chip1.tif")], Path("lbl.tif"))
    records = build_patch_records(sample, "train", 64, 0, (128, 128),
                                  created_utc="2026-01-01T00:00:00+00:00")
    ps = PatchStatistics.from_records(records)
    assert ps.num_patches == 4 and ps.patch_size == 64 and ps.per_split["train"] == 4


def test_split_statistics_from_manifest() -> None:
    manifest = split_samples([f"s{i}" for i in range(10)], seed=1)
    ss = SplitStatistics.from_manifest(manifest)
    assert sum(ss.counts.values()) == 10 and ss.seed == 1


# ---------------------------------------------------------------------------------------------------
# Reports (JSON / CSV / Markdown) + builders
# ---------------------------------------------------------------------------------------------------

def test_report_serialization_roundtrip(tmp_path: Path) -> None:
    report = Report(title="T", created_utc="2026-01-01T00:00:00+00:00")
    report.add(ReportSection(title="Summary", data={"a": 1, "b": 2}))
    report.add(ReportSection(title="Table", kind="table", columns=["x", "y"],
                             rows=[{"x": 1, "y": 2}, {"x": 3, "y": 4}]))
    # json
    parsed = json.loads(report.to_json())
    assert parsed["title"] == "T" and len(parsed["sections"]) == 2
    # markdown
    md = report.to_markdown()
    assert "# T" in md and "| x | y |" in md
    # csv
    csv_text = report.to_csv()
    assert "section" in csv_text.splitlines()[0]
    # save all formats
    written = report.save(tmp_path / "rep", formats=("json", "md", "csv"))
    assert set(written) == {"json", "md", "csv"} and all(p.is_file() for p in written.values())


def test_build_dataset_and_split_and_patch_reports() -> None:
    inspection = inspect_dataset("demo", _samples(4))
    dr = build_dataset_report(inspection, created_utc="2026-01-01T00:00:00+00:00")
    assert dr.title.endswith("demo") and any(s.title == "Validation summary" for s in dr.sections)

    ss = SplitStatistics.from_manifest(split_samples([f"s{i}" for i in range(10)], seed=1))
    assert "Split counts" in build_split_report(ss).to_markdown()

    sample = SampleRecord("c1", "demo", [Path("c1.tif")], Path("l.tif"))
    ps = PatchStatistics.from_records(
        build_patch_records(sample, "train", 64, 0, (128, 128), created_utc="t"))
    assert build_patch_report(ps).to_json()


# ---------------------------------------------------------------------------------------------------
# QC report
# ---------------------------------------------------------------------------------------------------

def test_qc_report_counts_and_markdown() -> None:
    vr = ValidationReport(samples_checked=3)
    vr.add("s1", DUPLICATE_ID, "dup")
    vr.add("s2", CORRUPTED_METADATA, "boom")
    vr.add("s3", MISSING_LABEL, "no label", severity="WARNING")
    qc = build_qc_report("demo", vr)
    assert qc.duplicate_identifiers == 1 and qc.corrupted_samples == 1 and qc.missing_labels == 1
    assert qc.passed is False  # has ERROR records
    md = qc.to_markdown()
    assert "Quality-control report: demo" in md and "duplicate identifiers" in md
    assert any("no label" in w for w in qc.warnings)


# ---------------------------------------------------------------------------------------------------
# Patch visualization metadata
# ---------------------------------------------------------------------------------------------------

def test_patch_grid_metadata_and_spec() -> None:
    sample = SampleRecord("c1", "demo", [Path("c1.tif")], Path("l.tif"))
    records = build_patch_records(sample, "train", 64, 16, (128, 128), created_utc="t")
    meta = patch_grid_metadata(records)
    assert meta.num_patches == len(records) and meta.overlap == 16 and meta.has_overlap is True
    spec = patch_grid_spec(records, (128, 128))
    assert spec.kind == FigureKind.PATCH_GRID.value
    assert spec.payload["image_size"] == [128, 128]
    assert len(spec.payload["rectangles"]) == len(records)


# ---------------------------------------------------------------------------------------------------
# Band / overlay specs
# ---------------------------------------------------------------------------------------------------

def test_band_and_overlay_specs() -> None:
    rgb = rgb_composite_spec(Path("img.tif"), default_rgb_bands("cloudsen12"))
    assert rgb.payload["band_indices"] == [3, 2, 1] and rgb.payload["mode"] == "rgb"
    assert single_band_spec(Path("img.tif"), 0).options["cmap"] == "gray"
    ov = overlay_spec(Path("img.tif"), Path("mask.tif"), get_colormap("on_cloud_n"), alpha=0.4)
    assert ov.kind == FigureKind.OVERLAY.value and ov.payload["alpha"] == 0.4
    with pytest.raises(ValueError):
        overlay_spec(Path("i"), Path("m"), get_colormap("on_cloud_n"), alpha=2.0)
    assert legend_for(get_colormap("on_cloud_n")).labels() == ["no_cloud", "cloud"]


# ---------------------------------------------------------------------------------------------------
# Plotting spec builders (deterministic)
# ---------------------------------------------------------------------------------------------------

def test_class_distribution_chart_deterministic() -> None:
    dist = ClassDistribution.from_counts({0: 10, 1: 5, 2: 1})
    a = class_distribution_chart(dist)
    b = class_distribution_chart(dist)
    assert a.to_dict() == b.to_dict()
    assert a.payload["labels"] == ["0", "1", "2"] and a.payload["values"] == [10, 5, 1]


# ---------------------------------------------------------------------------------------------------
# Backend graceful degradation
# ---------------------------------------------------------------------------------------------------

def test_get_backend_null_and_auto() -> None:
    assert isinstance(get_backend("null"), NullBackend)
    assert get_backend("auto").name in {"matplotlib", "null"}


def test_null_backend_writes_sidecar(tmp_path: Path) -> None:
    spec = FigureSpec(kind=FigureKind.BAR.value, title="t", payload={"labels": ["a"], "values": [1]})
    result = NullBackend().render(spec, tmp_path / "fig.png")
    assert result.status == RenderStatus.DEGRADED.value and result.ok
    assert result.sidecar_path and Path(result.sidecar_path).is_file()
    assert json.loads(Path(result.sidecar_path).read_text())["title"] == "t"


def test_render_figure_degrades_via_null(tmp_path: Path) -> None:
    spec = FigureSpec(kind=FigureKind.BAR.value, title="t", payload={"labels": ["a"], "values": [1]})
    result = render_figure(spec, tmp_path / "fig.png", backend_name="null")
    assert result.status == RenderStatus.DEGRADED.value


@pytest.mark.skipif(not HAS_MPL, reason="matplotlib not installed")
def test_matplotlib_backend_renders_bar(tmp_path: Path) -> None:
    spec = FigureSpec(kind=FigureKind.BAR.value, title="t",
                      payload={"labels": ["a", "b"], "values": [1, 2]})
    out = tmp_path / "bar.png"
    result = MatplotlibBackend().render(spec, out)
    assert result.status == RenderStatus.RENDERED.value and out.is_file()


@pytest.mark.skipif(not HAS_MPL, reason="matplotlib not installed")
def test_matplotlib_backend_renders_patch_grid(tmp_path: Path) -> None:
    sample = SampleRecord("c1", "demo", [Path("c1.tif")], Path("l.tif"))
    records = build_patch_records(sample, "train", 64, 0, (128, 128), created_utc="t")
    spec = patch_grid_spec(records, (128, 128))
    out = tmp_path / "grid.png"
    result = MatplotlibBackend().render(spec, out)
    assert result.status == RenderStatus.RENDERED.value and out.is_file()
