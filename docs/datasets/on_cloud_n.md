# On Cloud N (Reference Benchmark)

4-band Sentinel-2 dataset with **binary** cloud / no-cloud labels, from the DrivenData *On Cloud N: Cloud
Cover Detection Challenge*. **Retained, not replaced** — used to reproduce published binary results
(FR-2 oracle) and as a cross-dataset domain-shift check (Risk R-13). Metadata verified against the
competition materials and benchmark write-up; unconfirmed items marked *requires verification*.

## Dataset facts (verified)

- **22,728** training chips; imagery captured **2018–2020**.
- **4 bands** from Sentinel-2 **L2A**: **B02, B03, B04, B08** — one single-band GeoTIFF per band.
- Chips are **512×512** px (10 m); each GeoTIFF carries bounding coordinates, affine transform, CRS.
- Labels: single-band **512×512** GeoTIFFs, **binary** (0 = no cloud, 1 = cloud).
- Data provider/custodian: **Radiant Earth Foundation**; imagery served via **Microsoft Planetary Computer**.

## Citation

> Radiant Earth Foundation & DrivenData (2021). *On Cloud N: Cloud Cover Detection Challenge* — Sentinel-2
> cloud cover dataset. Sponsored by Microsoft AI for Earth. *(Exact dataset DOI/citation requires
> verification — the former Radiant MLHub host was sunset.)*

## Licence & redistribution (verified)

Governed by the **DrivenData competition / data-use terms**; underlying imagery is Sentinel-2 (Copernicus)
via Planetary Computer. **Redistribution is PROHIBITED** — participants agree not to transmit, duplicate,
publish, or redistribute the data, and use is limited to the competition's purpose and duration.

## Access route (requires registration — do NOT bypass)

1. Create a DrivenData account and open competition 83:
   <https://www.drivendata.org/competitions/83/cloud-cover/>
2. **Accept the competition rules / data-use agreement.**
3. Download training features + labels from the competition **data** tab.
4. Place files under `data/raw/on_cloud_n/`, record `download_date` + `checksum` in the manifest, and run
   `backend/scripts/verify_datasets.py`.

`datasets.yaml` records **no direct `download_urls`** (authenticated access after agreement), and
`download_on_cloud_n.py` documents these steps. Authentication failures (HTTP 401/403) are reported by the
downloader, never bypassed.

## Storage

≈ tens of GB for the training set (22,728 chips × 4 bands × 512×512) — *verify at download*.

## Sources

DrivenData *On Cloud N* competition (competition 83) data-use terms & data page; DrivenData cloud-cover
benchmark write-up (drivendata.co/blog/cloud-cover-benchmark); `torchgeo` CloudCoverDetection docs.
