# data/metadata

Human- and machine-referenced metadata describing the datasets' imagery and labels. **Tracked** (small
documentation, not heavy data).

| File | Describes |
|------|-----------|
| [`sentinel2_bands.md`](sentinel2_bands.md) | Sentinel-2 bands + spatial resolution. |
| [`cloudsen12_classes.md`](cloudsen12_classes.md) | CloudSEN12 multi-class label definitions. |
| [`on_cloud_n_labels.md`](on_cloud_n_labels.md) | On Cloud N binary label + band definitions. |

## Spatial resolution (summary)

Sentinel-2 MSI bands are natively 10 m, 20 m, or 60 m depending on band (see `sentinel2_bands.md`). Both
datasets provide imagery derived from Sentinel-2; the exact per-dataset resampling/patch size is recorded
per dataset and **requires verification** at download.

## Temporal resolution (summary)

The Sentinel-2 two-satellite constellation (S2A + S2B) has a combined revisit of ~5 days at the equator
(≈10 days for a single satellite), higher at higher latitudes due to swath overlap.
Source: ESA Copernicus Sentinel-2 mission documentation.

> Cloud masking here is a **per-scene** task; temporal resolution matters for the downstream
> change-detection task (O4, Milestone 12), not for single-scene masking.

## Provenance note

Sentinel-2 mission facts (bands, resolutions, revisit) are established ESA Copernicus specifications.
**Dataset-specific** details (exact bands provided, patch size, class integers, label encoding) are
marked **"requires verification"** until confirmed against the downloaded data and its official
documentation, per the Milestone 3 honesty policy.
