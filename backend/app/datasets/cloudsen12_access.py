"""CloudSEN12+ acquisition adapter for tacoreader 0.6.5 (Milestone 12, real data).

The **smallest necessary adapter** between the official CloudSEN12 access route (tacoreader 0.6.5 →
Hugging Face ``tacofoundation/cloudsen12``, CC0-1.0) and the existing M3/M12 dataset-management interfaces.
It does **not** create a second generic downloader — it reuses M3 integrity (`compute_checksum`) and feeds
the M12 pipeline typed :class:`SampleRecord`s. Verified against the installed tacoreader 0.6.5 API (not
guessed):

* ``tacoreader.load("<part.taco url>")`` → ``TortillaDataFrame`` (pandas); metadata footer only.
* each L1C sample is a ``TORTILLA`` of two ``GTiff`` assets: ``s2l1c`` (13-band uint16 512×512) and
  ``target`` (uint8 512×512 label: 0=clear,1=thick,2=thin,3=shadow) — read by **rasterio** from a
  ``/vsisubfile/…,/vsicurl/…`` ranged path, so a bounded subset downloads without the ~1 TB full set.
* per-sample class fractions (``thin_percentage`` …), ``roi_id`` (scene/group), and ``label_type``
  (``high`` = expert labels) live in the metadata → **class/scene-aware selection needs no raster reads**.

Requires the project venv (numpy, rasterio, tacoreader, aiohttp). Never bypasses access controls.
"""

from __future__ import annotations

import json
import logging
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.datasets.integrity import compute_checksum
from app.preprocessing.records import SampleRecord

logger = logging.getLogger(__name__)

CLOUDSEN12_REGISTRY_KEY = "cloudsen12-l1c"
CLASS_PCT_COLUMNS = ("clear_percentage", "thick_percentage", "thin_percentage", "cloud_shadow_percentage")


def ensure_tls_ca() -> str | None:
    """Point Python (aiohttp) and GDAL (rasterio /vsicurl) at certifi's CA bundle.

    macOS framework Python has no system CA store, so aiohttp/GDAL fail TLS verification; certifi (present
    via requests) provides the roots. Sets ``SSL_CERT_FILE`` / ``CURL_CA_BUNDLE`` when unset. Read-only wrt
    packages (installs nothing).
    """
    try:
        import certifi
    except ImportError:  # pragma: no cover
        return None
    ca = certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", ca)
    os.environ.setdefault("CURL_CA_BUNDLE", ca)
    return ca


def l1c_part_urls() -> list[str]:
    """Fetch the (public) CloudSEN12 L1C TACO part URLs from the TACO Foundation registry."""
    ensure_tls_ca()
    from tacoreader.v1.loader_dataframe import load_tacofoundation_datasets
    reg = load_tacofoundation_datasets()
    parts = reg[CLOUDSEN12_REGISTRY_KEY]
    return list(parts) if isinstance(parts, (list, tuple)) else [parts]


def load_l1c_part(part_index: int = 0) -> Any:
    """Load one L1C TACO part's metadata (footer only) as a ``TortillaDataFrame``."""
    ensure_tls_ca()
    import tacoreader
    url = l1c_part_urls()[part_index]
    logger.info("Loading CloudSEN12 L1C metadata footer: %s", url)
    df = tacoreader.load(url)
    df.attrs["source_url"] = url
    return df


# --------------------------------------------------------------------------------------------------
# Deterministic, class/scene-aware subset selection (metadata-only — no raster reads).
# --------------------------------------------------------------------------------------------------
@dataclass
class SelectionPlan:
    """A deterministic selection of sample positions with provenance for reproducibility."""

    positions: list[int]
    seed: int
    subset_size: int
    label_type: str
    min_thin_pct: float
    min_shadow_pct: float
    source_url: str
    part_index: int
    pool_size: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "positions": list(self.positions), "seed": self.seed, "subset_size": self.subset_size,
            "label_type": self.label_type, "min_thin_pct": self.min_thin_pct,
            "min_shadow_pct": self.min_shadow_pct, "source_url": self.source_url,
            "part_index": self.part_index, "pool_size": self.pool_size,
        }


def select_cloudsen12_subset(df: Any, *, seed: int, subset_size: int, part_index: int = 0,
                             label_type: str = "high", min_thin_pct: float = 10.0,
                             min_shadow_pct: float = 10.0, min_thick_pct: float = 10.0) -> tuple[Any, SelectionPlan]:
    """Select a deterministic, class-aware, scene-diverse subset from a part's metadata.

    Guarantees (from metadata class fractions, so no rasters are downloaded to choose):
    thin-cloud samples (``thin_percentage >= min_thin_pct``) and cloud-shadow samples
    (``cloud_shadow_percentage >= min_shadow_pct``) are included, then fills the budget with class-diverse,
    ROI-distinct samples. Deterministic given ``seed``. Returns ``(high_df, SelectionPlan)`` where the plan's
    positions are ``iloc`` positions into ``high_df`` (usable with ``TortillaDataFrame.read``).
    """
    hi = df[df["label_type"] == label_type].reset_index(drop=True)
    for c in CLASS_PCT_COLUMNS:
        hi[c] = hi[c].astype(float)
    rng = random.Random(seed)
    chosen: list[int] = []
    chosen_roi: set[str] = set()

    def positions_where(mask) -> list[int]:
        return sorted(int(p) for p in hi.index[mask].tolist())   # canonical order

    def pick(pool: list[int], k: int, *, distinct_roi: bool = True) -> list[int]:
        order = list(pool)
        rng.shuffle(order)
        out: list[int] = []
        for p in order:
            if len(out) >= k:
                break
            if p in chosen:
                continue
            roi = str(hi.iloc[p]["roi_id"])
            if distinct_roi and roi in chosen_roi:
                continue
            out.append(p)
            chosen_roi.add(roi)
        if len(out) < k:                                          # relax the distinct-ROI constraint
            for p in order:
                if len(out) >= k:
                    break
                if p in chosen or p in out:
                    continue
                out.append(p)
        return out

    n_thin = max(4, subset_size // 4)
    n_shadow = max(4, subset_size // 4)
    n_thick = max(2, subset_size // 6)
    chosen += pick(positions_where(hi["thin_percentage"] >= min_thin_pct), n_thin)
    chosen += [p for p in pick(positions_where(hi["cloud_shadow_percentage"] >= min_shadow_pct), n_shadow)
               if p not in chosen]
    chosen += [p for p in pick(positions_where(hi["thick_percentage"] >= min_thick_pct), n_thick)
               if p not in chosen]
    remaining = subset_size - len(chosen)
    if remaining > 0:                                            # fill with clear-inclusive diversity
        chosen += [p for p in pick(positions_where(hi["clear_percentage"] >= 0), remaining)
                   if p not in chosen]
    chosen = sorted(set(chosen))[:subset_size]

    plan = SelectionPlan(
        positions=chosen, seed=seed, subset_size=subset_size, label_type=label_type,
        min_thin_pct=min_thin_pct, min_shadow_pct=min_shadow_pct,
        source_url=df.attrs.get("source_url", ""), part_index=part_index, pool_size=len(hi))
    logger.info("Selected %d/%d %s-label sample(s) (seed=%d).", len(chosen), len(hi), label_type, seed)
    return hi, plan


# --------------------------------------------------------------------------------------------------
# Download the selected subset to local GeoTIFFs (git-ignored raw path) + provenance/checksums.
# --------------------------------------------------------------------------------------------------
@dataclass
class AcquiredSample:
    """One acquired real sample with provenance."""

    sample_id: str
    roi_id: str
    s2_id: str
    data_split: str
    image_path: str
    label_path: str
    image_checksum: str
    label_checksum: str
    crs: str
    class_percentages: dict[str, float]
    raster_shape: list[int]
    label_values: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id, "roi_id": self.roi_id, "s2_id": self.s2_id,
            "data_split": self.data_split, "image_path": self.image_path, "label_path": self.label_path,
            "image_checksum": self.image_checksum, "label_checksum": self.label_checksum, "crs": self.crs,
            "class_percentages": self.class_percentages, "raster_shape": self.raster_shape,
            "label_values": self.label_values,
        }


def _safe_id(raw: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in str(raw))


def download_selected(hi: Any, plan: SelectionPlan, dest_root: Path, *,
                      compress: str = "deflate") -> list[AcquiredSample]:
    """Download each selected sample's ``s2l1c`` + ``target`` into ``dest_root`` as compressed GeoTIFFs.

    Reads only the selected samples' bytes (ranged) — never the full dataset. Records provenance +
    SHA-256 checksums (reusing M3 ``compute_checksum``). Failed samples are skipped and reported.
    """
    import numpy as np
    import rasterio
    ensure_tls_ca()

    dest_root = Path(dest_root)
    images_dir = dest_root / "images"
    labels_dir = dest_root / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    acquired: list[AcquiredSample] = []
    failures: list[dict[str, Any]] = []
    for pos in plan.positions:
        meta = hi.iloc[pos]
        sid = _safe_id(meta["tortilla:id"])
        try:
            sample = hi.read(pos)                          # nested tortilla (s2l1c, target)
            s2_path = sample.read(0)
            tgt_path = sample.read(1)
            with rasterio.open(s2_path) as src:
                img = src.read()
                img_profile = src.profile
                crs = str(src.crs)
            with rasterio.open(tgt_path) as src:
                lab = src.read(1)
                lab_profile = src.profile
        except Exception as exc:  # noqa: BLE001 - a bad sample must not abort the whole acquisition
            logger.warning("Sample %s failed to download/read: %s", sid, exc)
            failures.append({"sample_id": sid, "error": f"{type(exc).__name__}: {exc}"})
            continue

        ip = images_dir / f"{sid}.tif"
        lp = labels_dir / f"{sid}.tif"
        pim = img_profile.copy(); pim.update(compress=compress)
        with rasterio.open(ip, "w", **pim) as dst:
            dst.write(img)
        plb = lab_profile.copy(); plb.update(compress=compress)
        with rasterio.open(lp, "w", **plb) as dst:
            dst.write(lab, 1)

        acquired.append(AcquiredSample(
            sample_id=sid, roi_id=str(meta["roi_id"]), s2_id=str(meta.get("s2_id", "")),
            data_split=str(meta.get("tortilla:data_split", "")), image_path=str(ip), label_path=str(lp),
            image_checksum=compute_checksum(ip), label_checksum=compute_checksum(lp), crs=crs,
            class_percentages={c: float(meta[c]) for c in CLASS_PCT_COLUMNS},
            raster_shape=[int(img.shape[-2]), int(img.shape[-1])],
            label_values=sorted(int(v) for v in np.unique(lab).tolist())))

    # Persist provenance + checksums sidecars alongside the raw data (git-ignored).
    provenance = {
        "dataset": "cloudsen12", "variant": CLOUDSEN12_REGISTRY_KEY, "license": "CC0-1.0",
        "access": "tacoreader 0.6.5 -> tacofoundation/cloudsen12 (Hugging Face)",
        "selection": plan.to_dict(), "acquired_count": len(acquired), "failed": failures,
        "samples": [a.to_dict() for a in acquired],
    }
    (dest_root / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    (dest_root / "checksums.sha256").write_text(
        "\n".join(f"{a.image_checksum}  {a.image_path}\n{a.label_checksum}  {a.label_path}"
                  for a in acquired), encoding="utf-8")
    logger.info("Acquired %d sample(s) (%d failed) into %s.", len(acquired), len(failures), dest_root)
    return acquired


def load_acquired(dest_root: Path) -> tuple[list[AcquiredSample], dict[str, Any]] | None:
    """Reconstruct previously-acquired samples from a ``provenance.json`` sidecar (resume, no re-download).

    Returns ``(samples, provenance)`` only when the sidecar exists and all referenced files are present.
    """
    dest_root = Path(dest_root)
    prov_path = dest_root / "provenance.json"
    if not prov_path.is_file():
        return None
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    samples: list[AcquiredSample] = []
    for d in prov.get("samples", []):
        if not (Path(d["image_path"]).is_file() and Path(d["label_path"]).is_file()):
            return None
        samples.append(AcquiredSample(
            sample_id=d["sample_id"], roi_id=d.get("roi_id", ""), s2_id=d.get("s2_id", ""),
            data_split=d.get("data_split", ""), image_path=d["image_path"], label_path=d["label_path"],
            image_checksum=d.get("image_checksum", ""), label_checksum=d.get("label_checksum", ""),
            crs=d.get("crs", ""), class_percentages=dict(d.get("class_percentages", {}) or {}),
            raster_shape=list(d.get("raster_shape", [512, 512])),
            label_values=list(d.get("label_values", []) or [])))
    return (samples, prov) if samples else None


# --------------------------------------------------------------------------------------------------
# Bridges to the M12 pipeline (typed records + rasterio readers).
# --------------------------------------------------------------------------------------------------
def read_image(path: Path) -> Any:
    """Read a multi-band raster as a ``(C, H, W)`` array (rasterio)."""
    import rasterio
    with rasterio.open(path) as src:
        return src.read()


def read_label(path: Path) -> Any:
    """Read a single-band label raster as an ``(H, W)`` array (rasterio)."""
    import rasterio
    with rasterio.open(path) as src:
        return src.read(1)


def to_pipeline_inputs(acquired: list[AcquiredSample]) -> dict[str, Any]:
    """Convert acquired samples into the inputs the M12 pipeline consumes."""
    from app.datasets.experimental_config import CLOUDSEN12_CLASS_MAPPING
    samples: list[SampleRecord] = []
    groups: dict[str, str] = {}
    sample_classes: dict[str, set[str]] = {}
    checksums: dict[str, str] = {}
    for a in acquired:
        samples.append(SampleRecord(sample_id=a.sample_id, dataset="cloudsen12",
                                    image_paths=[Path(a.image_path)], label_path=Path(a.label_path),
                                    group=a.roi_id))
        groups[a.sample_id] = a.roi_id
        sample_classes[a.sample_id] = {CLOUDSEN12_CLASS_MAPPING[v] for v in a.label_values
                                       if v in CLOUDSEN12_CLASS_MAPPING}
        checksums[a.image_path] = a.image_checksum
        checksums[a.label_path] = a.label_checksum
    return {"samples": samples, "groups": groups, "sample_classes": sample_classes,
            "checksums": checksums, "image_size": tuple(acquired[0].raster_shape) if acquired else (512, 512)}
