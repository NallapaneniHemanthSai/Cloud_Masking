# CloudSEN12 Label Classes

CloudSEN12 provides **multi-class** semantic labels for cloud understanding in Sentinel-2. Verified
against the CloudSEN12 paper (Scientific Data 2022) and the CloudSEN12+ dataset card
(Hugging Face `tacofoundation/cloudsen12`, version 1.1.2).

| Class integer | Class | Definition |
|---------------|-------|------------|
| 0 | Clear | Pixels without cloud/shadow contamination (includes snow / bright surfaces — no dedicated snow class). |
| 1 | Thick cloud | Opaque clouds blocking surface reflection. |
| 2 | Thin cloud | Semitransparent clouds; **haze is approximated within this class** (Charter §3.1). |
| 3 | Cloud shadow | Dark pixels where light is occluded by cloud. |

This matches `app.core.constants.CloudClass`. *(Source: CloudSEN12+ dataset card; CloudSEN12 Sci Data 2022.)*

## Bands (verified)

- **L1C mode:** all **13** bands — B01,B02,B03,B04,B05,B06,B07,B08,B8A,B09,B10,B11,B12 (reflectance scale 0.0001).
- **L2A mode:** **11** bands (excludes **B09** and **B10**) plus **AOT** and **WVP** layers (scale 0.0001).

## Patches & scale (verified)

- Patch sizes **509×509** and **2000×2000** px (padded to 512 / 2048 for divisibility by 32).
- ~**49,400** patches in the original release; global coverage (all continents except Antarctica).
- Current Hugging Face version **1.1.2**; tooling: **tacoreader** (≥0.5.3), Cloud-Optimized GeoTIFF.

## Stratification implication

Snow and other bright surfaces are labelled **"clear"**, not a separate class. Snow / bright-surface
pixels are stratified via **spectral proxies** (NDSI, brightness) using the SWIR/cirrus bands (available
in CloudSEN12's L1C) in Milestone 4 — this is exactly the cloud-vs-bright-surface challenge (O3).

## Label quality

CloudSEN12 includes hand-labelled ("high-quality") and automatic annotations of differing quality;
CloudSEN12+ expands the expert-labeled set. The specific subset/quality tier used is selected in
Milestone 4. Annotation quality is tracked as **Risk R-17**.
