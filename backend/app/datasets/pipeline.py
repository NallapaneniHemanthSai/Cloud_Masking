"""Experimental-dataset preparation pipeline (Milestone 12).

Orchestrates the full **acquisition → validation → subset → split → normalization → class distribution →
artifact → readiness → M11 handoff** flow by composing the M12 modules (which themselves reuse M3/M4/M5).
Two regimes:

* **synthetic** — build the numpy fixture and run the whole pipeline end-to-end (PIPELINE VALIDATION ONLY);
* **real** — inspect the local filesystem only (never downloads). When the dataset is absent the result is
  an honest ``NOT_PRESENT`` artifact whose readiness gate is ``False`` — M11 real training must not run.

No second downloader/validator/splitter is created; everything is reused. Standard-library + numpy(guarded).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.constants import DEFAULT_PROCESSED_DIRNAME
from app.datasets.artifact import DatasetArtifact
from app.datasets.availability import NOT_PRESENT as AVAIL_NOT_PRESENT
from app.datasets.availability import AvailabilityReport, check_availability
from app.datasets.dataset_statistics import (
    class_distribution_report,
    fit_normalization,
    normalization_stats_hash,
)
from app.datasets.experimental_config import ExperimentalDatasetConfig
from app.datasets.readiness import (
    ExperimentHandoff,
    ExperimentReadiness,
    build_handoff,
    is_experiment_ready,
)
from app.datasets.records import (
    NOT_PRESENT,
    REGIME_REAL,
    REGIME_SYNTHETIC,
    ClassDistributionReport,
    DatasetValidationReport,
    ExperimentalDatasetRecord,
    ExperimentalSplitManifest,
    SubsetSelection,
)
from app.datasets.sampling import build_split_manifest, select_subset
from app.datasets.synthetic import SYNTHETIC_BANNER, generate_synthetic_dataset, read_npy_array
from app.datasets.validation_gates import validate_experimental_dataset
from app.preprocessing.patch_manifest import PatchManifest, build_patch_records
from app.preprocessing.records import SampleRecord

logger = logging.getLogger(__name__)


@dataclass
class PreparedDataset:
    """Everything produced by preparing one experimental dataset."""

    config: ExperimentalDatasetConfig
    data_regime: str
    validation: DatasetValidationReport
    dataset_record: ExperimentalDatasetRecord
    artifact: DatasetArtifact
    readiness: ExperimentReadiness
    handoff: ExperimentHandoff
    availability: AvailabilityReport | None = None
    subset: SubsetSelection | None = None
    split_manifest: ExperimentalSplitManifest | None = None
    class_distribution: ClassDistributionReport | None = None
    normalization_hash: str = ""
    patch_count: int = 0
    output_dir: Path | None = None
    written: dict[str, str] = field(default_factory=dict)


def prepare_experimental_dataset(
    config: ExperimentalDatasetConfig,
    *,
    synthetic: bool = False,
    output_dir: Path | None = None,
    data_root: Path | None = None,
    synthetic_scenes: int = 8,
    synthetic_patches_per_scene: int = 3,
    synthetic_size: int = 32,
) -> PreparedDataset:
    """Prepare an experimental dataset (synthetic pipeline validation, or a real-data readiness check)."""
    if synthetic:
        return _prepare_synthetic(config, output_dir=output_dir, num_scenes=synthetic_scenes,
                                  patches_per_scene=synthetic_patches_per_scene, size=synthetic_size)
    return _prepare_real(config, data_root=data_root, output_dir=output_dir)


# --------------------------------------------------------------------------------------------------
# Synthetic regime (PIPELINE VALIDATION ONLY).
# --------------------------------------------------------------------------------------------------
def _prepare_synthetic(config: ExperimentalDatasetConfig, *, output_dir: Path | None,
                       num_scenes: int, patches_per_scene: int, size: int) -> PreparedDataset:
    out = Path(output_dir) if output_dir else None
    raw_root = (out / "raw_synthetic") if out else Path("./_synthetic_tmp")
    ds = generate_synthetic_dataset(
        raw_root, num_scenes=num_scenes, patches_per_scene=patches_per_scene, size=size,
        band_count=config.band_count, num_classes=config.class_count, seed=config.seed)

    # 1) Validation (reuses M3 integrity + injectable .npy reader).
    validation = validate_experimental_dataset(
        config.dataset_id, ds.samples, num_classes=config.class_count,
        required_classes=config.required_classes, class_mapping=config.class_mapping,
        label_reader=read_npy_array, checksums=ds.checksums, expected_bands=None,
        metadata_ok=True, data_regime=REGIME_SYNTHETIC)

    # 2) Deterministic curated subset (guarantees required classes / thin cloud).
    subset = select_subset(ds.sample_ids, config=config, groups=ds.groups,
                           sample_classes=ds.sample_classes, data_regime=REGIME_SYNTHETIC)
    dataset_version = config.dataset_version or f"synthetic-{subset.selection_hash()[:8]}"

    # 3) Group-aware split (reuses M4 split_samples) + persist.
    split_manifest = build_split_manifest(subset, config=config, dataset_version=dataset_version)
    by_id = {s.sample_id: s for s in ds.samples}
    samples_by_split: dict[str, list[SampleRecord]] = {
        split: [by_id[sid] for sid in split_manifest.ids_for(split) if sid in by_id]
        for split in ("train", "val", "test")}

    # 4) Real class distribution (thin cloud surfaced).
    distribution = class_distribution_report(
        samples_by_split, label_reader=read_npy_array, class_mapping=config.class_mapping,
        data_regime=REGIME_SYNTHETIC)

    # 5) Normalization fit on TRAIN ONLY (reuses M4).
    train_images = [s.image_paths[0] for s in samples_by_split["train"] if s.image_paths]
    norm_stats = fit_normalization(train_images, image_reader=read_npy_array,
                                   normalization_mode=config.normalization_mode,
                                   nodata_value=config.nodata_value)
    norm_hash = normalization_stats_hash(norm_stats)

    # 6) Patch manifest (reuses M4 PatchManifest / build_patch_records).
    patch_size_used = min(config.patch_size, size)
    manifest = PatchManifest()
    for split in ("train", "val", "test"):
        for s in samples_by_split[split]:
            manifest.extend(build_patch_records(s, split, patch_size_used, config.overlap, (size, size)))

    # 7) Observed dataset record (section 4) — synthetic, never merged with real provenance.
    observed_files = [str(p) for s in ds.samples for p in s.image_paths] + \
                     [str(s.label_path) for s in ds.samples if s.label_path]
    record = ExperimentalDatasetRecord(
        dataset_id=config.dataset_id, dataset_name="CloudSEN12 (SYNTHETIC fixture)", version=dataset_version,
        source=SYNTHETIC_BANNER, source_url="N/A (synthetic)", license="SYNTHETIC (public-domain fixture)",
        access_status="synthetic", download_date="N/A", local_path=str(ds.root),
        expected_files=[str(p) for p in sorted(ds.checksums)][:8], observed_files=observed_files[:8],
        checksum="verified (synthetic sha256)", patch_count=len(manifest), band_count=config.band_count,
        class_count=config.class_count, class_mapping={str(k): v for k, v in config.class_mapping.items()},
        patch_dimensions=f"{size}x{size}", spatial_resolution="N/A (synthetic)",
        preprocessing_version=config.preprocessing_version, manifest_version=config.manifest_version,
        data_regime=REGIME_SYNTHETIC, notes=SYNTHETIC_BANNER)

    counts = split_manifest.counts()
    artifact = DatasetArtifact.create(
        dataset_id=config.dataset_id, dataset_version=dataset_version,
        manifest_version=config.manifest_version, preprocessing_version=config.preprocessing_version,
        config_hash=config.config_hash(), subset_selection_hash=subset.selection_hash(),
        split_manifest_hash=split_manifest.split_config_hash(), normalization_statistics_hash=norm_hash,
        validation_report=validation.to_dict(), class_distribution=distribution.to_dict(),
        dataset_record=record.to_dict(), sample_count=subset.size, patch_count=len(manifest),
        train_count=counts["train"], validation_count=counts["val"], test_count=counts["test"],
        data_regime=REGIME_SYNTHETIC, notes=SYNTHETIC_BANNER)

    readiness = is_experiment_ready(artifact, split_manifest=split_manifest, config=config,
                                    dataset_record=record)

    written = _write_outputs(out, artifact, split_manifest, norm_stats, distribution, validation,
                             manifest, record) if out else {}
    handoff = build_handoff(
        artifact, readiness, config,
        dataset_artifact_path=written.get("artifact", ""),
        split_manifest_path=written.get("split_manifest", ""),
        normalization_statistics_path=written.get("normalization", ""))
    if out:
        import json
        handoff_path = out / "experiment_handoff.json"
        handoff_path.write_text(json.dumps(handoff.to_dict(), indent=2), encoding="utf-8")
        written["handoff"] = str(handoff_path)

    logger.info("SYNTHETIC dataset prepared: ready=%s, patches=%d, %s.",
                readiness.ready, len(manifest), SYNTHETIC_BANNER)
    return PreparedDataset(
        config=config, data_regime=REGIME_SYNTHETIC, validation=validation, dataset_record=record,
        artifact=artifact, readiness=readiness, handoff=handoff, subset=subset,
        split_manifest=split_manifest, class_distribution=distribution, normalization_hash=norm_hash,
        patch_count=len(manifest), output_dir=out, written=written)


# --------------------------------------------------------------------------------------------------
# Real regime — filesystem inspection only (NEVER downloads).
# --------------------------------------------------------------------------------------------------
def _prepare_real(config: ExperimentalDatasetConfig, *, data_root: Path | None,
                  output_dir: Path | None) -> PreparedDataset:
    from app.core.config import get_settings
    settings = get_settings()
    data_root = Path(data_root) if data_root else Path(settings.data_dir)
    out = Path(output_dir) if output_dir else None

    availability, provenance = _load_availability(config.dataset_id, data_root, settings)
    record = _provenance_record(config, provenance)

    status = availability.status_for(config.dataset_id) if availability else AVAIL_NOT_PRESENT
    if status == AVAIL_NOT_PRESENT:
        validation = validate_experimental_dataset(
            config.dataset_id, [], num_classes=config.class_count,
            required_classes=config.required_classes, class_mapping=config.class_mapping,
            data_regime=REGIME_REAL)
        record.access_status = "NOT_PRESENT (manual/authenticated access required — see docs)"
        artifact = DatasetArtifact.create(
            dataset_id=config.dataset_id, dataset_version=config.dataset_version or record.version,
            manifest_version=config.manifest_version, preprocessing_version=config.preprocessing_version,
            config_hash=config.config_hash(), validation_report=validation.to_dict(),
            dataset_record=record.to_dict(), data_regime=REGIME_REAL,
            notes="Real dataset NOT PRESENT — no data downloaded (access controls respected).")
        readiness = is_experiment_ready(artifact, split_manifest=ExperimentalSplitManifest(),
                                        config=config, dataset_record=record)
        handoff = build_handoff(artifact, readiness, config, dataset_artifact_path="",
                                split_manifest_path="", normalization_statistics_path="")
        written = {}
        if out:
            written["artifact"] = str(artifact.save_json(out / "dataset_artifact.json"))
        logger.warning("Real dataset '%s' NOT PRESENT — readiness=False (no download performed).",
                       config.dataset_id)
        return PreparedDataset(
            config=config, data_regime=REGIME_REAL, validation=validation, dataset_record=record,
            artifact=artifact, readiness=readiness, handoff=handoff, availability=availability,
            output_dir=out, written=written)

    # Data present but reading real GeoTIFF needs rasterio (absent here) — report honestly, don't fabricate.
    validation = validate_experimental_dataset(
        config.dataset_id, [], num_classes=config.class_count,
        required_classes=config.required_classes, class_mapping=config.class_mapping,
        data_regime=REGIME_REAL, metadata_ok=True)
    validation.overall_status = NOT_PRESENT
    validation.warnings.append("Data present but a label reader (rasterio) is unavailable — "
                               "install rasterio/tacoreader to validate real rasters.")
    record.access_status = "PRESENT (validation requires rasterio — NOT VERIFIED)"
    artifact = DatasetArtifact.create(
        dataset_id=config.dataset_id, dataset_version=config.dataset_version or record.version,
        manifest_version=config.manifest_version, preprocessing_version=config.preprocessing_version,
        config_hash=config.config_hash(), validation_report=validation.to_dict(),
        dataset_record=record.to_dict(), data_regime=REGIME_REAL,
        notes="Real data present but not machine-verifiable without rasterio.")
    readiness = is_experiment_ready(artifact, split_manifest=ExperimentalSplitManifest(),
                                    config=config, dataset_record=record)
    handoff = build_handoff(artifact, readiness, config, dataset_artifact_path="",
                            split_manifest_path="", normalization_statistics_path="")
    return PreparedDataset(
        config=config, data_regime=REGIME_REAL, validation=validation, dataset_record=record,
        artifact=artifact, readiness=readiness, handoff=handoff, availability=availability, output_dir=out)


def _load_availability(dataset_id: str, data_root: Path, settings: Any):
    """Load manifest records + availability; degrade gracefully if PyYAML/manifest is unavailable."""
    try:
        from app.datasets.manifest import default_manifest_path, load_manifest
        manifest_path = default_manifest_path(settings.data_manifests_dir)
        records = load_manifest(manifest_path)
        availability = check_availability(records, data_root, metadata_dir=settings.data_metadata_dir,
                                          manifest_path=manifest_path)
        return availability, records.get(dataset_id)
    except Exception as exc:  # noqa: BLE001 - manifest/yaml problems must not crash a readiness check
        logger.warning("Could not load manifest for availability: %s", exc)
        return None, None


def _provenance_record(config: ExperimentalDatasetConfig, provenance: Any) -> ExperimentalDatasetRecord:
    """Build the experimental record from M3 provenance (nothing invented)."""
    if provenance is None:
        return ExperimentalDatasetRecord(
            dataset_id=config.dataset_id, band_count=config.band_count, class_count=config.class_count,
            class_mapping={str(k): v for k, v in config.class_mapping.items()},
            preprocessing_version=config.preprocessing_version, manifest_version=config.manifest_version,
            data_regime=REGIME_REAL, notes="No provenance record found in datasets.yaml.")
    return ExperimentalDatasetRecord(
        dataset_id=config.dataset_id, dataset_name=getattr(provenance, "name", "UNKNOWN"),
        version=getattr(provenance, "version", "UNKNOWN"), source=getattr(provenance, "source", "UNKNOWN"),
        source_url=getattr(provenance, "homepage", "UNKNOWN"), license=getattr(provenance, "license", "UNKNOWN"),
        access_status="requires manual/authenticated access", download_date=getattr(provenance, "download_date", "") or "N/A",
        band_count=config.band_count, class_count=config.class_count,
        class_mapping={str(k): v for k, v in config.class_mapping.items()},
        spatial_resolution=config.spatial_resolution, preprocessing_version=config.preprocessing_version,
        manifest_version=config.manifest_version, data_regime=REGIME_REAL,
        notes=getattr(provenance, "notes", ""))


def _write_outputs(out: Path, artifact: DatasetArtifact, split_manifest: ExperimentalSplitManifest,
                   norm_stats: Any, distribution: ClassDistributionReport,
                   validation: DatasetValidationReport, manifest: PatchManifest,
                   record: ExperimentalDatasetRecord) -> dict[str, str]:
    """Persist all pipeline outputs under ``out`` (a processed-dataset directory)."""
    import json
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    written["artifact"] = str(artifact.save_json(out / "dataset_artifact.json"))
    written["split_manifest"] = str(split_manifest.save_json(out / "split_manifest.json"))
    written["normalization"] = str(norm_stats.save_json(out / "normalization_statistics.json"))
    (out / "class_distribution.json").write_text(json.dumps(distribution.to_dict(), indent=2),
                                                 encoding="utf-8")
    written["class_distribution"] = str(out / "class_distribution.json")
    (out / "validation_report.json").write_text(json.dumps(validation.to_dict(), indent=2),
                                                encoding="utf-8")
    written["validation"] = str(out / "validation_report.json")
    (out / "dataset_record.json").write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
    written["dataset_record"] = str(out / "dataset_record.json")
    written["patch_manifest"] = str(manifest.save_jsonl(out / "patch_manifest.jsonl"))
    return written


def default_processed_dir(dataset_id: str, data_root: Path) -> Path:
    """Conventional processed-dataset output directory."""
    return Path(data_root) / DEFAULT_PROCESSED_DIRNAME / dataset_id


def prepare_real_local_dataset(
    config: ExperimentalDatasetConfig,
    *,
    samples: list[SampleRecord],
    groups: dict[str, str],
    sample_classes: dict[str, set[str]],
    checksums: dict[str, str],
    image_reader,
    label_reader,
    image_size: tuple[int, int],
    dataset_version: str,
    dataset_record: ExperimentalDatasetRecord,
    output_dir: Path,
    expected_bands: int | None = 1,
) -> PreparedDataset:
    """Run the full M12 readiness pipeline on **already-acquired real local** samples (REAL regime).

    Reuses every M12 building block (validation gates, subset, group-aware split, train-only normalization,
    class distribution, patch manifest, artifact, readiness, handoff). No pixels are synthesised; all rasters
    are read via the injected rasterio readers. ``image_reader``/``label_reader`` map a path → a ``(C,H,W)`` /
    ``(H,W)`` array.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1) Validation gates (reuse M3 integrity + rasterio readers).
    validation = validate_experimental_dataset(
        config.dataset_id, samples, num_classes=config.class_count,
        required_classes=config.required_classes, class_mapping=config.class_mapping,
        label_reader=label_reader, checksums=checksums, expected_bands=expected_bands,
        metadata_ok=True, data_regime=REGIME_REAL)

    # 2) Deterministic subset record over the acquired pool (already class/scene-curated at acquisition).
    subset = select_subset([s.sample_id for s in samples], config=config, groups=groups,
                           sample_classes=sample_classes, data_regime=REGIME_REAL)

    # 3) Class-stratified group-aware split (reuse M4) — guarantees thin cloud is evaluable in val/test.
    split_manifest = build_split_manifest(subset, config=config, dataset_version=dataset_version,
                                          sample_classes=sample_classes, stratify=True)
    by_id = {s.sample_id: s for s in samples}
    samples_by_split: dict[str, list[SampleRecord]] = {
        split: [by_id[sid] for sid in split_manifest.ids_for(split) if sid in by_id]
        for split in ("train", "val", "test")}

    # 4) Real class distribution (thin cloud surfaced).
    distribution = class_distribution_report(
        samples_by_split, label_reader=label_reader, class_mapping=config.class_mapping,
        data_regime=REGIME_REAL)

    # 5) Normalization fit on TRAIN ONLY (reuse M4).
    train_images = [s.image_paths[0] for s in samples_by_split["train"] if s.image_paths]
    norm_stats = fit_normalization(train_images, image_reader=image_reader,
                                   normalization_mode=config.normalization_mode,
                                   nodata_value=config.nodata_value)
    norm_hash = normalization_stats_hash(norm_stats)

    # 6) Patch manifest (reuse M4).
    patch_size_used = min(config.patch_size, image_size[0], image_size[1])
    manifest = PatchManifest()
    for split in ("train", "val", "test"):
        for s in samples_by_split[split]:
            manifest.extend(build_patch_records(s, split, patch_size_used, config.overlap, image_size))

    dataset_record.patch_count = len(manifest)
    dataset_record.patch_dimensions = f"{image_size[0]}x{image_size[1]}"
    dataset_record.observed_files = [str(p) for s in samples for p in s.image_paths][:8]

    counts = split_manifest.counts()
    artifact = DatasetArtifact.create(
        dataset_id=config.dataset_id, dataset_version=dataset_version,
        manifest_version=config.manifest_version, preprocessing_version=config.preprocessing_version,
        config_hash=config.config_hash(), subset_selection_hash=subset.selection_hash(),
        split_manifest_hash=split_manifest.split_config_hash(), normalization_statistics_hash=norm_hash,
        validation_report=validation.to_dict(), class_distribution=distribution.to_dict(),
        dataset_record=dataset_record.to_dict(), sample_count=subset.size, patch_count=len(manifest),
        train_count=counts["train"], validation_count=counts["val"], test_count=counts["test"],
        data_regime=REGIME_REAL, notes="Real CloudSEN12+ curated subset (CC0).")

    readiness = is_experiment_ready(artifact, split_manifest=split_manifest, config=config,
                                    dataset_record=dataset_record)
    written = _write_outputs(out, artifact, split_manifest, norm_stats, distribution, validation,
                             manifest, dataset_record)
    handoff = build_handoff(
        artifact, readiness, config, dataset_artifact_path=written.get("artifact", ""),
        split_manifest_path=written.get("split_manifest", ""),
        normalization_statistics_path=written.get("normalization", ""))
    handoff_path = out / "experiment_handoff.json"
    handoff_path.write_text(json.dumps(handoff.to_dict(), indent=2), encoding="utf-8")
    written["handoff"] = str(handoff_path)

    logger.info("REAL dataset prepared: ready=%s, samples=%d, patches=%d.",
                readiness.ready, subset.size, len(manifest))
    return PreparedDataset(
        config=config, data_regime=REGIME_REAL, validation=validation, dataset_record=dataset_record,
        artifact=artifact, readiness=readiness, handoff=handoff, subset=subset,
        split_manifest=split_manifest, class_distribution=distribution, normalization_hash=norm_hash,
        patch_count=len(manifest), output_dir=out, written=written)
