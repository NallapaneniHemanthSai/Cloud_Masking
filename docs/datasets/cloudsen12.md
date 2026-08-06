# CloudSEN12 / CloudSEN12+ (Primary Dataset)

Global Sentinel-2 dataset with **multi-class** cloud labels (clear / thick cloud / thin cloud / cloud
shadow). Primary dataset for this project (ADR-0001). Metadata below is **verified** against the sources
listed at the bottom; unconfirmed items are marked *requires verification*.

## Versions

- **CloudSEN12** — original release (Scientific Data, 2022), 49,400 patches.
- **CloudSEN12+** — expanded/refined expert-labeled release (Data in Brief, 2024); current Hugging Face
  version **1.1.2**.

## Citation

> Aybar, C., Ysuhuaylas, L., Loja, J. et al. (2022). *CloudSEN12, a global dataset for semantic
> understanding of cloud and cloud shadow in Sentinel-2.* Scientific Data 9, 782.
> https://doi.org/10.1038/s41597-022-01878-2
>
> Extended by: Aybar, C. et al. (2024). *CloudSEN12+: The largest dataset of expert-labeled pixels for
> cloud and cloud shadow detection in Sentinel-2.* Data in Brief.
> https://www.sciencedirect.com/science/article/pii/S2352340924008163
> (exact volume/article number — *requires verification*.)

## Licence

**CC0-1.0 (public domain)** — verified. Redistribution permitted; citation requested but not required.

## Classes (verified)

`0 = clear` (incl. snow/bright surfaces), `1 = thick cloud`, `2 = thin cloud` (haze approximated here),
`3 = cloud shadow`.

## Bands (verified)

- **L1C:** 13 bands (B01–B12, B8A), reflectance scale 0.0001.
- **L2A:** 11 bands (excludes B09, B10) + AOT + WVP.

## Access route (verified channels)

CloudSEN12+ is distributed as **Cloud-Optimized GeoTIFF** via **Hugging Face**
(`tacofoundation/cloudsen12`), loaded with the **`tacoreader`** library (≥ 0.5.3); also available via
Zenodo and Google Earth Engine.

1. Install `tacoreader` (≥ 0.5.3) into the project's Python 3.11 environment.
2. Load from Hugging Face `tacofoundation/cloudsen12`; choose L1C or L2A and the high-quality subset.
3. Write raw files under `data/raw/cloudsen12/`.
4. Record `download_date` + per-file `checksum` in `data/manifests/datasets.yaml`.
5. Run `backend/scripts/verify_datasets.py`.

Because access is via a library API (not a static URL), `datasets.yaml` records **no direct
`download_urls`**, and `download_cloudsen12.py` prints these documented steps.

## Storage

Full CloudSEN12+ is **very large** (order of hundreds of GB — *requires verification at download*). This
project uses a **curated subset** (Milestone 4) to fit the Apple-Silicon compute envelope (ADR-0002,
Risk R-03). Confirm available disk before downloading.

## Sources

CloudSEN12 (Scientific Data 9:782, 2022); CloudSEN12+ (Data in Brief, 2024); Hugging Face
`tacofoundation/cloudsen12` dataset card; https://cloudsen12.github.io/.
