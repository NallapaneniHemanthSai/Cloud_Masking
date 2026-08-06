# ADR-0001 — Primary Dataset Selection

- **Status:** ACCEPTED (2026-08-06)
- **Deciders:** Project owner + assistant (planning)
- **Milestone:** M1
- **Related:** Risk R-05 (closed), Assumptions AS-01/AS-02, `04_SOURCE_TO_CLAIM_MAP.md` C-1/C-2

## Context

The cited reference source ("Satellite cloud detection" / DrivenData *On Cloud N*) provides Sentinel-2
imagery with **binary** cloud labels and only **4 bands** (B02, B03, B04, B08). The project's core
objectives require **stratifying** performance by **thin cloud, haze, snow, and bright surfaces** (O2) and
**discriminating cloud from bright surfaces such as snow** (O3).

Binary, 4-band data **cannot physically support** these objectives:
- No **cirrus band (B10)** → cannot flag thin cloud spectrally.
- No **SWIR bands (B11/B12)** → cannot compute **NDSI** = (B03−B11)/(B03+B11) for snow discrimination.
- No multi-class labels → no ground truth to stratify thin vs thick cloud.

## Options Considered

1. **CloudSEN12 (primary) + On Cloud N (cited reference).**
   - 13-band Sentinel-2; multi-class labels (clear / thick cloud / thin cloud / cloud shadow); global,
     includes snow-prone regions; hand-labelled high-quality subset available.
   - Directly supports O2 stratification, cirrus-based thin cloud, SWIR/NDSI-based snow/bright-surface work.
   - Larger download; multi-source hosting (HuggingFace/Zenodo/GEE).
2. **On Cloud N only + heuristically derived strata.**
   - Cheaper, but cannot do NDSI (no SWIR) or cirrus thin-cloud; O2/O3 become weakly supported. **Rejected.**
3. **SPARCS + Landsat-8 Biome.**
   - Explicit snow/ice class, full band set, strong snow stratification; but Landsat (not Sentinel-2),
     smaller, less thin-cloud emphasis. Kept as **alternative / cross-sensor validation candidate.**

## Decision

Adopt a **dual-dataset strategy — neither dataset is replaced**:

- **Primary dataset = CloudSEN12** (13-band Sentinel-2, multi-class) — used for multi-class cloud detection,
  O2 stratification, and the O3 cloud-vs-bright-surface contribution.
- **Reference benchmark = On Cloud N** (4-band, binary) — **actively reproduced** to (a) validate that our
  segmentation pipeline reproduces published binary cloud-detection results (FR-2 oracle) and (b) provide a
  **cross-dataset domain-shift check** (Risk R-13, claim C-6). On Cloud N is a first-class part of the plan,
  not merely cited.

Keep **SPARCS/Biome** noted as an optional cross-sensor robustness check.

## Consequences

- **Positive:** every stratification KPI (KPI-1/2/5) and the O3 snow/bright-surface contribution become
  physically supportable; spectral-index features (NDSI, cirrus) become available.
- **Negative / to manage:** larger data footprint → use hand-labelled subset + region-stratified sampling
  (R-03); snow/bright surface is not a native label → derived via spectral proxy (AS-01/AS-02), which must
  be validated in M4/M9, not assumed.
- **Verification owed (M3):** confirm CloudSEN12 class definitions, exact band list, patch size, licence,
  and snow-region coverage before building on them (source-to-claim C-2).

## Reference

Aybar, C. et al. "CloudSEN12, a global dataset for semantic understanding of cloud and cloud shadow in
Sentinel-2." *Scientific Data* 9, 782 (2022). *(Full citation to be verified and added to `paper/` in M3/M19.)*
