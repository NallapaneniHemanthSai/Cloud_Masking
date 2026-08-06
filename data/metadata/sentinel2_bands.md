# Sentinel-2 MSI Bands

Reference table of Sentinel-2 MultiSpectral Instrument (MSI) bands. Values are ESA Copernicus mission
specifications (central wavelength for Sentinel-2A; S2B differs slightly). Use this to interpret the
13-band CloudSEN12 imagery and the 4-band On Cloud N subset.

| Band | Name | Central λ (nm, S2A) | Spatial resolution | Relevance to cloud masking |
|------|------|---------------------|--------------------|----------------------------|
| B01 | Coastal aerosol | 443 | 60 m | Aerosol/haze sensitivity |
| B02 | Blue | 490 | 10 m | On Cloud N band; brightness |
| B03 | Green | 560 | 10 m | On Cloud N band; **NDSI** numerator |
| B04 | Red | 665 | 10 m | On Cloud N band; brightness |
| B05 | Red edge 1 | 705 | 20 m | Vegetation/edge |
| B06 | Red edge 2 | 740 | 20 m | Vegetation/edge |
| B07 | Red edge 3 | 783 | 20 m | Vegetation/edge |
| B08 | NIR | 842 | 10 m | On Cloud N band; brightness |
| B8A | Narrow NIR | 865 | 20 m | Vegetation/water |
| B09 | Water vapour | 945 | 60 m | Atmospheric water vapour |
| B10 | SWIR – Cirrus | 1375 | 60 m | **Thin/cirrus cloud** detection |
| B11 | SWIR 1 | 1610 | 20 m | **NDSI** (snow vs cloud) |
| B12 | SWIR 2 | 2190 | 20 m | Snow/cloud discrimination |

## Derived indices used later (Milestone 4)

- **NDSI** (Normalized Difference Snow Index) = (B03 − B11) / (B03 + B11) — separates **snow** from cloud.
- **Cirrus** band **B10** — flags optically **thin cloud**.

> These indices require the SWIR/cirrus bands, which the 13-band **CloudSEN12** provides but the 4-band
> **On Cloud N** subset does **not** — one reason CloudSEN12 is the primary dataset (ADR-0001).

**Source:** ESA Copernicus Sentinel-2 mission documentation. Per-dataset band availability and scaling
(reflectance vs DN) **requires verification** against each dataset's documentation at download.
