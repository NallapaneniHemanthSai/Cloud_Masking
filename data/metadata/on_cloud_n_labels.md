# On Cloud N Labels

On Cloud N (reference benchmark) provides **binary** pixel labels over a 4-band Sentinel-2 subset.
Verified against the DrivenData competition materials and benchmark write-up, and cross-checked with the
`torchgeo` CloudCoverDetection dataset documentation.

## Bands (verified)

Each chip has **4 bands from Sentinel-2 L2A**, one single-band GeoTIFF per band:

| Band | Name | Resolution |
|------|------|------------|
| B02 | Blue | 10 m |
| B03 | Green | 10 m |
| B04 | Red | 10 m |
| B08 | NIR | 10 m |

No SWIR (B11/B12) or cirrus (B10) bands are provided, so **NDSI and cirrus-based thin-cloud detection are
not possible** on On Cloud N — it is used only to reproduce published *binary* results and as a
domain-shift check (ADR-0001).

## Chips (verified)

- **512×512** pixels per chip; **22,728** training chips (imagery captured **2018–2020**).
- Files organised per chip id as `B02.tif`, `B03.tif`, `B04.tif`, `B08.tif`; each GeoTIFF carries its
  bounding coordinates, affine transform, and CRS.

## Labels (verified as binary)

| Label integer | Meaning |
|---------------|---------|
| 0 | No cloud |
| 1 | Cloud |

Labels are single-band **512×512** GeoTIFFs. This matches `app.core.constants.OnCloudNLabel`. *(Exact
pixel encoding beyond {0,1} is not separately documented — **requires verification** at download.)*

## Access & retention

On Cloud N is **retained, not replaced**. Access requires DrivenData registration and acceptance of the
competition/data terms; **redistribution is prohibited** (see `docs/datasets/on_cloud_n.md`,
`docs/datasets/licenses.md`). Provenance is in `data/manifests/datasets.yaml`.
