# Dataset Licences, Redistribution, Citation & Usage Restrictions

Verified against official sources on **2026-08-06**. Items that could not be confirmed remain marked
**"requires verification"** with the reason. Never claim a licence that has not been verified.

## CloudSEN12 / CloudSEN12+ (primary)

| Field | Value |
|-------|-------|
| Licence | **CC0-1.0 (public domain)** — verified (CloudSEN12+ dataset card, Hugging Face `tacofoundation/cloudsen12`; CloudSEN12 Sci Data 2022). |
| Redistribution | **Permitted** — CC0-1.0 places the data in the public domain (no permission/attribution required). |
| Citation requirement | Not legally required under CC0, but **citation is requested**: Aybar et al. (2022), Scientific Data 9:782 (see `cloudsen12.md`). |
| Usage restrictions | None under CC0. Confirm the specific variant/version (original vs CloudSEN12+ v1.1.2) you use. |

## On Cloud N (reference benchmark)

| Field | Value |
|-------|-------|
| Licence | **DrivenData competition data-use terms** governing the labels/packaging; underlying imagery is Sentinel-2 (Copernicus) via Microsoft Planetary Computer. |
| Redistribution | **PROHIBITED (verified).** Competition terms: participants "agree not to transmit, duplicate, publish, redistribute or otherwise provide or make available the Data to any party not participating"; use is limited to the competition's purpose and duration. |
| Citation requirement | Cite the On Cloud N / Radiant Earth dataset (see `on_cloud_n.md`); acknowledge DrivenData & Microsoft. Exact dataset DOI/citation **requires verification** (former Radiant MLHub host was sunset). |
| Usage restrictions | Access requires registration and acceptance of terms. **Retained, not replaced.** |

## Underlying imagery — Sentinel-2 / Copernicus

Both datasets derive from ESA **Copernicus Sentinel-2** imagery, provided under the Copernicus open-data
licence (free and open use with attribution to the Copernicus programme). Dataset-specific labels and
packaging add their own terms (above).

## Project commitments

- Keep raw datasets **git-ignored**; never redistribute On Cloud N data (redistribution prohibited).
- Record exact licence + version in `data/manifests/datasets.yaml`; CloudSEN12 confirmed CC0-1.0.
- Provide citations in `paper/` (Milestone 19).
- Treat any unresolved licence question as **Risk R-14** and block redistribution until resolved.

**Sources:** Hugging Face `tacofoundation/cloudsen12` dataset card; CloudSEN12 (Scientific Data 9:782,
2022); DrivenData *On Cloud N* competition data-use terms; DrivenData cloud-cover benchmark write-up.
